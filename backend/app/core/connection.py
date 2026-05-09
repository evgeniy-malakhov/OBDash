"""
Стабильное асинхронное подключение к ELM327 через постоянное TCP соединение
"""

import asyncio
import logging
import time
import socket
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

from .exceptions import ConnectionError, CommandError, TimeoutError
from ..models.schemas import DeviceInfo, ConnectionType, DeviceStatus

logger = logging.getLogger(__name__)


@dataclass
class QueuedCommand:
    """Команда в очереди"""
    command: str
    timeout: float = 5.0
    future: asyncio.Future = field(default_factory=asyncio.Future)
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0


class ELM327Protocol:
    """
    Низкоуровневый протокол общения с ELM327

    Обеспечивает:
    - Стабильное TCP соединение с автоматическим переподключением
    - Последовательную отправку команд через очередь
    - Очистку буфера перед каждой командой
    - Правильное определение конца ответа
    - Heartbeat для проверки соединения
    """

    # Константы протокола
    COMMAND_TERMINATOR = b'\r\n'
    RESPONSE_PROMPT = b'>'
    HEARTBEAT_INTERVAL = 5.0  # Проверка соединения каждые 5 сек
    RECONNECT_DELAY = 2.0     # Задержка перед переподключением
    MAX_RETRIES = 3           # Максимальное число попыток
    BUFFER_CLEAR_TIMEOUT = 0.1 # Таймаут очистки буфера

    def __init__(self, host: str, port: int, device_info: DeviceInfo):
        self.host = host
        self.port = port
        self.device_info = device_info

        # Сетевое соединение
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

        # Очередь команд (FIFO)
        self._command_queue: asyncio.Queue[QueuedCommand] = asyncio.Queue(maxsize=100)

        # Состояние
        self.connected = False
        self.running = False

        # Задачи
        self._worker_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_disconnect: Optional[Callable] = None
        self.on_reconnect: Optional[Callable] = None

        # Статистика
        self.stats = {
            'commands_sent': 0,
            'commands_failed': 0,
            'reconnects': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'queue_high_watermark': 0,
        }

    async def connect(self) -> bool:
        """Устанавливает TCP соединение с ELM327"""
        logger.info(f"🔌 Установка TCP соединения с {self.host}:{self.port}")

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10.0
            )

            # Настраиваем TCP keepalive
            sock = self._writer.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Читаем приветствие ELM327
            greeting = await self._read_until_prompt(timeout=2.0)
            if greeting:
                logger.info(f"📨 Приветствие: {greeting[:100]}")

            self.connected = True
            self.running = True

            # Запускаем воркер и heartbeat
            self._worker_task = asyncio.create_task(self._process_queue())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            logger.info(f"✅ TCP соединение установлено с {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            self.connected = False
            raise ConnectionError(f"Не удалось подключиться к {self.host}:{self.port}: {str(e)}")

    async def disconnect(self):
        """Закрывает TCP соединение"""
        logger.info("🔌 Закрытие TCP соединения")

        self.running = False

        # Останавливаем задачи
        for task in [self._worker_task, self._heartbeat_task, self._reconnect_task]:
            if task:
                task.cancel()
                try:
                    await task
                except:
                    pass

        # Отменяем все ожидающие команды
        while not self._command_queue.empty():
            try:
                cmd = self._command_queue.get_nowait()
                if not cmd.future.done():
                    cmd.future.set_exception(
                        ConnectionError("Соединение закрыто")
                    )
            except:
                pass

        # Закрываем TCP
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except:
                pass

        self.connected = False
        self._reader = None
        self._writer = None
        logger.info("✅ TCP соединение закрыто")

    async def send_command(self, command: str, timeout: float = 5.0) -> str:
        """
        Отправляет команду ELM327 через очередь

        Этот метод безопасно вызывать из разных корутин.
        Он добавляет команду в очередь и ждёт результат.
        """
        if not self.connected:
            raise ConnectionError("Нет соединения с устройством")

        if self._command_queue.qsize() >= 90:  # Почти полная очередь
            logger.warning(f"⚠️ Очередь команд почти заполнена: {self._command_queue.qsize()}")

        # Обновляем метрику
        current_size = self._command_queue.qsize()
        if current_size > self.stats['queue_high_watermark']:
            self.stats['queue_high_watermark'] = current_size

        # Создаём команду
        cmd = QueuedCommand(command=command.strip(), timeout=timeout)

        # Добавляем в очередь
        await self._command_queue.put(cmd)

        try:
            # Ждём результат
            result = await asyncio.wait_for(cmd.future, timeout=timeout + 2.0)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Таймаут команды: {command}")
        except asyncio.CancelledError:
            raise ConnectionError("Соединение потеряно во время выполнения команды")

    async def _process_queue(self):
        """Воркер: последовательно обрабатывает очередь команд"""
        logger.debug("🔄 Воркер очереди команд запущен")

        while self.running:
            try:
                # Ждём следующую команду с таймаутом
                try:
                    cmd = await asyncio.wait_for(
                        self._command_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Проверяем, не отменён ли запрос
                if cmd.future.done():
                    continue

                # Выполняем команду
                try:
                    response = await self._execute_single_command(cmd)

                    if not cmd.future.done():
                        cmd.future.set_result(response)

                    self.stats['commands_sent'] += 1

                except Exception as e:
                    self.stats['commands_failed'] += 1

                    # Пробуем переподключиться при ошибке соединения
                    if isinstance(e, (ConnectionError, OSError)):
                        logger.warning(f"⚠️ Потеря соединения при выполнении команды: {e}")

                        # Возвращаем команду в очередь если есть попытки
                        if cmd.retry_count < self.MAX_RETRIES:
                            cmd.retry_count += 1
                            await self._command_queue.put(cmd)
                            logger.info(f"🔄 Повторная попытка {cmd.retry_count}/{self.MAX_RETRIES}")

                            # Пытаемся переподключиться
                            await self._attempt_reconnect()
                        else:
                            if not cmd.future.done():
                                cmd.future.set_exception(e)
                    else:
                        if not cmd.future.done():
                            cmd.future.set_exception(e)

                # Пауза между командами для стабильности
                await asyncio.sleep(0.02)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в воркере: {e}")
                await asyncio.sleep(0.1)

        logger.debug("🔄 Воркер очереди команд остановлен")

    async def _execute_single_command(self, cmd: QueuedCommand) -> str:
        """Выполняет одну команду с правильной обработкой"""
        if not self._writer:
            raise ConnectionError("Нет активного соединения")

        # 1. Очищаем входной буфер
        await self._clear_input_buffer()

        # 2. Отправляем команду
        command_bytes = (cmd.command + '\r\n').encode()
        self._writer.write(command_bytes)
        await self._writer.drain()
        self.stats['bytes_sent'] += len(command_bytes)

        logger.debug(f"📤 TX: {cmd.command}")

        # 3. Читаем ответ
        response = await self._read_until_prompt(cmd.timeout)
        self.stats['bytes_received'] += len(response.encode())

        # 4. Очищаем ответ
        cleaned = self._clean_response(response)

        logger.debug(f"📥 RX: {cleaned[:100]}")

        return cleaned

    async def _read_until_prompt(self, timeout: float = 5.0) -> str:
        """Читает данные до появления приглашения '>'"""
        response_chunks = []
        start_time = time.time()
        prompt_received = False

        while time.time() - start_time < timeout:
            try:
                # Ждём данные
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=min(timeout, 0.5)
                )

                if not chunk:
                    if response_chunks:
                        break
                    continue

                response_chunks.append(chunk.decode('utf-8', errors='ignore'))

                # Проверяем наличие приглашения
                if self.RESPONSE_PROMPT in chunk:
                    prompt_received = True
                    break

            except asyncio.TimeoutError:
                if response_chunks:
                    break
                continue

        if not response_chunks:
            raise TimeoutError("Нет ответа от устройства")

        return ''.join(response_chunks)

    async def _clear_input_buffer(self):
        """Очищает входной буфер от старых данных"""
        try:
            while True:
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=self.BUFFER_CLEAR_TIMEOUT
                )
                if not chunk:
                    break
                logger.debug(f"🗑️ Очищено из буфера: {len(chunk)} байт")
        except (asyncio.TimeoutError, Exception):
            pass

    def _clean_response(self, response: str) -> str:
        """Очищает ответ ELM327 от служебных символов"""
        # Убираем всё до последнего '>' (если есть несколько ответов)
        if '>' in response:
            # Берём ответ после последнего приглашения
            parts = response.rsplit('>', 1)
            if len(parts) > 1 and parts[0].strip():
                response = parts[0]  # Данные до последнего приглашения

        # Убираем приветствие ELM327 если оно есть
        if 'ELM327' in response:
            lines = response.split('\n')
            meaningful_lines = []
            for line in lines:
                cleaned = line.strip().replace('\r', '')
                if cleaned and 'ELM327' not in cleaned and cleaned != '>':
                    meaningful_lines.append(cleaned)
            response = ' '.join(meaningful_lines)

        # Финальная очистка
        response = response.replace('>', '').strip()
        response = response.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

        return response.strip()

    async def _heartbeat_loop(self):
        """Heartbeat для проверки соединения"""
        logger.debug("💓 Heartbeat запущен")

        while self.running and self.connected:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

            if not self.connected:
                break

            try:
                # Отправляем ATI для проверки
                response = await asyncio.wait_for(
                    self._execute_single_command(
                        QueuedCommand(command='ATI', timeout=2.0)
                    ),
                    timeout=3.0
                )

                if not response:
                    logger.warning("⚠️ Heartbeat: пустой ответ")
                    await self._handle_connection_lost()
                else:
                    logger.debug(f"💓 Heartbeat OK: {response[:50]}")

            except Exception as e:
                logger.warning(f"⚠️ Heartbeat failed: {e}")
                await self._handle_connection_lost()

        logger.debug("💓 Heartbeat остановлен")

    async def _handle_connection_lost(self):
        """Обрабатывает потерю соединения"""
        logger.warning("🔴 Соединение потеряно")

        self.connected = False

        if self.on_disconnect:
            try:
                self.on_disconnect()
            except:
                pass

        # Пытаемся переподключиться
        await self._attempt_reconnect()

    async def _attempt_reconnect(self):
        """Пытается переподключиться к устройству"""
        if self._reconnect_task and not self._reconnect_task.done():
            return

        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        """Цикл переподключения"""
        logger.info("🔄 Попытка переподключения...")

        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"🔄 Попытка {attempt + 1}/{self.MAX_RETRIES}")

                # Закрываем старое соединение
                if self._writer:
                    try:
                        self._writer.close()
                    except:
                        pass

                # Пробуем подключиться заново
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=10.0
                )

                self.connected = True
                self.stats['reconnects'] += 1

                logger.info(f"✅ Переподключение успешно (попытка {attempt + 1})")

                if self.on_reconnect:
                    try:
                        self.on_reconnect()
                    except:
                        pass

                return

            except Exception as e:
                logger.warning(f"⚠️ Попытка {attempt + 1} не удалась: {e}")

                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RECONNECT_DELAY)

        logger.error("❌ Все попытки переподключения исчерпаны")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return {
            **self.stats,
            'connected': self.connected,
            'queue_size': self._command_queue.qsize(),
            'host': self.host,
            'port': self.port,
        }

"""
TCP Сервер эмулятора ELM327
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from .data_generator import OBDDataGenerator, DrivingMode
from .vehicle_profile import VEHICLE_PROFILES

logger = logging.getLogger(__name__)


class ELM327EmulatorServer:
    """Сервер эмулятора ELM327"""

    def __init__(self, host: str = '0.0.0.0', port: int = 35000,
                 profile_name: str = 'toyota_camry'):
        self.host = host
        self.port = port
        self.profile_name = profile_name

        # Создаём генератор данных
        profile = VEHICLE_PROFILES.get(profile_name, VEHICLE_PROFILES['toyota_camry'])
        self.generator = OBDDataGenerator(profile)

        # Сервер
        self.server: Optional[asyncio.AbstractServer] = None
        self.clients: Dict[int, asyncio.StreamWriter] = {}
        self.client_counter = 0

        # Состояние
        self.running = False
        self.echo_enabled = False
        self.headers_enabled = False
        self.spaces_enabled = True
        self.linefeeds_enabled = True
        self.adaptive_timing = True
        self.protocol = '6'  # CAN 11/500 по умолчанию
        self.timeout = 100  # мс

        # Статистика
        self.stats = {
            'connections': 0,
            'commands': 0,
            'errors': 0,
            'start_time': time.time(),
        }

    async def start(self):
        """Запускает сервер"""
        self.running = True

        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )

        logger.info(f"Эмулятор ELM327 запущен на {self.host}:{self.port}")
        logger.info(f"Профиль автомобиля: {self.generator.profile.name}")

        # Запускаем обновление данных
        asyncio.create_task(self._update_loop())

        # Запускаем цикл смены режимов
        asyncio.create_task(self._mode_cycle())

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Останавливает сервер"""
        self.running = False

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Отключаем всех клиентов
        for writer in self.clients.values():
            try:
                writer.close()
            except:
                pass
        self.clients.clear()

        logger.info("Эмулятор остановлен")

    async def _update_loop(self):
        """Цикл обновления данных"""
        while self.running:
            try:
                self.generator.update(0.1)  # 10 Гц
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Ошибка обновления: {e}")

    async def _mode_cycle(self):
        """Циклически меняет режимы движения для реалистичности"""
        modes = [
            (DrivingMode.IDLE, 5),  # 5 секунд холостой ход
            (DrivingMode.CITY, 30),  # 30 секунд городской цикл
            (DrivingMode.ACCELERATION, 5),  # 5 секунд разгон
            (DrivingMode.CRUISE, 20),  # 20 секунд круиз
            (DrivingMode.DECELERATION, 3),  # 3 секунды замедление
            (DrivingMode.IDLE, 2),  # 2 секунды холостой ход
        ]

        mode_index = 0

        while self.running:
            mode, duration = modes[mode_index]
            self.generator.set_mode(mode)

            logger.debug(f"Режим: {mode.value} ({duration}с)")

            await asyncio.sleep(duration)
            mode_index = (mode_index + 1) % len(modes)

    async def _handle_client(self, reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter):
        """Обрабатывает подключение клиента"""
        self.client_counter += 1
        client_id = self.client_counter

        addr = writer.get_extra_info('peername')
        logger.info(f"Клиент #{client_id} подключен: {addr}")

        self.clients[client_id] = writer
        self.stats['connections'] += 1

        # Отправляем приглашение
        writer.write(b'ELM327 v1.5\r\n>')
        await writer.drain()

        try:
            while self.running:
                # Читаем команду
                data = await asyncio.wait_for(
                    reader.read(1024),
                    timeout=60.0
                )

                if not data:
                    break

                command = data.decode('utf-8', errors='ignore').strip()

                if command:
                    logger.debug(f"Клиент #{client_id}: {command}")
                    self.stats['commands'] += 1

                    # Обрабатываем команду
                    response = await self._process_command(command)

                    # Отправляем ответ
                    if response:
                        writer.write(response.encode())
                        await writer.drain()

        except asyncio.TimeoutError:
            logger.debug(f"Клиент #{client_id}: таймаут")
        except ConnectionResetError:
            logger.debug(f"Клиент #{client_id}: соединение сброшено")
        except Exception as e:
            logger.error(f"Ошибка клиента #{client_id}: {e}")
        finally:
            try:
                writer.close()
            except:
                pass
            self.clients.pop(client_id, None)
            logger.info(f"Клиент #{client_id} отключен")

    async def _process_command(self, command: str) -> str:
        """Обрабатывает команду ELM327"""
        command_upper = command.upper().strip()

        try:
            # AT команды
            if command_upper.startswith('AT'):
                return await self._handle_at_command(command_upper)

            # OBD2 команды
            elif command_upper.startswith('01 '):
                pid = command_upper[3:].strip()
                response = self.generator.get_obd_response(pid)
                return self._format_response(response)

            elif command_upper.startswith('02 '):
                pid = command_upper[3:].strip()
                response = self.generator.get_obd_response(pid)
                return self._format_response(response.replace('41', '42'))

            elif command_upper == '03':
                response = self.generator.get_dtc_response('03')
                return self._format_response(response)

            elif command_upper == '04':
                self.generator.state.dtc_codes = []
                self.generator.profile.mil_on = False
                return self._format_response('44')

            elif command_upper == '07':
                response = self.generator.get_dtc_response('07')
                return self._format_response(response)

            elif command_upper == '0A':
                response = self.generator.get_dtc_response('0A')
                return self._format_response(response)

            elif command_upper.startswith('09 '):
                info_type = command_upper[3:].strip()
                response = self.generator.get_vehicle_info_response(info_type)
                return self._format_response(response)

            else:
                return self._format_response('?')

        except Exception as e:
            logger.error(f"Ошибка обработки команды: {e}")
            self.stats['errors'] += 1
            return self._format_response('?')

    async def _handle_at_command(self, command: str) -> str:
        """Обрабатывает AT команды"""
        parts = command.split()
        cmd = parts[0]

        if cmd == 'ATZ':
            # Сброс
            self.echo_enabled = False
            self.headers_enabled = False
            self.spaces_enabled = True
            self.linefeeds_enabled = True
            self.protocol = '6'
            return '\r\n\r\nELM327 v1.5\r\n\r\n>'

        elif cmd == 'ATI':
            return f'ELM327 v1.5\r\n>'

        elif cmd == 'ATE0':
            self.echo_enabled = False
            return 'OK\r\n>'

        elif cmd == 'ATE1':
            self.echo_enabled = True
            return 'OK\r\n>'

        elif cmd == 'ATH0':
            self.headers_enabled = False
            return 'OK\r\n>'

        elif cmd == 'ATH1':
            self.headers_enabled = True
            return 'OK\r\n>'

        elif cmd == 'ATS0':
            self.spaces_enabled = False
            return 'OK\r\n>'

        elif cmd == 'ATS1':
            self.spaces_enabled = True
            return 'OK\r\n>'

        elif cmd == 'ATL0':
            self.linefeeds_enabled = False
            return 'OK\r\n>'

        elif cmd == 'ATL1':
            self.linefeeds_enabled = True
            return 'OK\r\n>'

        elif cmd == 'ATSP0':
            self.protocol = '0'
            return 'OK\r\n>'

        elif cmd == 'ATSP':
            if len(parts) > 1:
                self.protocol = parts[1]
            return 'OK\r\n>'

        elif cmd == 'ATDP':
            protocols = {
                '0': 'AUTO',
                '1': 'SAE J1850 PWM',
                '2': 'SAE J1850 VPW',
                '3': 'ISO 9141-2',
                '4': 'ISO 14230-4 KWP',
                '5': 'ISO 14230-4 KWP FAST',
                '6': 'ISO 15765-4 CAN11/500',
                '7': 'ISO 15765-4 CAN29/500',
                '8': 'ISO 15765-4 CAN11/250',
                '9': 'ISO 15765-4 CAN29/250',
                'A': 'SAE J1939 CAN',
            }
            return f'{protocols.get(self.protocol, "AUTO")}\r\n>'

        elif cmd == 'ATDPN':
            return f'{self.protocol}\r\n>'

        elif cmd == 'ATRV':
            voltage = self.generator.state.voltage
            return f'{voltage:.1f}V\r\n>'

        elif cmd == 'ATIGN':
            return 'ON\r\n>'

        elif cmd == 'ATAT0':
            self.adaptive_timing = False
            return 'OK\r\n>'

        elif cmd == 'ATAT1':
            self.adaptive_timing = True
            return 'OK\r\n>'

        elif cmd == 'ATST':
            if len(parts) > 1:
                try:
                    self.timeout = int(parts[1], 16)
                except:
                    pass
            return 'OK\r\n>'

        elif cmd == 'AT@1':
            return 'OBDLink ELM327 Compatible\r\n>'

        elif cmd == 'AT@2':
            return 'ELM327 v1.5 Emulator\r\n>'

        elif cmd == 'ATCAF0':
            return 'OK\r\n>'

        elif cmd == 'ATCAF1':
            return 'OK\r\n>'

        elif cmd == 'ATCF':
            return 'OK\r\n>'

        elif cmd == 'ATCM':
            return 'OK\r\n>'

        elif cmd == 'ATCRA':
            return 'OK\r\n>'

        elif cmd == 'ATSH':
            return 'OK\r\n>'

        elif cmd == 'ATFC':
            return 'OK\r\n>'

        elif cmd in ['ATPC', 'AT&W', 'ATWS']:
            return 'OK\r\n>'

        elif cmd == 'ATAL':
            return 'OK\r\n>'

        elif cmd == 'ATNL':
            return 'OK\r\n>'

        elif cmd == 'ATRD':
            return 'OK\r\n>'

        elif cmd == 'ATSD':
            return 'OK\r\n>'

        elif cmd == 'ATWM':
            return 'OK\r\n>'

        elif cmd == 'ATTP':
            return 'OK\r\n>'

        elif cmd == 'ATLP':
            return 'OK\r\n>'

        elif cmd == 'ATRTR':
            return 'OK\r\n>'

        elif cmd.startswith('ATDM'):
            return 'OK\r\n>'

        elif cmd.startswith('ATMP'):
            return 'OK\r\n>'

        elif cmd.startswith('ATSR'):
            return 'OK\r\n>'

        else:
            return '?\r\n>'

    def _format_response(self, response: str) -> str:
        """Форматирует ответ согласно настройкам ELM327"""
        result = response

        # Убираем пробелы если нужно
        if not self.spaces_enabled:
            result = result.replace(' ', '')

        # Добавляем переводы строк
        if self.linefeeds_enabled:
            result += '\r\n'

        # Добавляем приглашение
        result += '>'

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        uptime = time.time() - self.stats['start_time']
        return {
            **self.stats,
            'uptime': round(uptime, 1),
            'active_clients': len(self.clients),
            'vehicle': self.generator.profile.name,
            'mode': self.generator.mode.value,
            'state': self.generator.get_state_dict(),
        }
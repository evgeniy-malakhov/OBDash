"""
Менеджер устройств - центральное управление подключением
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime
import os

from .exceptions import (
    ELM327Error, ConnectionError, MonitoringError,
    DeviceNotFoundError, ScanError
)
from .connection import ELM327Protocol
from .scanner import AsyncDeviceScanner
from ..models.schemas import (
    DeviceInfo, DeviceStatus, MonitorConfig, MonitorStatus,
    ConnectionType, PIDValue, CommandResponse, DTCInfo
)
from ..obd.parser import AsyncOBDParser, DTCFormatter
from ..config import settings

logger = logging.getLogger(__name__)


class DeviceManager:
    """Менеджер ELM327 устройств с правильной архитектурой"""

    def __init__(self):
        self.scanner = AsyncDeviceScanner()
        self.protocol: Optional[ELM327Protocol] = None
        self.executor = None  # Будет создан после подключения
        self.parser = AsyncOBDParser()

        # Текущее устройство
        self.current_device: Optional[DeviceInfo] = None

        # Мониторинг
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitor_config: Optional[MonitorConfig] = None
        self.monitor_active = False

        # Callbacks для WebSocket
        self._data_callbacks: List[Callable] = []
        self._status_callbacks: List[Callable] = []
        self._error_callbacks: List[Callable] = []

        # Буфер данных
        self.data_buffer: List[Dict] = []

        # Статистика
        self.stats = {
            'commands_executed': 0,
            'data_points_collected': 0,
            'start_time': datetime.now(),
            'connection_state': 'disconnected',
        }

    @property
    def is_connected(self) -> bool:
        """Проверяет, подключено ли устройство"""
        return self.protocol is not None and self.protocol.connected

    async def scan_devices(self, types: Optional[List[ConnectionType]] = None) -> List[DeviceInfo]:
        """Сканирует доступные устройства"""
        self._notify_status({'action': 'scan_start'})
        devices = await self.scanner.scan_all(types)
        self._notify_status({
            'action': 'scan_complete',
            'count': len(devices),
            'devices': [d.model_dump() for d in devices]
        })
        return devices

    async def connect_device(self, device_id: str, protocol: str = 'auto') -> DeviceInfo:
        """Подключается к устройству"""
        device = self.scanner.get_device(device_id)
        if not device:
            raise DeviceNotFoundError(f"Устройство {device_id} не найдено")

        # Отключаем текущее если есть
        if self.protocol:
            await self.disconnect_device()

        logger.info(f"Подключение к устройству: {device.name}")
        self.stats['connection_state'] = 'connecting'

        # Создаём протокол
        host = device.address
        port = device.port or 35000

        self.protocol = ELM327Protocol(host, port, device)
        self.protocol.on_disconnect = self._on_device_disconnect
        self.protocol.on_reconnect = self._on_device_reconnect

        # Подключаемся
        await self.protocol.connect()

        # Инициализируем ELM327
        await self._initialize_elm327()

        # Обновляем информацию
        device.status = DeviceStatus.ONLINE
        device.connected_at = datetime.now()
        self.current_device = device
        self.stats['connection_state'] = 'connected'

        # Создаём исполнитель команд (lazy import)
        from ..obd.executor import CommandExecutor
        self.executor = CommandExecutor(self)

        self._notify_status({
            'action': 'connected',
            'device': device.model_dump()
        })

        logger.info(f"Устройство подключено: {device.name}")
        return device

    async def _initialize_elm327(self):
        """Инициализирует ELM327 после подключения"""
        logger.info("Инициализация ELM327...")

        init_sequence = [
            'ATZ', 'ATE0', 'ATL0', 'ATH0', 'ATS0', 'ATSP0'
        ]

        for cmd in init_sequence:
            try:
                response = await self.protocol.send_command(cmd, timeout=3.0)
                logger.debug(f"  {cmd}: {response[:30]}")
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning(f"  {cmd}: {e}")

        # Получаем информацию
        try:
            version = (await self.protocol.send_command('ATI')).strip()
            voltage = (await self.protocol.send_command('ATRV')).strip()
            protocol = (await self.protocol.send_command('ATDPN')).strip()

            logger.info(f"  Версия: {version}")
            logger.info(f"  Напряжение: {voltage}")
            logger.info(f"  Протокол: {protocol}")

            if self.current_device:
                self.current_device.protocol = protocol
                try:
                    self.current_device.voltage = float(voltage.replace('V', ''))
                except:
                    pass
        except:
            pass

        logger.info("Инициализация завершена")

    async def disconnect_device(self):
        """Отключает устройство"""
        if self.monitor_active:
            await self.stop_monitoring()

        if self.protocol:
            logger.info("Отключение устройства...")
            await self.protocol.disconnect()
            self.protocol = None

        self.executor = None
        self.current_device = None
        self.stats['connection_state'] = 'disconnected'

        self._notify_status({'action': 'disconnected'})
        logger.info("Устройство отключено")

    async def send_command(self, command: str, timeout: float = 5.0) -> str:
        """Отправляет команду устройству"""
        if not self.protocol or not self.protocol.connected:
            raise ConnectionError("Устройство не подключено")

        self.stats['commands_executed'] += 1

        try:
            result = await self.protocol.send_command(command, timeout)
            return result
        except Exception as e:
            self._notify_error({
                'type': 'command_error',
                'command': command,
                'error': str(e)
            })
            raise

    async def execute_command(self, command: str, timeout: float = 5.0) -> CommandResponse:
        """Выполняет команду и возвращает структурированный ответ"""
        start = datetime.now()

        try:
            response = await self.send_command(command, timeout)
            execution_time = (datetime.now() - start).total_seconds() * 1000

            result = CommandResponse(
                success=True,
                command=command,
                response=response,
                execution_time=execution_time,
            )

            self._notify_data({
                'type': 'command_response',
                'data': result.model_dump()
            })

            return result

        except Exception as e:
            execution_time = (datetime.now() - start).total_seconds() * 1000

            result = CommandResponse(
                success=False,
                command=command,
                response='',
                execution_time=execution_time,
                error=str(e),
            )

            return result

    async def read_pid(self, pid: str) -> Optional[PIDValue]:
        """Читает один PID"""
        response = await self.send_command(f'01 {pid}')

        if response and 'NO DATA' not in response.upper():
            pid_value = self.parser.parse_response(pid, response)

            if pid_value:
                self._add_to_buffer(pid_value.model_dump())
                self.stats['data_points_collected'] += 1
                return pid_value

        return None

    async def read_multiple_pids(self, pids: List[str]) -> List[PIDValue]:
        """Читает несколько PID последовательно"""
        results = []

        for pid in pids:
            try:
                pid_value = await self.read_pid(pid)
                if pid_value:
                    results.append(pid_value)
            except Exception as e:
                logger.debug(f"Ошибка чтения PID {pid}: {e}")

            await asyncio.sleep(0.03)

        return results

    async def read_errors(self, mode: str = '03') -> List[DTCInfo]:
        """Читает коды ошибок"""
        response = await self.send_command(mode)

        if response and 'NO DATA' not in response.upper():
            dtcs = DTCFormatter.parse_dtc_response(response, mode)

            result = []
            for dtc in dtcs:
                dtc_info = DTCInfo(
                    code=dtc.get('code', ''),
                    category=dtc.get('category', 'Неизвестно'),
                    description=dtc.get('description', '')
                )
                result.append(dtc_info)

            self._notify_data({
                'type': 'dtc_update',
                'mode': mode,
                'data': [d.model_dump() for d in result]
            })

            return result

        return []

    async def clear_errors(self) -> bool:
        """Сбрасывает ошибки"""
        response = await self.send_command('04')
        return '44' in response

    async def get_vehicle_info(self) -> Dict[str, str]:
        """Получает информацию об автомобиле"""
        info = {}

        queries = [
            ('09 02', 'vin'),
            ('09 0A', 'ecu_name'),
            ('ATI', 'elm_version'),
            ('ATRV', 'voltage'),
            ('ATDP', 'protocol'),
        ]

        for cmd, key in queries:
            try:
                response = await self.send_command(cmd)
                info[key] = response.strip() if response else 'N/A'
            except:
                info[key] = 'N/A'

        return info

    async def start_monitoring(self, config: MonitorConfig):
        """Запускает мониторинг"""
        if self.monitor_active:
            await self.stop_monitoring()

        if not self.is_connected:
            raise ConnectionError("Устройство не подключено")

        valid_pids = [p for p in config.pids if AsyncOBDParser.get_pid_info(p)]

        if not valid_pids:
            raise MonitoringError("Нет валидных PID")

        config.pids = valid_pids
        self.monitor_config = config
        self.monitor_active = True

        self.monitor_task = asyncio.create_task(self._monitor_loop())

        self._notify_status({
            'action': 'monitor_started',
            'config': config.model_dump()
        })

        logger.info(f"Мониторинг запущен: {config.pids}")

    async def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.monitor_active = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except:
                pass
            self.monitor_task = None

        self._notify_status({
            'action': 'monitor_stopped',
            'data_points': self.stats['data_points_collected']
        })

        logger.info("Мониторинг остановлен")

    async def _monitor_loop(self):
        """Цикл мониторинга"""
        start_time = datetime.now()

        try:
            while self.monitor_active and self.monitor_config:
                if self.monitor_config.duration:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed >= self.monitor_config.duration:
                        break

                results = await self.read_multiple_pids(self.monitor_config.pids)

                if results:
                    self._notify_data({
                        'type': 'pid_data',
                        'data': [r.model_dump() for r in results]
                    })

                await asyncio.sleep(self.monitor_config.interval)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")
            self.monitor_active = False

    def _on_device_disconnect(self):
        """Callback при отключении устройства"""
        logger.warning("Устройство отключилось")
        self.stats['connection_state'] = 'disconnected'
        if self.current_device:
            self.current_device.status = DeviceStatus.OFFLINE
        self._notify_status({'action': 'device_disconnected'})

    def _on_device_reconnect(self):
        """Callback при переподключении"""
        logger.info("Устройство переподключено")
        self.stats['connection_state'] = 'connected'
        if self.current_device:
            self.current_device.status = DeviceStatus.ONLINE
        self._notify_status({'action': 'device_reconnected'})

    def _add_to_buffer(self, data: Dict):
        """Добавляет данные в буфер"""
        data['timestamp'] = datetime.now().isoformat()
        self.data_buffer.append(data)
        if len(self.data_buffer) > settings.DATA_BUFFER_SIZE:
            self.data_buffer = self.data_buffer[-settings.DATA_BUFFER_SIZE:]

    def get_buffer_data(self, limit: int = 100) -> List[Dict]:
        return self.data_buffer[-limit:]

    def clear_buffer(self):
        self.data_buffer.clear()

    def get_monitor_status(self) -> MonitorStatus:
        return MonitorStatus(
            active=self.monitor_active,
            pids=self.monitor_config.pids if self.monitor_config else [],
            interval=self.monitor_config.interval if self.monitor_config else 0,
            data_points=self.stats['data_points_collected'],
            errors=0,
        )

    def get_system_info(self) -> Dict[str, Any]:
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()

        return {
            'app_name': settings.APP_NAME,
            'version': settings.APP_VERSION,
            'device_connected': self.is_connected,
            'device_info': self.current_device.model_dump() if self.current_device else None,
            'monitor_active': self.monitor_active,
            'uptime': round(uptime, 1),
            'commands_executed': self.stats['commands_executed'],
            'data_points_collected': self.stats['data_points_collected'],
            'connection_state': self.stats['connection_state'],
            'protocol_stats': self.protocol.get_stats() if self.protocol else None,
        }

    # WebSocket Callbacks
    def on_data(self, callback: Callable):
        if callback not in self._data_callbacks:
            self._data_callbacks.append(callback)

    def on_status(self, callback: Callable):
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)

    def on_error(self, callback: Callable):
        if callback not in self._error_callbacks:
            self._error_callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        for lst in [self._data_callbacks, self._status_callbacks, self._error_callbacks]:
            if callback in lst:
                lst.remove(callback)

    def _notify_data(self, message: Dict):
        message['timestamp'] = datetime.now().isoformat()
        for cb in self._data_callbacks[:]:
            try:
                cb(message)
            except:
                pass

    def _notify_status(self, message: Dict):
        message['timestamp'] = datetime.now().isoformat()
        for cb in self._status_callbacks[:]:
            try:
                cb(message)
            except:
                pass

    def _notify_error(self, message: Dict):
        message['timestamp'] = datetime.now().isoformat()
        for cb in self._error_callbacks[:]:
            try:
                cb(message)
            except:
                pass
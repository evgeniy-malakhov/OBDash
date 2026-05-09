"""
Асинхронный сканер устройств с поддержкой эмулятора
"""

import asyncio
import logging
import socket
from typing import List, Optional, Dict, Any
import serial.tools.list_ports

from .exceptions import DeviceNotFoundError
from ..models.schemas import DeviceInfo, ConnectionType, DeviceStatus

logger = logging.getLogger(__name__)


class AsyncDeviceScanner:
    """Асинхронный сканер устройств ELM327"""

    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}

    async def scan_all(self, types: Optional[List[ConnectionType]] = None) -> List[DeviceInfo]:
        """
        Сканирует все доступные устройства

        Args:
            types: Типы устройств для сканирования (если None - все)

        Returns:
            Список найденных устройств
        """
        if types is None:
            types = [ConnectionType.BLUETOOTH, ConnectionType.WIFI, ConnectionType.SERIAL]

        self.devices.clear()

        tasks = []

        if ConnectionType.BLUETOOTH in types:
            tasks.append(self._scan_bluetooth())

        if ConnectionType.WIFI in types:
            tasks.append(self._scan_wifi())

        if ConnectionType.SERIAL in types:
            tasks.append(self._scan_serial())

        # Запускаем параллельное сканирование
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_devices = []
        for result in results:
            if isinstance(result, list):
                all_devices.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Ошибка сканирования: {result}")

        # Регистрируем устройства
        for device in all_devices:
            device.status = DeviceStatus.OFFLINE
            self.devices[device.id] = device

        logger.info(f"Всего найдено устройств: {len(all_devices)}")
        for d in all_devices:
            logger.info(f"  - {d.name} ({d.type}): {d.address}")

        return all_devices

    async def _scan_bluetooth(self) -> List[DeviceInfo]:
        """Сканирует Bluetooth устройства"""
        devices = []

        try:
            from bleak import BleakScanner

            logger.info("Сканирование Bluetooth устройств...")

            bt_devices = await BleakScanner.discover(timeout=10.0)

            obd_keywords = [
                'obd', 'elm', 'vgate', 'car', 'auto', 'viecar',
                'obdii', 'scanner', 'vlinker', 'vlink', 'icar'
            ]

            for device in bt_devices:
                if device.name:
                    name_lower = device.name.lower()
                    if any(keyword in name_lower for keyword in obd_keywords):
                        device_info = DeviceInfo(
                            id=f"bt_{device.address}",
                            name=device.name,
                            address=device.address,
                            type=ConnectionType.BLUETOOTH,
                            details={
                                'rssi': getattr(device, 'rssi', None),
                                'metadata': getattr(device, 'metadata', {})
                            }
                        )
                        devices.append(device_info)
                        logger.info(f"Найдено Bluetooth: {device.name} ({device.address})")

        except ImportError:
            logger.warning("Модуль bleak не установлен. Bluetooth сканирование недоступно.")
        except Exception as e:
            logger.error(f"Ошибка сканирования Bluetooth: {e}")

        return devices

    async def _scan_wifi(self) -> List[DeviceInfo]:
        """Сканирует WiFi устройства и эмулятор"""
        devices = []

        # Стандартные адреса WiFi ELM327
        wifi_targets = [
            # Стандартные адреса ELM327 WiFi адаптеров
            ('192.168.0.10', 35000, 'WiFi ELM327 (стандартный)'),
            ('192.168.1.10', 35000, 'WiFi ELM327'),
            ('192.168.0.10', 23, 'WiFi ELM327 (Telnet)'),
            ('10.0.0.1', 35000, 'WiFi ELM327'),

            # Локальный эмулятор
            ('127.0.0.1', 35000, 'Локальный эмулятор ELM327'),
            ('localhost', 35000, 'Локальный эмулятор ELM327'),

            # Дополнительные порты для эмулятора
            ('127.0.0.1', 35001, 'Эмулятор ELM327 (порт 35001)'),
            ('localhost', 35001, 'Эмулятор ELM327 (порт 35001)'),
        ]

        logger.info(f"Сканирование WiFi устройств и эмуляторов ({len(wifi_targets)} целей)...")

        async def check_target(ip: str, port: int, name: str) -> Optional[DeviceInfo]:
            """Проверяет доступность устройства и что это ELM327"""
            try:
                # Подключаемся
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=2.0
                )

                # Ждём приветствие от ELM327
                try:
                    greeting = await asyncio.wait_for(
                        reader.read(256),
                        timeout=1.0
                    )

                    greeting_text = greeting.decode('utf-8', errors='ignore')

                    # Проверяем, что это действительно ELM327
                    if 'ELM' in greeting_text.upper() or '>' in greeting_text:
                        # Отправляем ATI для получения версии
                        writer.write(b'ATI\r\n')
                        await writer.drain()

                        try:
                            version_response = await asyncio.wait_for(
                                reader.read(256),
                                timeout=1.0
                            )
                            version_text = version_response.decode('utf-8', errors='ignore')

                            # Извлекаем версию
                            version = 'Unknown'
                            for line in version_text.split('\n'):
                                if 'ELM' in line.upper():
                                    version = line.strip()
                                    break

                            logger.info(f"Найден ELM327: {ip}:{port} - {version}")

                            writer.close()
                            await writer.wait_closed()

                            return DeviceInfo(
                                id=f"wifi_{ip}_{port}",
                                name=name,
                                address=ip,
                                type=ConnectionType.WIFI,
                                port=port,
                                details={
                                    'version': version,
                                    'is_emulator': 'emulator' in version.lower() or '127.0.0.1' in ip or 'localhost' in ip,
                                }
                            )
                        except:
                            pass

                except asyncio.TimeoutError:
                    pass

                # Закрываем если не ELM327
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass

                return None

            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return None
            except Exception as e:
                logger.debug(f"Ошибка проверки {ip}:{port}: {e}")
                return None

        # Проверяем все цели
        tasks = [check_target(ip, port, name) for ip, port, name in wifi_targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, DeviceInfo):
                devices.append(result)
            elif isinstance(result, Exception):
                logger.debug(f"Ошибка сканирования WiFi: {result}")

        if devices:
            logger.info(f"Найдено WiFi/эмуляторов: {len(devices)}")
        else:
            logger.info("WiFi устройства не найдены")

        return devices

    async def _scan_serial(self) -> List[DeviceInfo]:
        """Сканирует последовательные порты"""
        devices = []

        try:
            ports = await asyncio.to_thread(serial.tools.list_ports.comports)

            for port in ports:
                is_likely_obd = any(
                    keyword in (port.description + port.hardware_id).lower()
                    for keyword in ['obd', 'elm', 'ch340', 'cp210', 'ftdi', 'usb serial', 'usb-serial']
                )

                device_info = DeviceInfo(
                    id=f"serial_{port.device}",
                    name=port.description or f"Serial {port.device}",
                    address=port.device,
                    type=ConnectionType.SERIAL,
                    details={
                        'description': port.description,
                        'hardware_id': port.hardware_id,
                        'manufacturer': port.manufacturer,
                        'is_likely_obd': is_likely_obd
                    }
                )
                devices.append(device_info)
                logger.info(f"Найден Serial порт: {port.device} - {port.description}")

        except Exception as e:
            logger.error(f"Ошибка сканирования Serial: {e}")

        return devices

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Возвращает устройство по ID"""
        return self.devices.get(device_id)

    def get_all_devices(self) -> List[DeviceInfo]:
        """Возвращает все найденные устройства"""
        return list(self.devices.values())
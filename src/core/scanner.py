"""
Сканер для поиска ELM327 устройств
"""

import asyncio
import logging
from typing import List, Tuple, Optional, Dict
import serial.tools.list_ports
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from .exceptions import DeviceNotFoundError
from ..utils.helpers import ColorScheme, Spinner

logger = logging.getLogger(__name__)


class DeviceInfo:
    """Информация об устройстве ELM327"""

    def __init__(self, name: str, address: str, device_type: str,
                 port: Optional[int] = None, details: Optional[Dict] = None):
        self.name = name
        self.address = address
        self.device_type = device_type  # 'bluetooth', 'wifi', 'serial'
        self.port = port
        self.details = details or {}

    def __str__(self):
        if self.device_type == 'bluetooth':
            return f"{self.name} ({self.address})"
        elif self.device_type == 'wifi':
            return f"WiFi ELM327: {self.address}:{self.port}"
        else:
            return f"Serial: {self.address} - {self.details.get('description', '')}"

    def __repr__(self):
        return f"DeviceInfo({self.device_type}: {self.address})"


class DeviceScanner:
    """Сканер устройств ELM327"""

    def __init__(self):
        self.devices: List[DeviceInfo] = []

    def scan_all(self) -> List[DeviceInfo]:
        """Сканирует все доступные устройства"""
        print(f"\n{ColorScheme.info('🔍 Поиск устройств ELM327...')}")
        print(ColorScheme.DIM + "  Это может занять до 30 секунд..." + ColorScheme.RESET)

        self.devices = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._scan_bluetooth): 'Bluetooth',
                executor.submit(self._scan_wifi): 'WiFi',
                executor.submit(self._scan_serial): 'Serial',
            }

            for future in as_completed(futures):
                try:
                    devices = future.result()
                    self.devices.extend(devices)
                    device_type = futures[future]
                    if devices:
                        print(f"  {ColorScheme.success('✓')} Найдено {device_type}: {len(devices)} устройств(а)")
                    else:
                        print(f"  {ColorScheme.DIM}  {device_type}: устройства не найдены{ColorScheme.RESET}")
                except Exception as e:
                    device_type = futures[future]
                    print(f"  {ColorScheme.warning('!')} {device_type}: {str(e)}")

        if not self.devices:
            raise DeviceNotFoundError(
                "Не найдено ни одного ELM327 устройства.\n"
                "Проверьте:\n"
                "  1. Включено ли зажигание автомобиля\n"
                "  2. Подключен ли адаптер к OBD2 разъёму\n"
                "  3. Включен ли Bluetooth/WiFi на компьютере"
            )

        return self.devices

    def _scan_bluetooth(self) -> List[DeviceInfo]:
        """Сканирует Bluetooth устройства"""
        devices = []

        try:
            import asyncio
            from bleak import BleakScanner

            async def scan():
                return await BleakScanner.discover(timeout=10.0)

            bt_devices = asyncio.run(scan())

            obd_keywords = ['obd', 'elm', 'vgate', 'car', 'auto', 'viecar',
                            'obdii', 'scanner', 'vlinker', 'vlink']

            for device in bt_devices:
                if device.name:
                    name_lower = device.name.lower()
                    if any(keyword in name_lower for keyword in obd_keywords):
                        devices.append(DeviceInfo(
                            name=device.name,
                            address=device.address,
                            device_type='bluetooth',
                            details={'rssi': getattr(device, 'rssi', None)}
                        ))
        except ImportError:
            logger.warning("Модуль bleak не установлен. Поиск Bluetooth недоступен.")
        except Exception as e:
            logger.error(f"Ошибка сканирования Bluetooth: {e}")

        return devices

    def _scan_wifi(self) -> List[DeviceInfo]:
        """Сканирует WiFi устройства"""
        devices = []
        common_configs = [
            ('192.168.0.10', 35000),
            ('192.168.1.10', 35000),
            ('192.168.0.10', 23),
            ('10.0.0.1', 35000),
        ]

        def check_ip(ip: str, port: int) -> Optional[DeviceInfo]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((ip, port))
                sock.close()

                if result == 0:
                    return DeviceInfo(
                        name=f"WiFi ELM327",
                        address=ip,
                        device_type='wifi',
                        port=port
                    )
            except:
                pass
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_ip, ip, port) for ip, port in common_configs]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    devices.append(result)

        return devices

    def _scan_serial(self) -> List[DeviceInfo]:
        """Сканирует последовательные порты"""
        devices = []

        try:
            ports = serial.tools.list_ports.comports()

            for port in ports:
                # Проверяем, может ли это быть ELM327
                is_obd = any(keyword in (port.description + port.hardware_id).lower()
                             for keyword in ['obd', 'elm', 'ch340', 'cp210', 'ftdi', 'usb serial'])

                devices.append(DeviceInfo(
                    name=port.description,
                    address=port.device,
                    device_type='serial',
                    details={
                        'description': port.description,
                        'hardware_id': port.hardware_id,
                        'is_likely_obd': is_obd
                    }
                ))
        except Exception as e:
            logger.error(f"Ошибка сканирования Serial: {e}")

        return devices

    def display_devices(self):
        """Отображает найденные устройства"""
        if not self.devices:
            print(ColorScheme.warning("  Устройства не найдены"))
            return

        print(f"\n{ColorScheme.info('📱 Найденные устройства:')}")
        print("  " + "─" * 50)

        for i, device in enumerate(self.devices, 1):
            icon = {'bluetooth': '🔵', 'wifi': '📶', 'serial': '🔌'}.get(device.device_type, '❓')
            print(f"  [{ColorScheme.highlight(str(i))}] {icon} {device}")

        print("  " + "─" * 50)

    def select_device(self, index: Optional[int] = None) -> DeviceInfo:
        """Выбирает устройство по индексу или запрашивает у пользователя"""
        if not self.devices:
            raise DeviceNotFoundError("Нет доступных устройств")

        if len(self.devices) == 1:
            return self.devices[0]

        if index is not None:
            if 1 <= index <= len(self.devices):
                return self.devices[index - 1]
            raise ValueError(f"Индекс должен быть от 1 до {len(self.devices)}")

        while True:
            try:
                choice = input(f"\n  Выберите устройство [1-{len(self.devices)}]: ").strip()
                if choice.lower() == 'q':
                    raise KeyboardInterrupt()
                idx = int(choice)
                if 1 <= idx <= len(self.devices):
                    return self.devices[idx - 1]
                print(ColorScheme.warning(f"  Введите число от 1 до {len(self.devices)}"))
            except ValueError:
                print(ColorScheme.warning("  Неверный ввод. Введите число."))
import asyncio
import serial
import socket
import time
from typing import Dict, Optional, List, Tuple


class ELM327Connection:
    """Базовый класс для подключения к ELM327"""

    def __init__(self):
        self.connected = False
        self.protocol_version = None
        self.supported_pids = []

    def send_command(self, command: str) -> str:
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class ELM327Bluetooth(ELM327Connection):
    """Подключение через Bluetooth"""

    def __init__(self, address: str):
        super().__init__()
        self.address = address
        self.client = None

    async def connect(self):
        """Подключение к устройству"""
        from bleak import BleakClient

        print(f"🔄 Подключение к {self.address}...")
        self.client = BleakClient(self.address)
        await self.client.connect()
        self.connected = True
        print("✅ Подключено!")

        # Инициализация
        await self.initialize()

    async def send_command(self, command: str) -> str:
        """Отправка команды и получение ответа"""
        # ELM327 использует характеристики UART для обмена данными
        # UUID может отличаться в зависимости от устройства
        uart_service_uuid = "0000ffe0-0000-1000-8000-00805f9b34fb"
        uart_rx_char_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"

        command_bytes = (command + '\r').encode()
        await self.client.write_gatt_char(uart_rx_char_uuid, command_bytes)
        await asyncio.sleep(0.1)

        # Чтение ответа (нужно адаптировать под конкретное устройство)
        response = await self.client.read_gatt_char(uart_rx_char_uuid)
        return response.decode().strip()

    async def initialize(self):
        """Инициализация ELM327"""
        commands = ['ATZ', 'ATE0', 'ATL0', 'ATH0', 'ATS0', 'ATSP0']
        for cmd in commands:
            response = await self.send_command(cmd)
            print(f"  {cmd}: {response}")
            await asyncio.sleep(0.5)

    def close(self):
        if self.client:
            asyncio.create_task(self.client.disconnect())


class ELM327Serial(ELM327Connection):
    """Подключение через последовательный порт (USB/WiFi адаптер)"""

    def __init__(self, port: str, baudrate: int = 38400):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None

    def connect(self):
        """Подключение к последовательному порту"""
        print(f"🔄 Подключение к {self.port}...")
        self.serial_conn = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        self.connected = True
        print("✅ Подключено!")
        self.initialize()

    def send_command(self, command: str) -> str:
        """Отправка команды и получение ответа"""
        if not self.serial_conn:
            raise ConnectionError("Нет подключения")

        self.serial_conn.write((command + '\r\n').encode())
        time.sleep(0.1)

        response = ""
        while self.serial_conn.in_waiting:
            response += self.serial_conn.read().decode('utf-8', errors='ignore')

        return response.strip().replace('\r', '').replace('\n', '')

    def initialize(self):
        """Инициализация ELM327"""
        commands = [
            'ATZ',  # Сброс
            'ATE0',  # Эхо выключено
            'ATL0',  # Переводы строк выключены
            'ATH0',  # Заголовки выключены
            'ATS0',  # Пробелы выключены
            'ATSP0',  # Автоопределение протокола
        ]

        for cmd in commands:
            response = self.send_command(cmd)
            print(f"  {cmd}: {response}")
            time.sleep(0.5)

        # Получаем версию
        version = self.send_command('ATI')
        print(f"  Версия устройства: {version}")

    def close(self):
        if self.serial_conn:
            self.serial_conn.close()


class ELM327WiFi(ELM327Serial):
    """Подключение через WiFi"""

    def __init__(self, host: str, port: int = 35000):
        super().__init__(port=None)
        self.host = host
        self.port_num = port
        self.socket_conn = None

    def connect(self):
        """Подключение через WiFi"""
        print(f"🔄 Подключение к {self.host}:{self.port_num}...")
        self.socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_conn.settimeout(5)
        self.socket_conn.connect((self.host, self.port_num))
        self.connected = True
        print("✅ Подключено через WiFi!")
        self.initialize()

    def send_command(self, command: str) -> str:
        """Отправка команды через сокет"""
        if not self.socket_conn:
            raise ConnectionError("Нет подключения")

        self.socket_conn.send((command + '\r\n').encode())
        time.sleep(0.1)

        response = b""
        try:
            while True:
                data = self.socket_conn.recv(4096)
                if not data:
                    break
                response += data
        except socket.timeout:
            pass

        return response.decode('utf-8', errors='ignore').strip()

    def close(self):
        if self.socket_conn:
            self.socket_conn.close()
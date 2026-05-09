"""
Пользовательские исключения для ELM327 API
"""

from typing import Optional


class ELM327Error(Exception):
    """Базовое исключение ELM327"""

    def __init__(self, message: str = "Ошибка ELM327", code: str = "ELM327_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Сериализация в словарь"""
        return {
            'error': self.code,
            'message': self.message,
            'type': self.__class__.__name__,
        }


class ConnectionError(ELM327Error):
    """Ошибка подключения к устройству"""

    def __init__(self, message: str = "Ошибка подключения"):
        super().__init__(message, code="CONNECTION_ERROR")


class DeviceNotFoundError(ELM327Error):
    """Устройство не найдено"""

    def __init__(self, message: str = "Устройство не найдено"):
        super().__init__(message, code="DEVICE_NOT_FOUND")


class DeviceBusyError(ELM327Error):
    """Устройство занято"""

    def __init__(self, message: str = "Устройство занято другой операцией"):
        super().__init__(message, code="DEVICE_BUSY")


class CommandError(ELM327Error):
    """Ошибка выполнения команды"""

    def __init__(self, message: str = "Ошибка выполнения команды", command: Optional[str] = None):
        self.command = command
        msg = message
        if command:
            msg = f"{message}: {command}"
        super().__init__(msg, code="COMMAND_ERROR")


class ProtocolError(ELM327Error):
    """Ошибка протокола OBD2"""

    def __init__(self, message: str = "Ошибка протокола"):
        super().__init__(message, code="PROTOCOL_ERROR")


class ParseError(ELM327Error):
    """Ошибка парсинга данных"""

    def __init__(self, message: str = "Ошибка парсинга данных"):
        super().__init__(message, code="PARSE_ERROR")


class TimeoutError(ELM327Error):
    """Таймаут операции"""

    def __init__(self, message: str = "Таймаут операции"):
        super().__init__(message, code="TIMEOUT_ERROR")


class ValidationError(ELM327Error):
    """Ошибка валидации данных"""

    def __init__(self, message: str = "Ошибка валидации данных"):
        super().__init__(message, code="VALIDATION_ERROR")


class MonitoringError(ELM327Error):
    """Ошибка мониторинга"""

    def __init__(self, message: str = "Ошибка мониторинга"):
        super().__init__(message, code="MONITORING_ERROR")


class InitializationError(ELM327Error):
    """Ошибка инициализации"""

    def __init__(self, message: str = "Ошибка инициализации устройства"):
        super().__init__(message, code="INITIALIZATION_ERROR")


class ConfigurationError(ELM327Error):
    """Ошибка конфигурации"""

    def __init__(self, message: str = "Ошибка конфигурации"):
        super().__init__(message, code="CONFIGURATION_ERROR")


class WebSocketError(ELM327Error):
    """Ошибка WebSocket"""

    def __init__(self, message: str = "Ошибка WebSocket"):
        super().__init__(message, code="WEBSOCKET_ERROR")


class ScanError(ELM327Error):
    """Ошибка сканирования"""

    def __init__(self, message: str = "Ошибка сканирования устройств"):
        super().__init__(message, code="SCAN_ERROR")
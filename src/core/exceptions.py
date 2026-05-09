"""
Пользовательские исключения для ELM327 Scanner
"""

class ELM327Error(Exception):
    """Базовое исключение ELM327"""
    pass

class ConnectionError(ELM327Error):
    """Ошибка подключения к устройству"""
    pass

class DeviceNotFoundError(ELM327Error):
    """Устройство не найдено"""
    pass

class CommandError(ELM327Error):
    """Ошибка выполнения команды"""
    pass

class ParseError(ELM327Error):
    """Ошибка парсинга данных"""
    pass

class ProtocolError(ELM327Error):
    """Ошибка протокола OBD2"""
    pass

class TimeoutError(ELM327Error):
    """Таймаут операции"""
    pass

class ValidationError(ELM327Error):
    """Ошибка валидации данных"""
    pass
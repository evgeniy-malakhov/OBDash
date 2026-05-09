"""
Конфигурация приложения
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Настройки приложения"""

    # Приложение
    APP_NAME: str = "ELM327 OBD2 Scanner API"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "Профессиональный API для диагностики автомобилей через ELM327"
    DEBUG: bool = True

    # Сервер
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 10

    # ELM327
    DEFAULT_BAUDRATE: int = 38400
    COMMAND_TIMEOUT: float = 5.0
    RECONNECT_ATTEMPTS: int = 3
    RECONNECT_DELAY: float = 2.0

    # Мониторинг
    DEFAULT_MONITOR_INTERVAL: float = 0.5
    MAX_MONITOR_PIDS: int = 10
    DATA_BUFFER_SIZE: int = 1000

    # CORS - теперь с правильным типом
    CORS_ORIGINS: List[str] = ["*"]

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Данные
    DATA_DIR: str = "data"
    SESSION_DATA_DIR: str = "data/sessions"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Разрешаем любые дополнительные поля
        extra = "allow"


settings = Settings()

# Создаём необходимые директории
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.SESSION_DATA_DIR, exist_ok=True)
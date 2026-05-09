#!/usr/bin/env python3
"""
Скрипт для запуска сервера ELM327 OBD2 API
"""

import sys
import os
import signal
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app.config import settings


def main():
    """Запускает сервер"""
    print("=" * 60)
    print(f"Запуск {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 60)
    print(f"API: http://{settings.HOST}:{settings.PORT}")
    print(f"Swagger: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"ReDoc: http://{settings.HOST}:{settings.PORT}/redoc")
    print(f"WebSocket: ws://{settings.HOST}:{settings.PORT}{settings.API_PREFIX}/ws")
    print(f"Health: http://{settings.HOST}:{settings.PORT}/health")
    print("=" * 60)
    print("Нажмите CTRL+C для остановки сервера")
    print("=" * 60)

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
    )

    config = uvicorn.Config(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
        loop="asyncio",
    )

    server = uvicorn.Server(config)

    def handle_signal(signum, frame):
        print(f"\nПолучен сигнал {signum}, завершение...")
        server.should_exit = True

    signal.signal(signal.SIGINT, handle_signal)
    try:
        signal.signal(signal.SIGTERM, handle_signal)
    except:
        pass

    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("\nСервер остановлен пользователем")
    except Exception as e:
        print(f"\nОшибка сервера: {e}")
    finally:
        print("\n" + "=" * 60)
        print("Сервер остановлен")
        print("=" * 60)


if __name__ == "__main__":
    main()
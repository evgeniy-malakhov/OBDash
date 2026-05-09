"""
Главный файл FastAPI приложения
"""

import logging
import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .core.manager import DeviceManager
from .core.exceptions import ELM327Error
from .api.routes import router as api_router
from .api.websocket import router as ws_router, ws_manager


# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
)
logger = logging.getLogger(__name__)

# Глобальный менеджер устройств
device_manager = DeviceManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("=" * 60)
    logger.info(f"Запуск {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"API: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"Документация: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info("=" * 60)

    await ws_manager.start_heartbeat()

    try:
        yield
    finally:
        logger.info("Начинаем graceful shutdown...")

        if device_manager.monitor_active:
            try:
                await device_manager.stop_monitoring()
            except:
                pass

        if device_manager.is_connected:
            try:
                await device_manager.disconnect_device()
            except:
                pass

        await ws_manager.stop_heartbeat()
        await ws_manager.close_all("Server shutdown")

        stats = device_manager.get_system_info()
        logger.info(f"Команд выполнено: {stats['commands_executed']}")
        logger.info(f"Точек данных: {stats['data_points_collected']}")
        logger.info("Сервер остановлен")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(ws_router, prefix=settings.API_PREFIX)


@app.exception_handler(ELM327Error)
async def elm327_error_handler(request, exc: ELM327Error):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": exc.message,
            "error": exc.code,
            "data": None,
        }
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "device_connected": device_manager.is_connected,
    }


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
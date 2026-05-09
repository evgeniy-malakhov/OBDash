"""
REST API роуты
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ..core.manager import DeviceManager
from ..core.exceptions import ELM327Error, ConnectionError
from ..models.schemas import (
    APIResponse, CommandRequest, CommandResponse,
    DeviceInfo, MonitorConfig, MonitorStatus,
    PIDValue, DTCInfo, ScanRequest, ConnectRequest,
    OBDProtocol, ConnectionType,
)
from ..obd.parser import AsyncOBDParser
from ..config import settings
from .websocket import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def get_device_manager() -> DeviceManager:
    """Dependency для получения менеджера устройств"""
    from ..main import device_manager
    return device_manager


class CustomConnectRequest(BaseModel):
    """Запрос на кастомное подключение"""
    host: str = Field(..., description="IP адрес или хост")
    port: int = Field(35000, description="Порт")
    protocol: OBDProtocol = Field(default=OBDProtocol.AUTO)


# ============================================================
# СИСТЕМНЫЕ ЭНДПОИНТЫ
# ============================================================

@router.get("/system/info", response_model=APIResponse)
async def get_system_info(manager: DeviceManager = Depends(get_device_manager)):
    """Информация о системе"""
    info = manager.get_system_info()

    return APIResponse(
        success=True,
        message="Информация о системе",
        data=info,
    )


@router.get("/system/health", response_model=APIResponse)
async def api_health_check(manager: DeviceManager = Depends(get_device_manager)):
    """Проверка здоровья системы"""
    return APIResponse(
        success=manager.is_connected,
        message="Устройство подключено" if manager.is_connected else "Устройство не подключено",
        data={
            'device_connected': manager.is_connected,
            'monitor_active': manager.monitor_active,
            'connection_state': manager.stats.get('connection_state', 'unknown'),
            'ws_connections': ws_manager.connection_stats['current_connections'],
        }
    )


# ============================================================
# СКАНИРОВАНИЕ И ПОДКЛЮЧЕНИЕ
# ============================================================

@router.post("/scan", response_model=APIResponse)
async def scan_devices(
    request: ScanRequest = ScanRequest(),
    manager: DeviceManager = Depends(get_device_manager),
):
    """Сканирует доступные устройства"""
    try:
        devices = await manager.scan_devices(request.types)

        return APIResponse(
            success=True,
            message=f"Найдено устройств: {len(devices)}",
            data={
                'devices': [d.model_dump() for d in devices],
                'count': len(devices),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices", response_model=APIResponse)
async def get_devices(manager: DeviceManager = Depends(get_device_manager)):
    """Возвращает список найденных устройств"""
    devices = manager.scanner.get_all_devices()

    return APIResponse(
        success=True,
        message=f"Устройств: {len(devices)}",
        data={
            'devices': [d.model_dump() for d in devices],
        }
    )


@router.post("/connect", response_model=APIResponse)
async def connect_device(
    request: ConnectRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    """Подключается к устройству из результатов сканирования"""
    try:
        device = await manager.connect_device(request.device_id, request.protocol.value)

        return APIResponse(
            success=True,
            message=f"Подключено к {device.name}",
            data={'device': device.model_dump()},
        )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка подключения: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/custom", response_model=APIResponse)
async def connect_custom(
    request: CustomConnectRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    """Подключается к кастомному серверу (эмулятору или удалённому ELM327)"""
    try:
        from ..models.schemas import DeviceInfo, ConnectionType, DeviceStatus

        logger.info(f"Кастомное подключение к {request.host}:{request.port}")

        # Создаём виртуальное устройство
        device = DeviceInfo(
            id=f"custom_{request.host}_{request.port}",
            name=f"ELM327 ({request.host}:{request.port})",
            address=request.host,
            type=ConnectionType.WIFI,
            port=request.port,
            status=DeviceStatus.OFFLINE,
        )

        # Добавляем в сканер
        manager.scanner.devices[device.id] = device

        # Подключаемся
        connected_device = await manager.connect_device(device.id, request.protocol.value)

        return APIResponse(
            success=True,
            message=f"✅ Подключено к {request.host}:{request.port}",
            data={'device': connected_device.model_dump()},
        )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка кастомного подключения: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect", response_model=APIResponse)
async def disconnect_device(manager: DeviceManager = Depends(get_device_manager)):
    """Отключает устройство"""
    await manager.disconnect_device()

    return APIResponse(
        success=True,
        message="Устройство отключено",
    )


@router.get("/device/status", response_model=APIResponse)
async def get_device_status(manager: DeviceManager = Depends(get_device_manager)):
    """Возвращает статус устройства"""
    return APIResponse(
        success=True,
        message="Статус устройства",
        data={
            'connected': manager.is_connected,
            'connection_state': manager.stats.get('connection_state'),
            'device': manager.current_device.model_dump() if manager.current_device else None,
            'protocol_stats': manager.protocol.get_stats() if manager.protocol else None,
        }
    )


# ============================================================
# ВЫПОЛНЕНИЕ КОМАНД
# ============================================================

@router.post("/command", response_model=APIResponse)
async def execute_command(
    request: CommandRequest,
    manager: DeviceManager = Depends(get_device_manager),
):
    """Выполняет OBD2 или AT команду"""
    try:
        result = await manager.execute_command(request.command, request.timeout)

        return APIResponse(
            success=result.success,
            message="Команда выполнена" if result.success else "Ошибка выполнения",
            data=result.model_dump(),
            error=result.error if not result.success else None,
        )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pid/{pid}", response_model=APIResponse)
async def read_pid(
    pid: str,
    manager: DeviceManager = Depends(get_device_manager),
):
    """Читает один PID"""
    try:
        pid_value = await manager.read_pid(pid)

        if pid_value:
            return APIResponse(
                success=True,
                message=f"PID {pid} прочитан",
                data={'pid': pid_value.model_dump()},
            )
        else:
            return APIResponse(
                success=False,
                message=f"Не удалось прочитать PID {pid}",
                error="Нет данных или PID не поддерживается",
            )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pids", response_model=APIResponse)
async def read_multiple_pids(
    pids: str = Query(..., description="PID через запятую, например: 0C,0D,05"),
    manager: DeviceManager = Depends(get_device_manager),
):
    """Читает несколько PID"""
    pid_list = [p.strip() for p in pids.split(',')]

    try:
        results = await manager.read_multiple_pids(pid_list)

        return APIResponse(
            success=True,
            message=f"Прочитано PID: {len(results)}/{len(pid_list)}",
            data={
                'pids': [r.model_dump() for r in results],
                'requested': pid_list,
                'received': len(results),
            }
        )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pids/list", response_model=APIResponse)
async def get_available_pids():
    """Возвращает список всех доступных PID с описанием"""
    pids = AsyncOBDParser.format_pid_list()

    return APIResponse(
        success=True,
        message=f"Доступно PID: {len(pids)}",
        data={'pids': pids},
    )


# ============================================================
# КОДЫ ОШИБОК
# ============================================================

@router.get("/errors", response_model=APIResponse)
async def read_errors(
    mode: str = Query('03', description="Режим: 03, 07, 0A"),
    manager: DeviceManager = Depends(get_device_manager),
):
    """Читает коды ошибок"""
    try:
        errors = await manager.read_errors(mode)

        return APIResponse(
            success=True,
            message=f"Найдено ошибок: {len(errors)}",
            data={
                'errors': [e.model_dump() for e in errors],
                'count': len(errors),
                'mode': mode,
            }
        )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/errors/clear", response_model=APIResponse)
async def clear_errors(manager: DeviceManager = Depends(get_device_manager)):
    """Сбрасывает ошибки"""
    success = await manager.clear_errors()

    return APIResponse(
        success=success,
        message="Ошибки сброшены" if success else "Ошибка сброса",
    )


# ============================================================
# ИНФОРМАЦИЯ ОБ АВТОМОБИЛЕ
# ============================================================

@router.get("/vehicle/info", response_model=APIResponse)
async def get_vehicle_info(manager: DeviceManager = Depends(get_device_manager)):
    """Информация об автомобиле"""
    try:
        info = await manager.get_vehicle_info()

        return APIResponse(
            success=True,
            message="Информация об автомобиле",
            data=info,
        )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# МОНИТОРИНГ
# ============================================================

@router.post("/monitor/start", response_model=APIResponse)
async def start_monitoring(
    config: MonitorConfig,
    manager: DeviceManager = Depends(get_device_manager),
):
    """Запускает мониторинг в реальном времени"""
    try:
        await manager.start_monitoring(config)

        return APIResponse(
            success=True,
            message=f"Мониторинг запущен: {config.pids}",
            data={'config': config.model_dump(), 'status': 'started'},
        )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/stop", response_model=APIResponse)
async def stop_monitoring(manager: DeviceManager = Depends(get_device_manager)):
    """Останавливает мониторинг"""
    await manager.stop_monitoring()

    return APIResponse(
        success=True,
        message="Мониторинг остановлен",
    )


@router.get("/monitor/status", response_model=APIResponse)
async def get_monitor_status(manager: DeviceManager = Depends(get_device_manager)):
    """Возвращает статус мониторинга"""
    status = manager.get_monitor_status()

    return APIResponse(
        success=True,
        message="Статус мониторинга",
        data=status.model_dump(),
    )


@router.get("/monitor/data", response_model=APIResponse)
async def get_monitor_data(
    limit: int = Query(100, description="Количество записей"),
    manager: DeviceManager = Depends(get_device_manager),
):
    """Возвращает данные мониторинга из буфера"""
    data = manager.get_buffer_data(limit)

    return APIResponse(
        success=True,
        message=f"Записей в буфере: {len(data)}",
        data={'records': data, 'total': len(data), 'limit': limit},
    )


@router.delete("/monitor/data", response_model=APIResponse)
async def clear_monitor_data(manager: DeviceManager = Depends(get_device_manager)):
    """Очищает буфер данных"""
    manager.clear_buffer()

    return APIResponse(
        success=True,
        message="Буфер очищен",
    )


# ============================================================
# WEBSOCKET ИНФОРМАЦИЯ
# ============================================================

@router.get("/ws/stats", response_model=APIResponse)
async def get_websocket_stats():
    """Статистика WebSocket соединений"""
    stats = ws_manager.get_stats()

    return APIResponse(
        success=True,
        message="Статистика WebSocket",
        data=stats,
    )
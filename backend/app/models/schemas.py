"""
Pydantic модели данных
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class ConnectionType(str, Enum):
    """Тип подключения"""
    BLUETOOTH = "bluetooth"
    WIFI = "wifi"
    SERIAL = "serial"


class DeviceStatus(str, Enum):
    """Статус устройства"""
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ERROR = "error"
    SCANNING = "scanning"


class OBDProtocol(str, Enum):
    """Протоколы OBD2"""
    AUTO = "auto"
    J1850_PWM = "j1850_pwm"
    J1850_VPW = "j1850_vpw"
    ISO_9141 = "iso_9141"
    ISO_14230_KWP5 = "iso_14230_kwp5"
    ISO_14230_KWP_FAST = "iso_14230_kwp_fast"
    CAN_11_500 = "can_11_500"
    CAN_29_500 = "can_29_500"
    CAN_11_250 = "can_11_250"
    CAN_29_250 = "can_29_250"
    J1939 = "j1939"


class DeviceInfo(BaseModel):
    """Информация об устройстве"""
    id: str = Field(..., description="Уникальный идентификатор")
    name: str = Field(..., description="Имя устройства")
    address: str = Field(..., description="Адрес устройства")
    type: ConnectionType = Field(..., description="Тип подключения")
    port: Optional[int] = Field(None, description="Порт (для WiFi)")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    status: DeviceStatus = Field(default=DeviceStatus.OFFLINE)
    protocol: Optional[str] = None
    voltage: Optional[float] = None
    connected_at: Optional[datetime] = None


class CommandRequest(BaseModel):
    """Запрос на выполнение команды"""
    command: str = Field(..., description="OBD2 или AT команда")
    timeout: Optional[float] = Field(5.0, description="Таймаут в секундах")

    class Config:
        json_schema_extra = {
            "example": {
                "command": "01 0C",
                "timeout": 3.0
            }
        }


class CommandResponse(BaseModel):
    """Ответ на команду"""
    success: bool
    command: str
    response: str
    timestamp: datetime = Field(default_factory=datetime.now)
    execution_time: float = Field(0, description="Время выполнения в мс")
    error: Optional[str] = None


class PIDValue(BaseModel):
    """Значение PID"""
    pid: str
    name: str
    value: Any
    unit: str
    icon: str
    status: str = "NORMAL"  # NORMAL, WARNING, ERROR, UNKNOWN
    timestamp: datetime = Field(default_factory=datetime.now)
    min: Optional[float] = None
    max: Optional[float] = None
    description: Optional[str] = None


class DTCInfo(BaseModel):
    """Информация о коде ошибки"""
    code: str
    category: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.now)


class MonitorConfig(BaseModel):
    """Конфигурация мониторинга"""
    pids: List[str] = Field(..., description="Список PID для мониторинга")
    interval: float = Field(0.5, ge=0.1, le=10.0, description="Интервал обновления в секундах")
    duration: Optional[float] = Field(None, description="Длительность в секундах (None = бесконечно)")
    save_to_file: bool = Field(False, description="Сохранять в файл")


class MonitorStatus(BaseModel):
    """Статус мониторинга"""
    active: bool
    pids: List[str]
    interval: float
    started_at: Optional[datetime] = None
    data_points: int = 0
    errors: int = 0


class WebSocketMessage(BaseModel):
    """Сообщение WebSocket"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class APIResponse(BaseModel):
    """Стандартный ответ API"""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ScanRequest(BaseModel):
    """Запрос на сканирование"""
    types: List[ConnectionType] = Field(
        default=[ConnectionType.BLUETOOTH, ConnectionType.WIFI, ConnectionType.SERIAL],
        description="Типы устройств для сканирования"
    )

class CustomConnectRequest(BaseModel):
    """Запрос на кастомное подключение"""
    host: str = Field(..., description="IP адрес или хост")
    port: int = Field(35000, description="Порт")
    protocol: OBDProtocol = Field(default=OBDProtocol.AUTO)


class ConnectRequest(BaseModel):
    """Запрос на подключение"""
    device_id: str = Field(..., description="ID устройства из результатов сканирования")
    protocol: OBDProtocol = Field(default=OBDProtocol.AUTO)


class SystemInfo(BaseModel):
    """Информация о системе"""
    app_name: str
    version: str
    device_connected: bool
    device_info: Optional[DeviceInfo] = None
    monitor_active: bool
    uptime: float = 0
    commands_executed: int = 0
    data_points_collected: int = 0
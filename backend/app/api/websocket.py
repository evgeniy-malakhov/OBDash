"""
WebSocket обработчик для real-time данных
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from ..core.manager import DeviceManager
from ..models.schemas import WebSocketMessage, MonitorConfig
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketManager:
    """Менеджер WebSocket соединений"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_stats: Dict[str, Any] = {
            'total_connections': 0,
            'current_connections': 0,
            'messages_sent': 0,
        }
        self._heartbeat_task: asyncio.Task = None

    async def connect(self, websocket: WebSocket):
        """Принимает WebSocket соединение"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_stats['total_connections'] += 1
        self.connection_stats['current_connections'] = len(self.active_connections)

        logger.info(f"🔌 WebSocket подключен. Активных: {len(self.active_connections)}")

        # Отправляем приветственное сообщение
        await self._safe_send(websocket, {
            'type': 'connection',
            'data': {
                'status': 'connected',
                'message': 'Подключено к ELM327 OBD2 Server',
                'timestamp': datetime.now().isoformat(),
            }
        })

    async def disconnect(self, websocket: WebSocket):
        """Отключает WebSocket соединение"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_stats['current_connections'] = len(self.active_connections)
            logger.info(f"🔌 WebSocket отключен. Активных: {len(self.active_connections)}")

    async def _safe_send(self, websocket: WebSocket, message: Dict[str, Any]):
        """Безопасная отправка сообщения"""
        try:
            message['timestamp'] = datetime.now().isoformat()
            await websocket.send_text(json.dumps(message, ensure_ascii=False, default=str))
            self.connection_stats['messages_sent'] += 1
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки WebSocket: {e}")
            await self.disconnect(websocket)
            return False

    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Отправляет сообщение конкретному клиенту"""
        await self._safe_send(websocket, message)

    async def broadcast(self, message: Dict[str, Any]):
        """Отправляет сообщение всем подключенным клиентам"""
        disconnected = set()

        for connection in list(self.active_connections):
            success = await self._safe_send(connection, message)
            if not success:
                disconnected.add(connection)

        # Очищаем отключенные соединения
        for conn in disconnected:
            await self.disconnect(conn)

    async def broadcast_data(self, data: Dict[str, Any]):
        """Отправляет данные всем клиентам"""
        await self.broadcast(data)

    async def broadcast_status(self, status: Dict[str, Any]):
        """Отправляет статус всем клиентам"""
        await self.broadcast({
            'type': 'status',
            'data': status,
        })

    async def broadcast_error(self, error: Dict[str, Any]):
        """Отправляет ошибку всем клиентам"""
        await self.broadcast({
            'type': 'error',
            'data': error,
        })

    async def start_heartbeat(self):
        """Запускает heartbeat для проверки соединений"""
        async def heartbeat_loop():
            logger.info("💓 Heartbeat запущен")
            while True:
                try:
                    await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)

                    if not self.active_connections:
                        continue

                    disconnected = set()
                    for connection in list(self.active_connections):
                        success = await self._safe_send(connection, {
                            'type': 'heartbeat',
                            'timestamp': datetime.now().isoformat()
                        })
                        if not success:
                            disconnected.add(connection)

                    for conn in disconnected:
                        await self.disconnect(conn)

                except asyncio.CancelledError:
                    logger.info("💓 Heartbeat остановлен")
                    break
                except Exception as e:
                    logger.error(f"Ошибка heartbeat: {e}")

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def stop_heartbeat(self):
        """Останавливает heartbeat"""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("💓 Heartbeat остановлен")

    async def close_all(self, reason: str = "Server shutdown"):
        """Закрывает все соединения"""
        logger.info(f"Закрытие всех WebSocket соединений: {reason}")

        for connection in list(self.active_connections):
            try:
                await connection.close(code=1001, reason=reason)
            except Exception as e:
                logger.warning(f"Ошибка закрытия WebSocket: {e}")

        self.active_connections.clear()
        self.connection_stats['current_connections'] = 0
        logger.info("Все WebSocket соединения закрыты")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику WebSocket"""
        return self.connection_stats.copy()


# Глобальный экземпляр менеджера WebSocket
ws_manager = WebSocketManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Основной WebSocket эндпоинт для real-time данных
    """
    await ws_manager.connect(websocket)

    # Получаем менеджер устройств
    from ..main import device_manager as dm
    device_manager = dm

    # Регистрируем callback'и
    def on_data(message):
        asyncio.create_task(ws_manager.send_message(websocket, message))

    def on_status(message):
        asyncio.create_task(ws_manager.send_message(websocket, {
            'type': 'status',
            'data': message
        }))

    def on_error(message):
        asyncio.create_task(ws_manager.send_message(websocket, {
            'type': 'error',
            'data': message
        }))

    device_manager.on_data(on_data)
    device_manager.on_status(on_status)
    device_manager.on_error(on_error)

    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get('action', '')

                if action == 'ping':
                    await ws_manager.send_message(websocket, {
                        'type': 'pong',
                        'data': {'timestamp': datetime.now().isoformat()}
                    })

                elif action == 'command':
                    command = message.get('command', '')
                    timeout = message.get('timeout', 5.0)
                    response = await device_manager.execute_command(command, timeout)
                    await ws_manager.send_message(websocket, {
                        'type': 'command_response',
                        'data': response.model_dump()
                    })

                elif action == 'read_pid':
                    pid = message.get('pid', '')
                    pid_value = await device_manager.read_pid(pid)
                    if pid_value:
                        await ws_manager.send_message(websocket, {
                            'type': 'pid_data',
                            'data': {'pids': [pid_value.model_dump()]}
                        })

                elif action == 'read_pids':
                    pids = message.get('pids', [])
                    values = await device_manager.read_multiple_pids(pids)
                    await ws_manager.send_message(websocket, {
                        'type': 'pid_data',
                        'data': {'pids': [v.model_dump() for v in values]}
                    })

                elif action == 'read_errors':
                    mode = message.get('mode', '03')
                    errors = await device_manager.read_errors(mode)
                    await ws_manager.send_message(websocket, {
                        'type': 'dtc_data',
                        'data': {'errors': [e.model_dump() for e in errors]}
                    })

                elif action == 'start_monitor':
                    config = MonitorConfig(
                        pids=message.get('pids', ['0C', '0D', '05']),
                        interval=message.get('interval', 1.0),
                        duration=message.get('duration'),
                        save_to_file=message.get('save_to_file', False),
                    )
                    await device_manager.start_monitoring(config)
                    await ws_manager.send_message(websocket, {
                        'type': 'status',
                        'data': {'action': 'monitor_started', 'config': config.model_dump()}
                    })

                elif action == 'stop_monitor':
                    await device_manager.stop_monitoring()
                    await ws_manager.send_message(websocket, {
                        'type': 'status',
                        'data': {'action': 'monitor_stopped'}
                    })

                elif action == 'get_system_info':
                    info = device_manager.get_system_info()
                    await ws_manager.send_message(websocket, {
                        'type': 'system_info',
                        'data': info
                    })

                elif action == 'get_buffer':
                    limit = message.get('limit', 100)
                    buffer_data = device_manager.get_buffer_data(limit)
                    await ws_manager.send_message(websocket, {
                        'type': 'buffer_data',
                        'data': {'records': buffer_data, 'total': len(buffer_data)}
                    })

                else:
                    await ws_manager.send_message(websocket, {
                        'type': 'error',
                        'data': {'message': f'Неизвестное действие: {action}'}
                    })

            except json.JSONDecodeError:
                await ws_manager.send_message(websocket, {
                    'type': 'error',
                    'data': {'message': 'Неверный формат JSON'}
                })
            except Exception as e:
                logger.error(f"Ошибка WebSocket: {e}")
                await ws_manager.send_message(websocket, {
                    'type': 'error',
                    'data': {'message': str(e)}
                })

    except WebSocketDisconnect:
        logger.info("WebSocket клиент отключился")
    except Exception as e:
        logger.error(f"Ошибка WebSocket соединения: {e}")
    finally:
        # Убираем callback'и
        device_manager.remove_callback(on_data)
        device_manager.remove_callback(on_status)
        device_manager.remove_callback(on_error)

        await ws_manager.disconnect(websocket)
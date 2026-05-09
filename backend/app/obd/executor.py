"""
Исполнитель OBD2 команд
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from .parser import AsyncOBDParser, DTCFormatter
from ..models.schemas import PIDValue, CommandResponse, DTCInfo
from ..core.exceptions import CommandError

if TYPE_CHECKING:
    from ..core.manager import DeviceManager

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Исполнитель OBD2 и AT команд"""

    def __init__(self, device_manager: 'DeviceManager'):
        self.manager = device_manager
        self.parser = AsyncOBDParser()

    async def execute_raw(self, command: str, timeout: float = 5.0) -> CommandResponse:
        """Выполняет сырую команду"""
        return await self.manager.execute_command(command, timeout)

    async def read_pid(self, pid: str, timeout: float = 5.0) -> Optional[PIDValue]:
        """Читает один PID и парсит его"""
        return await self.manager.read_pid(pid)

    async def read_multiple_pids(self, pids: List[str], timeout: float = 5.0) -> List[PIDValue]:
        """Читает несколько PID"""
        return await self.manager.read_multiple_pids(pids)

    async def read_errors(self, mode: str = '03', timeout: float = 5.0) -> List[Dict]:
        """Читает коды ошибок"""
        dtc_list = await self.manager.read_errors(mode)
        return [d.model_dump() for d in dtc_list]

    async def get_mil_status(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Получает статус MIL"""
        response = await self.manager.send_command('01 01')
        if response:
            return DTCFormatter.get_mil_status(response)
        return {'error': 'Ошибка получения статуса MIL'}

    async def clear_errors(self, timeout: float = 10.0) -> bool:
        """Сбрасывает ошибки"""
        return await self.manager.clear_errors()

    async def get_vehicle_info(self, timeout: float = 5.0) -> Dict[str, str]:
        """Получает информацию об автомобиле"""
        return await self.manager.get_vehicle_info()

    async def get_supported_pids(self, timeout: float = 10.0) -> List[str]:
        """Определяет поддерживаемые PID"""
        supported = []
        pid_ranges = ['00', '20', '40', '60', '80', 'A0']

        for pid_range in pid_ranges:
            try:
                response = await self.manager.send_command(f'01 {pid_range}')
                if response:
                    clean = response.replace(' ', '').replace(f'41{pid_range}', '')
                    if len(clean) >= 8:
                        mask = int(clean[:8], 16)
                        for i in range(32):
                            if mask & (1 << (31 - i)):
                                supported.append(f'{int(pid_range, 16) + i:02X}')
            except Exception as e:
                logger.warning(f"Ошибка при запросе PID {pid_range}: {e}")

        return supported

    async def get_device_info(self, timeout: float = 5.0) -> Dict[str, str]:
        """Получает информацию об устройстве ELM327"""
        info = {}
        queries = [
            ('ATI', 'version'),
            ('ATRV', 'voltage'),
            ('ATDP', 'protocol_name'),
            ('ATDPN', 'protocol_number'),
        ]

        for command, key in queries:
            try:
                response = await self.manager.send_command(command)
                info[key] = response.strip() if response else 'N/A'
            except:
                info[key] = 'N/A'

        return info
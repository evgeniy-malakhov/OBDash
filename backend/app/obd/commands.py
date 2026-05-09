"""
База данных OBD2 команд для API
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class PIDInfo:
    """Информация о PID"""
    pid: str
    name: str
    description: str
    unit: str
    icon: str
    category: str
    range: tuple = (0, 0)
    warning_range: Optional[tuple] = None
    formula_description: str = ''
    bytes_count: int = 1
    priority: int = 10


class OBDCommandDatabase:
    """База данных OBD2 команд"""

    def __init__(self):
        self._build_database()

    def _build_database(self):
        """Строит базу данных"""
        self.pids: Dict[str, PIDInfo] = {}
        self.categories: Dict[str, List[str]] = {}

        # Категории
        categories = {
            'engine': '📊 Двигатель',
            'fuel': '⛽ Топливная система',
            'air': '💨 Впуск и воздух',
            'speed': '🏎️ Скорость',
            'o2': '🔬 Кислородные датчики',
            'electrical': '⚡ Электрика',
            'temperature': '🌡️ Температуры',
            'other': '📋 Прочее',
        }

        # PID база
        pid_data = [
            # (pid, name, description, unit, icon, category, range, warning_range, bytes)
            ('04', 'Нагрузка двигателя', 'Вычисленная нагрузка', '%', '⏱️', 'engine', (0, 100), (80, 100), 1),
            ('05', 'Температура ОЖ', 'Температура охлаждающей жидкости', '°C', '🌡️', 'temperature', (-40, 215),
             (105, 120), 1),
            ('0B', 'Давление впуска', 'MAP сенсор', 'kPa', '💨', 'air', (0, 255), None, 1),
            ('0C', 'Обороты двигателя', 'RPM коленвала', 'RPM', '⏱️', 'engine', (0, 16383), (6000, 16383), 2),
            ('0D', 'Скорость', 'Скорость автомобиля', 'km/h', '🏎️', 'speed', (0, 255), None, 1),
            ('0E', 'Угол зажигания', 'Опережение зажигания', '°', '⚡', 'engine', (-64, 63.5), None, 1),
            ('0F', 'Температура воздуха', 'Впускной воздух', '°C', '🌡️', 'temperature', (-40, 215), None, 1),
            ('10', 'MAF расход воздуха', 'Массовый расход', 'g/s', '💨', 'air', (0, 655), None, 2),
            ('11', 'Положение дросселя', 'TPS сенсор', '%', '🔧', 'air', (0, 100), None, 1),
            ('14', 'O2 B1S1', 'Напряжение датчика', 'V', '🔬', 'o2', (0, 1.275), None, 1),
            ('15', 'O2 B1S2', 'Напряжение датчика', 'V', '🔬', 'o2', (0, 1.275), None, 1),
            ('1F', 'Время работы', 'С последнего запуска', 'сек', '⏲️', 'engine', (0, 65535), None, 2),
            ('2F', 'Уровень топлива', 'В баке', '%', '🛢️', 'fuel', (0, 100), (0, 15), 1),
            ('06', 'STFT B1', 'Краткосрочная коррекция', '%', '📊', 'fuel', (-100, 99), (-25, 25), 1),
            ('07', 'LTFT B1', 'Долгосрочная коррекция', '%', '📈', 'fuel', (-100, 99), (-25, 25), 1),
            ('42', 'Напряжение ЭБУ', 'Питание контроллера', 'V', '⚡', 'electrical', (0, 65.5), (0, 11.5), 2),
            ('46', 'Температура окр.', 'Окружающая среда', '°C', '🌤️', 'temperature', (-40, 215), None, 1),
            ('5C', 'Температура масла', 'Моторное масло', '°C', '🛢️', 'temperature', (-40, 215), (120, 215), 1),
            ('5E', 'Расход топлива', 'Мгновенный расход', 'L/h', '⛽', 'fuel', (0, 3276), None, 2),
            ('44', 'Лямбда', 'Командная AFR', 'λ', '🔬', 'o2', (0, 2), None, 2),
            ('45', 'Дроссель отн.', 'Относительное положение', '%', '🔧', 'air', (0, 100), None, 1),
            ('4C', 'EGR команда', 'Клапан EGR', '%', '♻️', 'other', (0, 100), None, 1),
            ('5A', 'Педаль газа', 'Положение педали', '%', '🦶', 'engine', (0, 100), None, 1),
            ('31', 'Пробег после сброса', 'С последней очистки DTC', 'km', '🛣️', 'other', (0, 65535), None, 2),
            ('21', 'Пробег с MIL', 'С горящим Check Engine', 'km', '🛣️', 'other', (0, 65535), None, 2),
            ('30', 'Прогревы', 'После сброса ошибок', '', '🔄', 'other', (0, 255), None, 1),
        ]

        for data in pid_data:
            pid, name, desc, unit, icon, cat, range_val, warn, bytes_count = data
            self.pids[pid] = PIDInfo(
                pid=pid,
                name=name,
                description=desc,
                unit=unit,
                icon=icon,
                category=cat,
                range=range_val,
                warning_range=warn,
                bytes_count=bytes_count,
            )

            if cat not in self.categories:
                self.categories[cat] = []
            self.categories[cat].append(pid)

    def get_pid(self, pid: str) -> Optional[PIDInfo]:
        """Возвращает информацию о PID"""
        return self.pids.get(pid.upper())

    def get_all_pids(self) -> List[PIDInfo]:
        """Возвращает все PID"""
        return list(self.pids.values())

    def get_pids_by_category(self, category: str) -> List[PIDInfo]:
        """Возвращает PID в категории"""
        pid_list = self.categories.get(category, [])
        return [self.pids[pid] for pid in pid_list if pid in self.pids]

    def get_categories(self) -> Dict[str, str]:
        """Возвращает категории"""
        return self.categories

    def get_monitoring_presets(self) -> Dict[str, Dict]:
        """Возвращает пресеты для мониторинга"""
        return {
            'basic': {
                'name': 'Базовый',
                'description': 'Самые важные параметры',
                'pids': ['0C', '0D', '05'],
                'interval': 0.5,
            },
            'detailed': {
                'name': 'Расширенный',
                'description': 'Детальный мониторинг',
                'pids': ['0C', '0D', '05', '0B', '11', '04'],
                'interval': 1.0,
            },
            'fuel': {
                'name': 'Топливный',
                'description': 'Расход и коррекции',
                'pids': ['0C', '0D', '04', '06', '07', '2F', '5E'],
                'interval': 1.0,
            },
            'sensors': {
                'name': 'Датчики O2',
                'description': 'Кислородные датчики и AFR',
                'pids': ['14', '15', '24', '44'],
                'interval': 0.5,
            },
            'temperatures': {
                'name': 'Температуры',
                'description': 'Все температурные датчики',
                'pids': ['05', '0F', '46', '5C'],
                'interval': 1.0,
            },
        }


# Глобальный экземпляр базы команд
command_database = OBDCommandDatabase()
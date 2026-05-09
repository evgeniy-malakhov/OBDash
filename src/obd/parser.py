"""
Парсер OBD2 данных с формулами преобразования
"""

import struct
import logging
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValueStatus(Enum):
    """Статус значения"""
    NORMAL = '✅'
    WARNING = '⚠️'
    ERROR = '❌'
    UNKNOWN = '❓'


@dataclass
class ParsedValue:
    """Результат парсинга значения"""
    pid: str
    name: str
    value: Any
    unit: str
    icon: str
    status: ValueStatus
    raw_hex: str
    description: str = ''
    min_val: Optional[float] = None
    max_val: Optional[float] = None

    def __str__(self):
        if isinstance(self.value, float):
            value_str = f"{self.value:.1f}"
        elif isinstance(self.value, int):
            value_str = str(self.value)
        else:
            value_str = str(self.value)

        return f"{self.icon} {self.name}: {value_str} {self.unit} {self.status.value}"

    def to_dict(self) -> Dict:
        """Сериализация в словарь"""
        return {
            'pid': self.pid,
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'icon': self.icon,
            'status': self.status.name,
            'raw': self.raw_hex,
            'description': self.description,
            'min': self.min_val,
            'max': self.max_val,
        }


class OBDParser:
    """Парсер OBD2 PID данных с формулами"""

    # ============================================================
    # БАЗА ДАННЫХ PID С ФОРМУЛАМИ
    # ============================================================
    PID_DATABASE = {
        # === Датчики двигателя ===
        '04': {
            'name': 'Нагрузка двигателя',
            'unit': '%',
            'icon': '⏱️',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
            'warning_range': (80, 100),
            'description': 'Вычисленная нагрузка двигателя в процентах'
        },
        '05': {
            'name': 'Температура охлаждающей жидкости',
            'unit': '°C',
            'icon': '🌡️',
            'bytes': 1,
            'formula': lambda A: A - 40,
            'range': (-40, 215),
            'warning_range': (105, 120),
            'description': 'Температура двигателя. Норма 85-105°C'
        },
        '0B': {
            'name': 'Давление впускного коллектора',
            'unit': 'kPa',
            'icon': '💨',
            'bytes': 1,
            'formula': lambda A: A,
            'range': (0, 255),
            'description': 'Абсолютное давление во впускном коллекторе'
        },
        '0C': {
            'name': 'Обороты двигателя',
            'unit': 'RPM',
            'icon': '⏱️',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) / 4),
            'range': (0, 16383),
            'warning_range': (6000, 16383),
            'description': 'Частота вращения коленчатого вала'
        },
        '0F': {
            'name': 'Температура впускного воздуха',
            'unit': '°C',
            'icon': '🌡️',
            'bytes': 1,
            'formula': lambda A: A - 40,
            'range': (-40, 215),
            'description': 'Температура воздуха на впуске'
        },
        '46': {
            'name': 'Температура окружающей среды',
            'unit': '°C',
            'icon': '🌤️',
            'bytes': 1,
            'formula': lambda A: A - 40,
            'range': (-40, 215),
            'description': 'Температура окружающего воздуха'
        },
        '5C': {
            'name': 'Температура масла',
            'unit': '°C',
            'icon': '🛢️',
            'bytes': 1,
            'formula': lambda A: A - 40,
            'range': (-40, 215),
            'warning_range': (120, 215),
            'description': 'Температура моторного масла'
        },
        '33': {
            'name': 'Барометрическое давление',
            'unit': 'kPa',
            'icon': '🌡️',
            'bytes': 1,
            'formula': lambda A: A,
            'range': (0, 255),
            'description': 'Атмосферное давление'
        },
        '43': {
            'name': 'Абсолютная нагрузка двигателя',
            'unit': '%',
            'icon': '📊',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) * 100 / 255, 1),
            'range': (0, 25700),
            'description': 'Отношение текущего крутящего момента к максимальному'
        },
        '5D': {
            'name': 'Время впрыска топлива',
            'unit': 'ms',
            'icon': '💉',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) / 1000, 3),
            'range': (0, 65.535),
            'description': 'Длительность импульса форсунок'
        },

        # === Топливная система ===
        '03': {
            'name': 'Статус топливной системы',
            'unit': '',
            'icon': '⛽',
            'bytes': 2,
            'formula': None,  # Особая обработка
            'description': 'Режим работы топливной системы (Open/Closed loop)'
        },
        '06': {
            'name': 'Краткосрочная коррекция топлива (Bank 1)',
            'unit': '%',
            'icon': '📊',
            'bytes': 1,
            'formula': lambda A: round((A - 128) * 100 / 128, 1),
            'range': (-100, 99.2),
            'warning_range': (-25, 25),
            'description': 'Мгновенная коррекция подачи топлива. Норма ±10%'
        },
        '07': {
            'name': 'Долгосрочная коррекция топлива (Bank 1)',
            'unit': '%',
            'icon': '📈',
            'bytes': 1,
            'formula': lambda A: round((A - 128) * 100 / 128, 1),
            'range': (-100, 99.2),
            'warning_range': (-25, 25),
            'description': 'Долговременная адаптация топливной смеси'
        },
        '08': {
            'name': 'Краткосрочная коррекция топлива (Bank 2)',
            'unit': '%',
            'icon': '📊',
            'bytes': 1,
            'formula': lambda A: round((A - 128) * 100 / 128, 1),
            'range': (-100, 99.2),
        },
        '09': {
            'name': 'Долгосрочная коррекция топлива (Bank 2)',
            'unit': '%',
            'icon': '📈',
            'bytes': 1,
            'formula': lambda A: round((A - 128) * 100 / 128, 1),
            'range': (-100, 99.2),
        },
        '0A': {
            'name': 'Давление топлива',
            'unit': 'kPa',
            'icon': '⛽',
            'bytes': 1,
            'formula': lambda A: A * 3,
            'range': (0, 765),
            'description': 'Давление в топливной системе'
        },
        '2F': {
            'name': 'Уровень топлива',
            'unit': '%',
            'icon': '🛢️',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
            'warning_range': (0, 15),
            'description': 'Оставшееся топливо в баке'
        },
        '44': {
            'name': 'Командная лямбда',
            'unit': 'λ',
            'icon': '🔬',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) / 32768, 3),
            'range': (0, 2),
            'description': 'Запрошенное соотношение воздух/топливо. 1.0 = стехиометрия'
        },
        '5E': {
            'name': 'Расход топлива',
            'unit': 'L/h',
            'icon': '⛽',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) * 0.05, 2),
            'range': (0, 3276.75),
            'description': 'Мгновенный расход топлива'
        },
        '52': {
            'name': 'Этанол в топливе',
            'unit': '%',
            'icon': '🧪',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
            'description': 'Процентное содержание этанола'
        },

        # === Впуск и воздух ===
        '10': {
            'name': 'Массовый расход воздуха',
            'unit': 'g/s',
            'icon': '💨',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) / 100, 2),
            'range': (0, 655.35),
            'description': 'Количество воздуха, поступающего в двигатель'
        },
        '11': {
            'name': 'Абсолютное положение дросселя',
            'unit': '%',
            'icon': '🔧',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
            'description': 'Положение дроссельной заслонки'
        },
        '45': {
            'name': 'Относительное положение дросселя',
            'unit': '%',
            'icon': '🔧',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
        },
        '5A': {
            'name': 'Положение педали акселератора',
            'unit': '%',
            'icon': '🦶',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
            'description': 'Нажатие педали газа'
        },
        '4C': {
            'name': 'Команда управления EGR',
            'unit': '%',
            'icon': '♻️',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
            'description': 'Управление клапаном рециркуляции выхлопных газов'
        },
        '2C': {
            'name': 'Запрошенный EGR',
            'unit': '%',
            'icon': '♻️',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
        },

        # === Скорость и положение ===
        '0D': {
            'name': 'Скорость автомобиля',
            'unit': 'km/h',
            'icon': '🏎️',
            'bytes': 1,
            'formula': lambda A: A,
            'range': (0, 255),
            'description': 'Текущая скорость по данным ЭБУ'
        },
        '0E': {
            'name': 'Угол опережения зажигания',
            'unit': '°',
            'icon': '⚡',
            'bytes': 1,
            'formula': lambda A: round((A - 128) / 2, 1) if A <= 128 else round((A - 256) / 2, 1),
            'range': (-64, 63.5),
            'description': 'Угол опережения зажигания относительно ВМТ'
        },
        '1F': {
            'name': 'Время работы с запуска',
            'unit': 'сек',
            'icon': '⏲️',
            'bytes': 2,
            'formula': lambda A, B: A * 256 + B,
            'range': (0, 65535),
            'description': 'Сколько секунд работает двигатель после последнего запуска'
        },
        '21': {
            'name': 'Пробег с включённым MIL',
            'unit': 'km',
            'icon': '🛣️',
            'bytes': 2,
            'formula': lambda A, B: A * 256 + B,
            'range': (0, 65535),
            'description': 'Пройденное расстояние с горящим Check Engine'
        },
        '31': {
            'name': 'Пробег после сброса ошибок',
            'unit': 'km',
            'icon': '🛣️',
            'bytes': 2,
            'formula': lambda A, B: A * 256 + B,
            'range': (0, 65535),
        },
        '30': {
            'name': 'Прогревы после сброса ошибок',
            'unit': '',
            'icon': '🔄',
            'bytes': 1,
            'formula': lambda A: A,
            'range': (0, 255),
            'description': 'Количество циклов прогрева с момента сброса ошибок'
        },

        # === Кислородные датчики ===
        '14': {
            'name': 'Напряжение O2 Bank 1 Sensor 1',
            'unit': 'V',
            'icon': '🔬',
            'bytes': 1,
            'formula': lambda A: round(A / 200, 3),
            'range': (0, 1.275),
            'description': 'Передний кислородный датчик (до катализатора)'
        },
        '15': {
            'name': 'Напряжение O2 Bank 1 Sensor 2',
            'unit': 'V',
            'icon': '🔬',
            'bytes': 1,
            'formula': lambda A: round(A / 200, 3),
            'range': (0, 1.275),
            'description': 'Задний кислородный датчик (после катализатора)'
        },
        '18': {
            'name': 'Напряжение O2 Bank 2 Sensor 1',
            'unit': 'V',
            'icon': '🔬',
            'bytes': 1,
            'formula': lambda A: round(A / 200, 3),
            'range': (0, 1.275),
        },
        '19': {
            'name': 'Напряжение O2 Bank 2 Sensor 2',
            'unit': 'V',
            'icon': '🔬',
            'bytes': 1,
            'formula': lambda A: round(A / 200, 3),
            'range': (0, 1.275),
        },
        '24': {
            'name': 'Лямбда O2 Bank 1 Sensor 1',
            'unit': 'λ',
            'icon': '🔬',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) / 32768, 3),
            'range': (0, 2),
            'description': 'Текущее соотношение воздух/топливо с датчика'
        },
        '25': {
            'name': 'Лямбда O2 Bank 1 Sensor 2',
            'unit': 'λ',
            'icon': '🔬',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) / 32768, 3),
            'range': (0, 2),
        },
        '34': {
            'name': 'AFR O2 Bank 1 Sensor 1',
            'unit': '',
            'icon': '🔬',
            'bytes': 4,
            'formula': lambda A, B, C, D: round((A * 256 + B) / ((C * 256 + D) * 32768), 3),
            'range': (0, 2),
        },
        '35': {
            'name': 'AFR O2 Bank 1 Sensor 2',
            'unit': '',
            'icon': '🔬',
            'bytes': 4,
            'formula': lambda A, B, C, D: round((A * 256 + B) / ((C * 256 + D) * 32768), 3),
            'range': (0, 2),
        },

        # === Электрика ===
        '42': {
            'name': 'Напряжение модуля управления',
            'unit': 'V',
            'icon': '⚡',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) / 1000, 3),
            'range': (0, 65.535),
            'warning_range': (0, 11.5),
            'description': 'Напряжение питания ЭБУ'
        },
        '1C': {
            'name': 'Стандарт OBD',
            'unit': '',
            'icon': '📋',
            'bytes': 1,
            'formula': None,  # Особая обработка
            'description': 'Тип OBD сертификации'
        },

        # === Прочее ===
        '1E': {
            'name': 'Вспомогательные входы/выходы',
            'unit': '',
            'icon': '🔌',
            'bytes': 1,
            'formula': lambda A: 'PTO' if A & 0x01 else 'Off',
            'description': 'Статус дополнительного оборудования'
        },
        '3F': {
            'name': 'Индикатор Check Engine',
            'unit': '',
            'icon': '💡',
            'bytes': 1,
            'formula': None,
            'description': 'Статус лампы неисправности двигателя'
        },
    }

    # Статусы топливной системы
    FUEL_SYSTEM_STATUS = {
        0: 'Выключен двигатель',
        1: 'Open loop - недостаточно температуры',
        2: 'Closed loop (нормальная работа)',
        4: 'Open loop - высокая нагрузка/замедление',
        8: 'Open loop - обнаружена неисправность',
        16: 'Closed loop - ошибка датчика O2',
    }

    # Типы OBD стандартов
    OBD_STANDARDS = {
        1: 'OBD-II (CARB)',
        2: 'OBD (EPA)',
        3: 'OBD и OBD-II',
        4: 'OBD-I',
        5: 'Не OBD',
        6: 'EOBD (Европа)',
        7: 'EOBD и OBD-II',
        8: 'EOBD и OBD',
        9: 'EOBD, OBD, OBD-II',
        10: 'JOBD (Япония)',
        11: 'JOBD и OBD-II',
        12: 'JOBD и EOBD',
        13: 'JOBD, EOBD, OBD-II',
        14: 'Зарезервировано',
        15: 'Зарезервировано',
        16: 'Зарезервировано',
        17: 'Не соответствует OBD',
    }

    @classmethod
    def parse_response(cls, pid: str, raw_response: str) -> Optional[ParsedValue]:
        """
        Парсит ответ от ELM327 на запрос PID

        Args:
            pid: Идентификатор PID (например '0C')
            raw_response: Сырой ответ от устройства (например '41 0C 1A F8')

        Returns:
            ParsedValue или None при ошибке
        """
        pid_upper = pid.upper().replace(' ', '')

        # Проверяем, есть ли PID в базе
        if pid_upper not in cls.PID_DATABASE:
            logger.debug(f"PID {pid_upper} не найден в базе данных")
            return None

        pid_info = cls.PID_DATABASE[pid_upper]

        try:
            # Очищаем ответ
            clean_response = raw_response.replace(' ', '').replace('\r', '').replace('\n', '')

            # Проверяем на NO DATA
            if 'NODATA' in clean_response.upper() or '?' in clean_response:
                return ParsedValue(
                    pid=pid_upper,
                    name=pid_info['name'],
                    value='Нет данных',
                    unit=pid_info['unit'],
                    icon=pid_info['icon'],
                    status=ValueStatus.UNKNOWN,
                    raw_hex=raw_response,
                    description=pid_info.get('description', ''),
                )

            # Проверяем наличие ответа 41 (режим 01)
            if '41' in clean_response:
                # Убираем 41 и PID из ответа
                data_part = clean_response.replace(f'41{pid_upper}', '')
            else:
                data_part = clean_response

            # Конвертируем HEX в байты
            bytes_list = []
            for i in range(0, len(data_part), 2):
                if i + 1 < len(data_part):
                    bytes_list.append(int(data_part[i:i + 2], 16))

            if not bytes_list:
                return None

            # Обработка особых случаев
            if pid_upper == '03':
                # Статус топливной системы
                status_a = cls.FUEL_SYSTEM_STATUS.get(bytes_list[0], f'Неизвестно ({bytes_list[0]})')
                status_b = cls.FUEL_SYSTEM_STATUS.get(bytes_list[1], '') if len(bytes_list) > 1 else ''
                value = status_a
                if status_b:
                    value += f' | Bank 2: {status_b}'

            elif pid_upper == '1C':
                # Стандарт OBD
                value = cls.OBD_STANDARDS.get(bytes_list[0], f'Неизвестно ({bytes_list[0]})')

            elif pid_upper == '3F':
                # Check Engine
                value = 'ВКЛЮЧЕН' if bytes_list[0] & 0x80 else 'Выключен'

            elif pid_info['formula']:
                # Стандартная формула
                required_bytes = pid_info['bytes']
                if len(bytes_list) >= required_bytes:
                    value = pid_info['formula'](*bytes_list[:required_bytes])
                else:
                    return None
            else:
                value = ' '.join(f'{b:02X}' for b in bytes_list)

            # Определяем статус значения
            status = ValueStatus.NORMAL
            if 'warning_range' in pid_info:
                warn_min, warn_max = pid_info['warning_range']
                if isinstance(value, (int, float)):
                    if value < warn_min or value > warn_max:
                        status = ValueStatus.WARNING

            if 'range' in pid_info:
                val_min, val_max = pid_info['range']
                if isinstance(value, (int, float)):
                    if value < val_min or value > val_max:
                        status = ValueStatus.ERROR

            return ParsedValue(
                pid=pid_upper,
                name=pid_info['name'],
                value=value,
                unit=pid_info['unit'],
                icon=pid_info['icon'],
                status=status,
                raw_hex=raw_response,
                description=pid_info.get('description', ''),
                min_val=pid_info.get('range', (None, None))[0],
                max_val=pid_info.get('range', (None, None))[1],
            )

        except Exception as e:
            logger.error(f"Ошибка парсинга PID {pid_upper}: {e}")
            return ParsedValue(
                pid=pid_upper,
                name=pid_info['name'],
                value=f'Ошибка: {str(e)}',
                unit=pid_info['unit'],
                icon=pid_info['icon'],
                status=ValueStatus.ERROR,
                raw_hex=raw_response,
            )

    @classmethod
    def get_supported_pids(cls) -> List[str]:
        """Возвращает список всех поддерживаемых PID"""
        return list(cls.PID_DATABASE.keys())

    @classmethod
    def get_pid_info(cls, pid: str) -> Optional[Dict]:
        """Возвращает информацию о PID"""
        return cls.PID_DATABASE.get(pid.upper())


class DTCFormatter:
    """Форматирование кодов ошибок"""

    DTC_CATEGORIES = {
        'P0': 'Powertrain - Стандартный',
        'P1': 'Powertrain - Производитель',
        'P2': 'Powertrain - Стандартный',
        'P3': 'Powertrain - Производитель/Зарезервирован',
        'C0': 'Chassis - Стандартный',
        'C1': 'Chassis - Производитель',
        'B0': 'Body - Стандартный',
        'B1': 'Body - Производитель',
        'U0': 'Network - Стандартный',
        'U1': 'Network - Производитель',
    }

    DTC_DESCRIPTIONS = {
        'P0100': 'Неисправность цепи MAF/VAF датчика',
        'P0101': 'Диапазон/производительность MAF датчика',
        'P0102': 'Низкий сигнал MAF датчика',
        'P0103': 'Высокий сигнал MAF датчика',
        'P0110': 'Неисправность цепи датчика температуры впуска',
        'P0111': 'Диапазон датчика температуры впуска',
        'P0112': 'Низкий сигнал температуры впуска',
        'P0113': 'Высокий сигнал температуры впуска',
        'P0115': 'Неисправность цепи датчика температуры ОЖ',
        'P0116': 'Диапазон датчика температуры ОЖ',
        'P0117': 'Низкий сигнал температуры ОЖ',
        'P0118': 'Высокий сигнал температуры ОЖ',
        'P0120': 'Неисправность датчика положения дросселя',
        'P0121': 'Диапазон датчика положения дросселя',
        'P0122': 'Низкий сигнал датчика дросселя',
        'P0123': 'Высокий сигнал датчика дросселя',
        'P0130': 'Неисправность цепи O2 датчика B1S1',
        'P0131': 'Низкое напряжение O2 B1S1',
        'P0132': 'Высокое напряжение O2 B1S1',
        'P0133': 'Медленный отклик O2 B1S1',
        'P0134': 'Нет активности O2 B1S1',
        'P0135': 'Неисправность подогрева O2 B1S1',
        'P0136': 'Неисправность цепи O2 B1S2',
        'P0137': 'Низкое напряжение O2 B1S2',
        'P0138': 'Высокое напряжение O2 B1S2',
        'P0139': 'Медленный отклик O2 B1S2',
        'P0140': 'Нет активности O2 B1S2',
        'P0141': 'Неисправность подогрева O2 B1S2',
        'P0171': 'Слишком бедная смесь (Bank 1)',
        'P0172': 'Слишком богатая смесь (Bank 1)',
        'P0173': 'Слишком бедная смесь (Bank 2)',
        'P0174': 'Слишком богатая смесь (Bank 2)',
        'P0201': 'Неисправность форсунки цилиндра 1',
        'P0202': 'Неисправность форсунки цилиндра 2',
        'P0203': 'Неисправность форсунки цилиндра 3',
        'P0204': 'Неисправность форсунки цилиндра 4',
        'P0300': 'Случайные/множественные пропуски зажигания',
        'P0301': 'Пропуски зажигания в цилиндре 1',
        'P0302': 'Пропуски зажигания в цилиндре 2',
        'P0303': 'Пропуски зажигания в цилиндре 3',
        'P0304': 'Пропуски зажигания в цилиндре 4',
        'P0420': 'Эффективность катализатора ниже порога (Bank 1)',
        'P0430': 'Эффективность катализатора ниже порога (Bank 2)',
        'P0440': 'Неисправность системы улавливания паров топлива',
        'P0442': 'Малая утечка в системе EVAP',
        'P0455': 'Большая утечка в системе EVAP',
        'P0500': 'Неисправность датчика скорости',
        'P0505': 'Неисправность системы холостого хода',
        'P0601': 'Ошибка контрольной суммы ROM',
        'P0606': 'Неисправность процессора PCM',
        'P0700': 'Неисправность системы управления трансмиссией',
        'P0715': 'Неисправность датчика скорости турбины',
        'P0720': 'Неисправность датчика выходной скорости',
    }

    @classmethod
    def format_dtc(cls, raw_hex: str) -> Dict[str, str]:
        """
        Конвертирует сырой HEX код в DTC формат
        Пример: '0104' -> 'P0104'
        """
        try:
            if len(raw_hex) < 4:
                return {'code': raw_hex, 'error': 'Слишком короткий код'}

            # Первые два байта определяют префикс
            first_byte = int(raw_hex[0:2], 16)
            second_byte = int(raw_hex[2:4], 16)

            # Определяем тип кода
            dtc_prefixes = {
                0x00: 'P0', 0x01: 'P0', 0x02: 'P0', 0x03: 'P0',
                0x04: 'C0', 0x05: 'C0', 0x06: 'C0', 0x07: 'C0',
                0x08: 'B0', 0x09: 'B0', 0x0A: 'B0', 0x0B: 'B0',
                0x0C: 'U0', 0x0D: 'U0', 0x0E: 'U0', 0x0F: 'U0',
            }

            prefix = dtc_prefixes.get(first_byte >> 4, 'P0')

            # Формируем код
            dtc_code = f"{prefix}{first_byte & 0x0F:01X}{second_byte:02X}"

            # Ищем описание
            description = cls.DTC_DESCRIPTIONS.get(dtc_code, '')

            # Определяем категорию
            prefix_2 = dtc_code[:2]
            category = cls.DTC_CATEGORIES.get(prefix_2, 'Неизвестная категория')

            return {
                'code': dtc_code,
                'category': category,
                'description': description,
                'raw': raw_hex,
            }

        except Exception as e:
            return {
                'code': raw_hex,
                'error': f'Ошибка форматирования: {str(e)}',
                'raw': raw_hex,
            }

    @classmethod
    def parse_dtc_response(cls, response: str, mode: str = '03') -> List[Dict[str, str]]:
        """
        Парсит ответ с кодами ошибок от ELM327

        Args:
            response: Ответ от устройства
            mode: Режим (03, 07, 0A)

        Returns:
            Список расшифрованных кодов ошибок
        """
        codes = []

        # Очищаем ответ
        clean = response.replace(' ', '').replace('\r', '').replace('\n', '')

        # Проверяем, есть ли ошибки
        if 'NODATA' in clean.upper() or 'OK' in clean.upper() or len(clean) < 4:
            return codes

        # Определяем префикс ответа в зависимости от режима
        mode_prefixes = {'03': '43', '07': '47', '0A': '4A'}
        expected_prefix = mode_prefixes.get(mode, '43')

        # Убираем префикс ответа если есть
        if expected_prefix in clean:
            clean = clean.replace(expected_prefix, '')

        # Извлекаем коды (каждый код - 4 символа HEX)
        for i in range(0, len(clean), 4):
            if i + 4 <= len(clean):
                code_hex = clean[i:i + 4]
                if code_hex != '0000' and len(code_hex) == 4:
                    dtc = cls.format_dtc(code_hex)
                    codes.append(dtc)

        return codes

    @classmethod
    def get_mil_status(cls, response: str) -> Dict[str, Any]:
        """
        Определяет статус индикатора MIL из ответа 01 01
        """
        clean = response.replace(' ', '').replace('41', '').replace('01', '')

        if len(clean) < 8:
            return {'error': 'Неверный формат ответа'}

        try:
            mil_byte = int(clean[0:2], 16)

            return {
                'mil_on': bool(mil_byte & 0x80),
                'dtc_count': mil_byte & 0x7F,
                'raw': clean,
            }
        except:
            return {'error': 'Ошибка парсинга MIL'}
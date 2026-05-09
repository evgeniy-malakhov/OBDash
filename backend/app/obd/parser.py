"""
Асинхронный парсер OBD2 данных
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

from ..models.schemas import PIDValue

logger = logging.getLogger(__name__)


class AsyncOBDParser:
    """Асинхронный парсер OBD2 данных"""

    # База данных PID с формулами (аналогична консольной версии)
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
        '0D': {
            'name': 'Скорость автомобиля',
            'unit': 'km/h',
            'icon': '🏎️',
            'bytes': 1,
            'formula': lambda A: A,
            'range': (0, 255),
            'description': 'Текущая скорость по данным ЭБУ'
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
        '5E': {
            'name': 'Расход топлива',
            'unit': 'L/h',
            'icon': '⛽',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) * 0.05, 2),
            'range': (0, 3276.75),
            'description': 'Мгновенный расход топлива'
        },
        '0E': {
            'name': 'Угол опережения зажигания',
            'unit': '°',
            'icon': '⚡',
            'bytes': 1,
            'formula': lambda A: round(A / 2 - 64, 1),
            'range': (-64, 63.5),
            'description': 'Угол опережения зажигания'
        },
        '1F': {
            'name': 'Время работы с запуска',
            'unit': 'сек',
            'icon': '⏲️',
            'bytes': 2,
            'formula': lambda A, B: A * 256 + B,
            'range': (0, 65535),
            'description': 'Время работы двигателя после запуска'
        },
        '31': {
            'name': 'Пробег после сброса ошибок',
            'unit': 'km',
            'icon': '🛣️',
            'bytes': 2,
            'formula': lambda A, B: A * 256 + B,
            'range': (0, 65535),
            'description': 'Пройденное расстояние после сброса ошибок'
        },
        '44': {
            'name': 'Командная лямбда',
            'unit': 'λ',
            'icon': '🔬',
            'bytes': 2,
            'formula': lambda A, B: round((A * 256 + B) / 32768, 3),
            'range': (0, 2),
            'description': 'Запрошенное соотношение воздух/топливо'
        },
        '45': {
            'name': 'Относительное положение дросселя',
            'unit': '%',
            'icon': '🔧',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
            'description': 'Относительное положение дроссельной заслонки'
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
        '5A': {
            'name': 'Положение педали акселератора',
            'unit': '%',
            'icon': '🦶',
            'bytes': 1,
            'formula': lambda A: round(A * 100 / 255, 1),
            'range': (0, 100),
            'description': 'Нажатие педали газа'
        },
    }

    # Статусы топливной системы
    FUEL_SYSTEM_STATUS = {
        0: 'Выключен двигатель',
        1: 'Open loop - прогрев',
        2: 'Closed loop (норма)',
        4: 'Open loop - высокая нагрузка',
        8: 'Open loop - ошибка',
        16: 'Closed loop - ошибка O2',
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
    }

    @classmethod
    def parse_response(cls, pid: str, raw_response: str) -> Optional[PIDValue]:
        """
        Парсит ответ от ELM327 на запрос PID

        Args:
            pid: Идентификатор PID
            raw_response: Сырой ответ от устройства

        Returns:
            Parsed PIDValue или None
        """
        pid_upper = pid.upper().replace(' ', '')

        if pid_upper not in cls.PID_DATABASE:
            logger.debug(f"PID {pid_upper} не найден в базе")
            return None

        pid_info = cls.PID_DATABASE[pid_upper]

        try:
            # Очищаем ответ
            clean_response = raw_response.replace(' ', '').replace('\r', '').replace('\n', '')

            # Проверяем на отсутствие данных
            if 'NODATA' in clean_response.upper() or '?' in clean_response:
                return PIDValue(
                    pid=pid_upper,
                    name=pid_info['name'],
                    value='Нет данных',
                    unit=pid_info['unit'],
                    icon=pid_info['icon'],
                    status='UNKNOWN',
                    description=pid_info.get('description', ''),
                )

            # Извлекаем данные из ответа 41
            if '41' in clean_response:
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

            # Применяем формулу
            required_bytes = pid_info['bytes']
            if len(bytes_list) >= required_bytes:
                value = pid_info['formula'](*bytes_list[:required_bytes])
            else:
                return None

            # Определяем статус
            status = 'NORMAL'
            if 'warning_range' in pid_info:
                warn_min, warn_max = pid_info['warning_range']
                if isinstance(value, (int, float)):
                    if value < warn_min or value > warn_max:
                        status = 'WARNING'

            if 'range' in pid_info:
                val_min, val_max = pid_info['range']
                if isinstance(value, (int, float)):
                    if value < val_min or value > val_max:
                        status = 'ERROR'

            return PIDValue(
                pid=pid_upper,
                name=pid_info['name'],
                value=value,
                unit=pid_info['unit'],
                icon=pid_info['icon'],
                status=status,
                min=pid_info.get('range', (None, None))[0],
                max=pid_info.get('range', (None, None))[1],
                description=pid_info.get('description', ''),
            )

        except Exception as e:
            logger.error(f"Ошибка парсинга PID {pid}: {e}")
            return PIDValue(
                pid=pid_upper,
                name=pid_info['name'],
                value=f'Ошибка: {str(e)}',
                unit=pid_info['unit'],
                icon=pid_info['icon'],
                status='ERROR',
            )

    @classmethod
    def get_supported_pids(cls) -> List[str]:
        """Возвращает список поддерживаемых PID"""
        return list(cls.PID_DATABASE.keys())

    @classmethod
    def get_pid_info(cls, pid: str) -> Optional[Dict]:
        """Возвращает информацию о PID"""
        return cls.PID_DATABASE.get(pid.upper())

    @classmethod
    def format_pid_list(cls) -> List[Dict]:
        """Возвращает список всех PID с информацией"""
        result = []
        for pid, info in cls.PID_DATABASE.items():
            result.append({
                'pid': pid,
                'name': info['name'],
                'unit': info['unit'],
                'icon': info['icon'],
                'description': info.get('description', ''),
                'range': list(info.get('range', (0, 0))),
            })
        return result


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
        'P0100': 'Неисправность цепи MAF датчика',
        'P0101': 'Диапазон/производительность MAF',
        'P0102': 'Низкий сигнал MAF',
        'P0103': 'Высокий сигнал MAF',
        'P0110': 'Неисправность цепи датчика температуры впуска',
        'P0115': 'Неисправность цепи датчика температуры ОЖ',
        'P0120': 'Неисправность датчика положения дросселя',
        'P0130': 'Неисправность цепи O2 B1S1',
        'P0135': 'Неисправность подогрева O2 B1S1',
        'P0171': 'Слишком бедная смесь (Bank 1)',
        'P0172': 'Слишком богатая смесь (Bank 1)',
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
        'P0700': 'Неисправность системы управления трансмиссией',
    }

    @classmethod
    def format_dtc(cls, raw_hex: str) -> Dict[str, str]:
        """Конвертирует сырой HEX код в DTC формат"""
        try:
            if len(raw_hex) < 4:
                return {'code': raw_hex, 'error': 'Слишком короткий код'}

            first_byte = int(raw_hex[0:2], 16)
            second_byte = int(raw_hex[2:4], 16)

            dtc_prefixes = {
                0x00: 'P0', 0x01: 'P0', 0x02: 'P0', 0x03: 'P0',
                0x04: 'C0', 0x05: 'C0', 0x06: 'C0', 0x07: 'C0',
                0x08: 'B0', 0x09: 'B0', 0x0A: 'B0', 0x0B: 'B0',
                0x0C: 'U0', 0x0D: 'U0', 0x0E: 'U0', 0x0F: 'U0',
            }

            prefix = dtc_prefixes.get(first_byte >> 4, 'P0')
            dtc_code = f"{prefix}{first_byte & 0x0F:01X}{second_byte:02X}"

            description = cls.DTC_DESCRIPTIONS.get(dtc_code, '')
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
        """Парсит ответ с кодами ошибок от ELM327"""
        codes = []

        clean = response.replace(' ', '').replace('\r', '').replace('\n', '')

        if 'NODATA' in clean.upper() or 'OK' in clean.upper() or len(clean) < 4:
            return codes

        mode_prefixes = {'03': '43', '07': '47', '0A': '4A'}
        expected_prefix = mode_prefixes.get(mode, '43')

        if expected_prefix in clean:
            clean = clean.replace(expected_prefix, '')

        for i in range(0, len(clean), 4):
            if i + 4 <= len(clean):
                code_hex = clean[i:i + 4]
                if code_hex != '0000' and len(code_hex) == 4:
                    dtc = cls.format_dtc(code_hex)
                    codes.append(dtc)

        return codes

    @classmethod
    def get_mil_status(cls, response: str) -> Dict[str, Any]:
        """Определяет статус индикатора MIL"""
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
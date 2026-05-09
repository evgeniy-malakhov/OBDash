"""
База данных команд OBD2 и ELM327
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Command:
    """Описывает одну команду"""
    command: str
    description: str
    icon: str = '📡'
    unit: str = ''
    formula: Optional[callable] = None
    priority: int = 10

    def __str__(self):
        return f"{self.icon} {self.description}"


class CommandGroup:
    """Группа команд"""

    def __init__(self, name: str, description: str, icon: str = '📋'):
        self.name = name
        self.description = description
        self.icon = icon
        self.commands: List[Command] = []
        self.subgroups: Dict[str, 'CommandGroup'] = {}

    def add_command(self, command: str, description: str, **kwargs):
        """Добавляет команду в группу"""
        self.commands.append(Command(command, description, **kwargs))

    def add_subgroup(self, key: str, subgroup: 'CommandGroup'):
        """Добавляет подгруппу"""
        self.subgroups[key] = subgroup


class ELM327CommandDatabase:
    """База данных всех команд ELM327"""

    def __init__(self):
        self._build_database()

    def _build_database(self):
        """Строит базу данных команд"""

        # ============================================================
        # 1. ТЕКУЩИЕ ДАННЫЕ (Mode 01)
        # ============================================================
        self.current_data = CommandGroup(
            '📊 Текущие данные',
            'Параметры двигателя в реальном времени',
            '📊'
        )

        # --- Датчики двигателя ---
        engine = CommandGroup('Датчики двигателя', 'Основные параметры работы', '⚙️')
        engine.add_command('01 04', 'Нагрузка двигателя', icon='⏱️', unit='%')
        engine.add_command('01 05', 'Температура ОЖ', icon='🌡️', unit='°C')
        engine.add_command('01 0C', 'Обороты двигателя', icon='⏱️', unit='RPM', priority=1)
        engine.add_command('01 0B', 'Давление впускного коллектора', icon='💨', unit='kPa')
        engine.add_command('01 0F', 'Температура впускного воздуха', icon='🌡️', unit='°C')
        engine.add_command('01 46', 'Температура окружающей среды', icon='🌤️', unit='°C')
        engine.add_command('01 5C', 'Температура масла', icon='🛢️', unit='°C')
        engine.add_command('01 33', 'Барометрическое давление', icon='🌡️', unit='kPa')
        engine.add_command('01 43', 'Абсолютная нагрузка', icon='📊', unit='%')
        self.current_data.add_subgroup('engine', engine)

        # --- Топливная система ---
        fuel = CommandGroup('Топливная система', 'Подача топлива и смесеобразование', '⛽')
        fuel.add_command('01 03', 'Статус топливной системы', icon='⛽')
        fuel.add_command('01 06', 'Краткосрочная коррекция (Bank 1)', icon='📊', unit='%')
        fuel.add_command('01 07', 'Долгосрочная коррекция (Bank 1)', icon='📈', unit='%')
        fuel.add_command('01 08', 'Краткосрочная коррекция (Bank 2)', icon='📊', unit='%')
        fuel.add_command('01 09', 'Долгосрочная коррекция (Bank 2)', icon='📈', unit='%')
        fuel.add_command('01 0A', 'Давление топлива', icon='⛽', unit='kPa')
        fuel.add_command('01 2F', 'Уровень топлива', icon='🛢️', unit='%')
        fuel.add_command('01 51', 'Тип топлива', icon='⛽')
        fuel.add_command('01 52', 'Этанол в топливе', icon='🧪', unit='%')
        fuel.add_command('01 44', 'Лямбда (командная)', icon='🔬', unit='λ')
        fuel.add_command('01 5E', 'Расход топлива', icon='⛽', unit='L/h')
        fuel.add_command('01 23', 'Давление в топливной рампе', icon='⛽', unit='kPa')
        self.current_data.add_subgroup('fuel', fuel)

        # --- Впуск и воздух ---
        air = CommandGroup('Впуск и воздух', 'Параметры воздушного потока', '💨')
        air.add_command('01 10', 'MAF расход воздуха', icon='💨', unit='g/s')
        air.add_command('01 11', 'Положение дросселя', icon='🔧', unit='%')
        air.add_command('01 45', 'Относительное положение дросселя', icon='🔧', unit='%')
        air.add_command('01 5A', 'Положение педали акселератора', icon='🦶', unit='%')
        air.add_command('01 4C', 'Команда EGR', icon='♻️', unit='%')
        air.add_command('01 4D', 'Ошибка EGR', icon='♻️', unit='%')
        air.add_command('01 2C', 'Запрошенный EGR', icon='♻️', unit='%')
        self.current_data.add_subgroup('air', air)

        # --- Скорость и время ---
        speed = CommandGroup('Скорость и время', 'Данные о движении', '🏎️')
        speed.add_command('01 0D', 'Скорость автомобиля', icon='🏎️', unit='km/h')
        speed.add_command('01 0E', 'Угол опережения зажигания', icon='⚡', unit='°')
        speed.add_command('01 1F', 'Время работы с запуска', icon='⏲️', unit='сек')
        speed.add_command('01 21', 'Пробег с MIL', icon='🛣️', unit='km')
        speed.add_command('01 31', 'Пробег после сброса ошибок', icon='🛣️', unit='km')
        speed.add_command('01 30', 'Прогревы после сброса', icon='🔄')
        self.current_data.add_subgroup('speed', speed)

        # --- Кислородные датчики ---
        o2 = CommandGroup('Кислородные датчики', 'Показания O2 сенсоров', '🔬')
        o2.add_command('01 14', 'O2 Bank 1 Sensor 1', icon='🔬', unit='V')
        o2.add_command('01 15', 'O2 Bank 1 Sensor 2', icon='🔬', unit='V')
        o2.add_command('01 18', 'O2 Bank 2 Sensor 1', icon='🔬', unit='V')
        o2.add_command('01 19', 'O2 Bank 2 Sensor 2', icon='🔬', unit='V')
        o2.add_command('01 24', 'Лямбда Bank 1 Sensor 1', icon='🔬', unit='λ')
        o2.add_command('01 25', 'Лямбда Bank 1 Sensor 2', icon='🔬', unit='λ')
        o2.add_command('01 34', 'AFR O2 Bank 1 Sensor 1', icon='🔬')
        o2.add_command('01 35', 'AFR O2 Bank 1 Sensor 2', icon='🔬')
        self.current_data.add_subgroup('o2', o2)

        # --- Электрика ---
        electrical = CommandGroup('Электрика', 'Электрические параметры', '⚡')
        electrical.add_command('01 42', 'Напряжение модуля управления', icon='⚡', unit='V')
        electrical.add_command('01 3E', 'Расход топлива (L/h)', icon='⛽', unit='L/h')
        electrical.add_command('01 1C', 'Стандарт OBD', icon='📋')
        self.current_data.add_subgroup('electrical', electrical)

        # ============================================================
        # 2. КОДЫ ОШИБОК
        # ============================================================
        self.errors = CommandGroup('❌ Коды ошибок', 'Диагностика неисправностей', '❌')

        error_commands = CommandGroup('Чтение ошибок', 'Различные типы DTC', '🔍')
        error_commands.add_command('03', 'Подтверждённые ошибки (Mode 03)', icon='❌')
        error_commands.add_command('07', 'Ожидающие ошибки (Mode 07)', icon='⚠️')
        error_commands.add_command('0A', 'Постоянные ошибки (Mode 0A)', icon='🔒')
        error_commands.add_command('01 01', 'Статус MIL', icon='💡')
        self.errors.add_subgroup('read', error_commands)

        clear_commands = CommandGroup('Управление ошибками', 'Сброс и очистка', '🧹')
        clear_commands.add_command('04', 'Сбросить все ошибки (Mode 04)', icon='🧹')
        self.errors.add_subgroup('clear', clear_commands)

        # --- Специализированные системы ---
        specialized = CommandGroup('Специализированные системы', 'SRS, ABS, трансмиссия', '🔧')

        # Setup and read SRS
        specialized.add_command('AT SH 7B0', 'Установить заголовок SRS', icon='🛡️')
        specialized.add_command('19 02 01', 'Ошибки SRS', icon='🛡️')

        # Setup and read ABS
        specialized.add_command('AT SH 7A0', 'Установить заголовок ABS', icon='🛞')
        specialized.add_command('19 02 01', 'Ошибки ABS', icon='🛞')

        # Setup and read Transmission
        specialized.add_command('AT SH 7E0', 'Установить заголовок трансмиссии', icon='⚙️')
        specialized.add_command('19 02 01', 'Ошибки трансмиссии', icon='⚙️')

        self.errors.add_subgroup('specialized', specialized)

        # ============================================================
        # 3. ИНФОРМАЦИЯ ОБ АВТОМОБИЛЕ (Mode 09)
        # ============================================================
        self.vehicle_info = CommandGroup('ℹ️ Информация об авто', 'Идентификация и параметры', 'ℹ️')

        self.vehicle_info.add_command('09 02', 'VIN номер', icon='🚗')
        self.vehicle_info.add_command('09 0A', 'Имя ECU', icon='💻')
        self.vehicle_info.add_command('09 03', 'Калибровочный ID', icon='🔧')
        self.vehicle_info.add_command('09 04', 'Калибровочные числа (CVN)', icon='✅')
        self.vehicle_info.add_command('09 06', 'Мониторинг производительности', icon='📈')
        self.vehicle_info.add_command('09 09', 'Время работы двигателя', icon='⏱️')
        self.vehicle_info.add_command('09 0B', 'Данные мониторинга', icon='📊')

        # ============================================================
        # 4. AT КОМАНДЫ НАСТРОЙКИ
        # ============================================================
        self.at_commands = CommandGroup('⚙️ Настройки адаптера', 'AT команды ELM327', '⚙️')

        # Общие
        general = CommandGroup('Общие', 'Базовые команды', '🔧')
        general.add_command('ATZ', 'Сброс к заводским настройкам', icon='🔄')
        general.add_command('ATI', 'Информация о версии', icon='ℹ️')
        general.add_command('ATRV', 'Напряжение батареи', icon='🔋', unit='V')
        general.add_command('ATIGN', 'Состояние зажигания', icon='🔑')
        general.add_command('ATDP', 'Текущий протокол', icon='🌐')
        general.add_command('ATDPN', 'Номер протокола', icon='🌐')
        self.at_commands.add_subgroup('general', general)

        # Форматирование
        formatting = CommandGroup('Форматирование', 'Настройка вывода', '📝')
        formatting.add_command('ATE0', 'Выключить эхо', icon='📝')
        formatting.add_command('ATE1', 'Включить эхо', icon='📝')
        formatting.add_command('ATH0', 'Выключить заголовки', icon='📝')
        formatting.add_command('ATH1', 'Включить заголовки', icon='📝')
        formatting.add_command('ATS0', 'Выключить пробелы', icon='📝')
        formatting.add_command('ATS1', 'Включить пробелы', icon='📝')
        formatting.add_command('ATL0', 'Выключить переводы строк', icon='📝')
        formatting.add_command('ATL1', 'Включить переводы строк', icon='📝')
        self.at_commands.add_subgroup('formatting', formatting)

        # Протоколы
        protocols = CommandGroup('Протоколы', 'Выбор протокола OBD2', '🌐')
        protocols.add_command('ATSP 0', 'Автовыбор протокола', icon='🔄')
        protocols.add_command('ATSP 1', 'SAE J1850 PWM (41.6K)', icon='🌐')
        protocols.add_command('ATSP 2', 'SAE J1850 VPW (10.4K)', icon='🌐')
        protocols.add_command('ATSP 3', 'ISO 9141-2', icon='🌐')
        protocols.add_command('ATSP 4', 'ISO 14230-4 KWP (5b)', icon='🌐')
        protocols.add_command('ATSP 5', 'ISO 14230-4 KWP (fast)', icon='🌐')
        protocols.add_command('ATSP 6', 'ISO 15765 CAN (11/500)', icon='🌐')
        protocols.add_command('ATSP 7', 'ISO 15765 CAN (29/500)', icon='🌐')
        protocols.add_command('ATSP 8', 'ISO 15765 CAN (11/250)', icon='🌐')
        protocols.add_command('ATSP 9', 'ISO 15765 CAN (29/250)', icon='🌐')
        protocols.add_command('ATSP A', 'SAE J1939 CAN (29/250)', icon='🚛')
        self.at_commands.add_subgroup('protocols', protocols)

        # CAN настройки
        can = CommandGroup('CAN настройки', 'Параметры CAN шины', '🔧')
        can.add_command('ATCAF0', 'CAN автоформат выкл', icon='🔧')
        can.add_command('ATCAF1', 'CAN автоформат вкл', icon='🔧')
        can.add_command('ATCF', 'Установить CAN фильтр', icon='🔧')
        can.add_command('ATCM', 'Установить CAN маску', icon='🔧')
        can.add_command('ATCRA', 'Установить CAN приёмник', icon='🔧')
        can.add_command('ATSH', 'Установить заголовок', icon='🔧')
        self.at_commands.add_subgroup('can', can)

        # Память и питание
        memory = CommandGroup('Память и питание', 'Сохранение и энергопотребление', '💾')
        memory.add_command('AT&W', 'Сохранить настройки', icon='💾')
        memory.add_command('ATWS', 'Сохранить в EEPROM', icon='💾')
        memory.add_command('ATZ', 'Аппаратный сброс', icon='🔄')
        memory.add_command('ATPC', 'Сохранить протокол', icon='💾')
        memory.add_command('ATLP', 'Режим низкого питания', icon='🔋')
        self.at_commands.add_subgroup('memory', memory)

        # Таймауты
        timing = CommandGroup('Таймауты', 'Временные настройки', '⏱️')
        timing.add_command('ATAT0', 'Адаптивный тайминг выкл', icon='⏱️')
        timing.add_command('ATAT1', 'Адаптивный тайминг вкл', icon='⏱️')
        timing.add_command('ATAT2', 'Адаптивный тайминг (агрес.)', icon='⏱️')
        timing.add_command('ATST', 'Установить таймаут', icon='⏱️')
        self.at_commands.add_subgroup('timing', timing)

        # ============================================================
        # 5. МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ
        # ============================================================
        self.monitoring = CommandGroup('📈 Мониторинг', 'Отслеживание параметров', '📈')

        self.monitoring_presets = {
            'basic': {
                'name': '📊 Базовый мониторинг',
                'description': 'Самые важные параметры',
                'commands': [
                    ('01 0C', 'Обороты (RPM)'),
                    ('01 0D', 'Скорость (km/h)'),
                    ('01 05', 'Температура ОЖ (°C)'),
                ],
                'interval': 0.5
            },
            'detailed': {
                'name': '📈 Расширенный мониторинг',
                'description': 'Для детального анализа',
                'commands': [
                    ('01 0C', 'Обороты (RPM)'),
                    ('01 0D', 'Скорость (km/h)'),
                    ('01 05', 'Температура ОЖ (°C)'),
                    ('01 0B', 'Давление впуска (kPa)'),
                    ('01 11', 'Положение дросселя (%)'),
                    ('01 04', 'Нагрузка (%)'),
                ],
                'interval': 1.0
            },
            'fuel_economy': {
                'name': '⛽ Топливная экономичность',
                'description': 'Расход топлива и коррекции',
                'commands': [
                    ('01 0C', 'Обороты (RPM)'),
                    ('01 0D', 'Скорость (km/h)'),
                    ('01 04', 'Нагрузка (%)'),
                    ('01 06', 'STFT Bank 1 (%)'),
                    ('01 07', 'LTFT Bank 1 (%)'),
                    ('01 2F', 'Уровень топлива (%)'),
                    ('01 5E', 'Расход топлива (L/h)'),
                ],
                'interval': 1.0
            },
            'sensors': {
                'name': '🔬 Датчики O2 и AFR',
                'description': 'Показания кислородных датчиков',
                'commands': [
                    ('01 14', 'O2 B1S1 (V)'),
                    ('01 15', 'O2 B1S2 (V)'),
                    ('01 24', 'Lambda B1S1'),
                    ('01 44', 'Commanded Lambda'),
                ],
                'interval': 0.5
            },
            'temperatures': {
                'name': '🌡️ Температуры',
                'description': 'Все температурные датчики',
                'commands': [
                    ('01 05', 'Охлаждающая жидкость (°C)'),
                    ('01 0F', 'Впускной воздух (°C)'),
                    ('01 46', 'Окружающая среда (°C)'),
                    ('01 5C', 'Масло (°C)'),
                ],
                'interval': 1.0
            }
        }

    def get_group(self, group_name: str) -> CommandGroup:
        """Возвращает группу команд по имени"""
        groups = {
            'current': self.current_data,
            'errors': self.errors,
            'vehicle': self.vehicle_info,
            'at': self.at_commands,
            'monitoring': self.monitoring,
        }
        return groups.get(group_name)

    def get_monitoring_presets(self) -> Dict:
        """Возвращает пресеты для мониторинга"""
        return self.monitoring_presets

    def get_favorite_pids(self) -> List[str]:
        """Возвращает самые популярные PID"""
        return ['0C', '0D', '05', '04', '11', '10', '0F', '2F', '06', '07']
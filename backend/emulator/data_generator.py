"""
Генератор реалистичных OBD2 данных
"""

import random
import math
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .vehicle_profile import VehicleProfile, VEHICLE_PROFILES


class DrivingMode(Enum):
    """Режимы движения"""
    IDLE = "idle"  # Холостой ход
    CRUISE = "cruise"  # Круиз
    ACCELERATION = "accel"  # Ускорение
    DECELERATION = "decel"  # Замедление
    CITY = "city"  # Городской цикл


@dataclass
class EngineState:
    """Состояние двигателя"""
    rpm: float = 0
    speed: float = 0
    load: float = 0
    throttle: float = 0
    coolant_temp: float = 20
    intake_temp: float = 20
    oil_temp: float = 20
    fuel_level: float = 80
    fuel_rate: float = 0
    maf: float = 0
    map: float = 100
    o2_voltage_b1s1: float = 0.45
    o2_voltage_b1s2: float = 0.6
    o2_voltage_b2s1: float = 0.45
    o2_voltage_b2s2: float = 0.6
    stft_b1: float = 0
    ltft_b1: float = 0
    stft_b2: float = 0
    ltft_b2: float = 0
    timing_advance: float = 10
    voltage: float = 14.2
    baro_pressure: float = 101.3
    commanded_lambda: float = 1.0
    o2_lambda_b1s1: float = 1.0
    o2_lambda_b1s2: float = 1.0
    egr_command: float = 0
    throttle_rel: float = 0
    accelerator_pedal: float = 0
    fuel_pressure: float = 350
    runtime: int = 0
    dtc_codes: List[str] = None

    def __post_init__(self):
        self.dtc_codes = self.dtc_codes or []


class OBDDataGenerator:
    """Генератор реалистичных OBD2 данных"""

    def __init__(self, profile: Optional[VehicleProfile] = None, seed: int = 42):
        self.profile = profile or VEHICLE_PROFILES["toyota_camry"]
        self.state = EngineState()
        self.mode = DrivingMode.IDLE
        self.time = 0
        self.dt = 0.1  # Шаг времени в секундах

        # Инициализация случайного генератора
        self.rng = random.Random(seed)

        # Инициализация начального состояния
        self._init_state()

    def _init_state(self):
        """Инициализирует начальное состояние"""
        self.state.rpm = self.profile.idle_rpm
        self.state.speed = 0
        self.state.load = 20
        self.state.throttle = 13
        self.state.coolant_temp = 20  # Холодный двигатель
        self.state.intake_temp = 22
        self.state.oil_temp = 20
        self.state.fuel_level = self.rng.uniform(60, 95)
        self.state.fuel_pressure = self.profile.fuel_pressure
        self.state.baro_pressure = 101.3
        self.state.voltage = 12.4  # До запуска
        self.state.dtc_codes = self.profile.dtc_codes.copy()

    def update(self, dt: Optional[float] = None):
        """Обновляет состояние двигателя"""
        if dt:
            self.dt = dt

        self.time += self.dt

        # Прогрев двигателя
        self._update_temperatures()

        # Обновление в зависимости от режима
        if self.mode == DrivingMode.IDLE:
            self._update_idle()
        elif self.mode == DrivingMode.CRUISE:
            self._update_cruise()
        elif self.mode == DrivingMode.ACCELERATION:
            self._update_acceleration()
        elif self.mode == DrivingMode.DECELERATION:
            self._update_deceleration()
        elif self.mode == DrivingMode.CITY:
            self._update_city()

        # Обновление производных параметров
        self._update_derived_params()

        # Добавление шума
        self._add_noise()

        # Обновление счётчика времени
        self.state.runtime = int(self.time)

    def _update_temperatures(self):
        """Обновляет температуры (прогрев)"""
        # Температура ОЖ растёт до рабочей
        if self.state.rpm > 0:
            target_temp = self.profile.operating_temp
            warmup_rate = 0.1 * (self.state.rpm / self.profile.idle_rpm)
            self.state.coolant_temp += (target_temp - self.state.coolant_temp) * warmup_rate * self.dt

            # Температура масла растёт медленнее
            self.state.oil_temp += (self.state.coolant_temp - self.state.oil_temp) * 0.05 * self.dt

            # Температура впуска зависит от ОЖ и окружающей среды
            ambient = 22 + 5 * math.sin(self.time / 3600)
            self.state.intake_temp = ambient + (self.state.coolant_temp - ambient) * 0.15
        else:
            # Остывание
            self.state.coolant_temp -= (self.state.coolant_temp - 22) * 0.01 * self.dt
            self.state.oil_temp -= (self.state.oil_temp - 22) * 0.005 * self.dt

    def _update_idle(self):
        """Холостой ход"""
        target_rpm = self.profile.idle_rpm

        # Добавляем небольшое изменение при прогреве
        if self.state.coolant_temp < 60:
            target_rpm += 200 * (1 - self.state.coolant_temp / 60)

        # Плавное изменение оборотов
        self.state.rpm += (target_rpm - self.state.rpm) * 0.3
        self.state.rpm += self.rng.gauss(0, 20)  # Небольшая нестабильность

        self.state.speed = 0
        self.state.load = 18 + self.rng.gauss(0, 2)
        self.state.throttle = 13 + self.rng.gauss(0, 1)
        self.state.throttle_rel = self.state.throttle
        self.state.accelerator_pedal = 0

        # Расход топлива на холостом
        self.state.fuel_rate = 0.6 + self.rng.gauss(0, 0.05)

    def _update_cruise(self):
        """Круизный режим"""
        cruise_speed = 90 + self.rng.gauss(0, 5)
        cruise_rpm = 2000 + self.rng.gauss(0, 50)

        self.state.speed += (cruise_speed - self.state.speed) * 0.2
        self.state.rpm += (cruise_rpm - self.state.rpm) * 0.3

        self.state.load = 35 + self.rng.gauss(0, 5)
        self.state.throttle = 25 + self.rng.gauss(0, 3)
        self.state.throttle_rel = self.state.throttle
        self.state.accelerator_pedal = 22 + self.rng.gauss(0, 2)

        # Расход топлива
        self.state.fuel_rate = 5.5 + self.rng.gauss(0, 0.3)

    def _update_acceleration(self):
        """Режим ускорения"""
        target_rpm = 3500 + self.rng.gauss(0, 200)
        target_speed = 60 + self.rng.gauss(0, 10)

        self.state.rpm += (target_rpm - self.state.rpm) * 0.5
        self.state.speed += (target_speed - self.state.speed) * 0.3

        self.state.load = 65 + self.rng.gauss(0, 10)
        self.state.throttle = 55 + self.rng.gauss(0, 5)
        self.state.throttle_rel = self.state.throttle
        self.state.accelerator_pedal = 50 + self.rng.gauss(0, 5)

        # Повышенный расход топлива
        self.state.fuel_rate = 12 + self.rng.gauss(0, 1)

        # Обогащение смеси при ускорении
        self.state.commanded_lambda = 0.95 + self.rng.gauss(0, 0.02)

    def _update_deceleration(self):
        """Режим замедления"""
        self.state.rpm += (self.profile.idle_rpm + 200 - self.state.rpm) * 0.4
        self.state.speed *= 0.95  # Постепенное замедление

        self.state.load = 12 + self.rng.gauss(0, 3)
        self.state.throttle = 10 + self.rng.gauss(0, 2)
        self.state.throttle_rel = self.state.throttle
        self.state.accelerator_pedal = 3 + self.rng.gauss(0, 1)

        # Минимальный расход (торможение двигателем)
        self.state.fuel_rate = 0.3 + self.rng.gauss(0, 0.05)

        # Отсечка топлива
        if self.state.rpm > 1500:
            self.state.fuel_rate = 0
            self.state.commanded_lambda = 1.5  # Бедная смесь

    def _update_city(self):
        """Городской цикл"""
        # Симулируем частые остановки и разгоны
        cycle = self.time % 60  # 60-секундный цикл

        if cycle < 10:
            # Разгон
            self._update_acceleration()
        elif cycle < 20:
            # Крейсерская скорость
            self.state.speed = 50 + self.rng.gauss(0, 5)
            self.state.rpm = 1800 + self.rng.gauss(0, 100)
            self.state.load = 30 + self.rng.gauss(0, 5)
            self.state.throttle = 20 + self.rng.gauss(0, 3)
            self.state.fuel_rate = 4 + self.rng.gauss(0, 0.5)
        elif cycle < 30:
            # Замедление
            self._update_deceleration()
        elif cycle < 40:
            # Остановка
            self._update_idle()
        elif cycle < 50:
            # Разгон
            target_rpm = 2500 + self.rng.gauss(0, 150)
            target_speed = 40 + self.rng.gauss(0, 5)
            self.state.rpm += (target_rpm - self.state.rpm) * 0.4
            self.state.speed += (target_speed - self.state.speed) * 0.3
            self.state.load = 40 + self.rng.gauss(0, 8)
            self.state.throttle = 30 + self.rng.gauss(0, 4)
            self.state.fuel_rate = 7 + self.rng.gauss(0, 0.7)
        else:
            # Замедление до остановки
            self._update_deceleration()

    def _update_derived_params(self):
        """Обновляет производные параметры"""
        # MAF расход воздуха зависит от оборотов и нагрузки
        maf_base = self.profile.maf_idle + (self.state.rpm - self.profile.idle_rpm) / 1000 * 5
        maf_load_factor = self.state.load / 50
        self.state.maf = maf_base * maf_load_factor
        self.state.maf = max(self.profile.maf_idle * 0.8, min(self.profile.maf_max, self.state.maf))

        # MAP давление впуска
        map_base = self.profile.map_idle
        map_load = (self.profile.map_max - self.profile.map_idle) * (self.state.load / 100)
        self.state.map = map_base + map_load

        # Напряжение O2 датчиков
        if self.state.coolant_temp > 60:  # После прогрева
            # Банк 1 Сенсор 1 (до катализатора) - колеблется
            self.state.o2_voltage_b1s1 = 0.45 + self.rng.gauss(0, 0.2)
            self.state.o2_voltage_b1s1 = max(0.05, min(0.95, self.state.o2_voltage_b1s1))

            # Банк 1 Сенсор 2 (после катализатора) - стабильный
            self.state.o2_voltage_b1s2 = 0.65 + self.rng.gauss(0, 0.05)

            # Лямбда значения
            self.state.o2_lambda_b1s1 = 1.0 + self.rng.gauss(0, 0.03)
            self.state.o2_lambda_b1s2 = 1.0 + self.rng.gauss(0, 0.01)
        else:
            # До прогрева - фиксированные значения
            self.state.o2_voltage_b1s1 = 0.45
            self.state.o2_voltage_b1s2 = 0.45

        # Топливные коррекции
        self.state.stft_b1 = self.rng.gauss(0, 3)
        self.state.stft_b2 = self.rng.gauss(0, 3)
        self.state.ltft_b1 = self.rng.gauss(2, 1)
        self.state.ltft_b2 = self.rng.gauss(2, 1)

        # Угол зажигания
        base_timing = 10
        load_correction = -(self.state.load - 20) * 0.3
        rpm_correction = (self.state.rpm - self.profile.idle_rpm) / 1000 * 5
        self.state.timing_advance = base_timing + load_correction + rpm_correction
        self.state.timing_advance = max(-10, min(50, self.state.timing_advance))

        # Напряжение
        if self.state.rpm > 500:
            self.state.voltage = 13.8 + self.rng.gauss(0, 0.1)
        else:
            self.state.voltage = 12.4 + self.rng.gauss(0, 0.05)

        # EGR
        if 1500 < self.state.rpm < 3500 and self.state.load < 60:
            self.state.egr_command = 15 + self.rng.gauss(0, 5)
        else:
            self.state.egr_command = 0

        # Командная лямбда (если не задана режимом)
        if self.mode not in [DrivingMode.ACCELERATION, DrivingMode.DECELERATION]:
            self.state.commanded_lambda = 1.0 + self.rng.gauss(0, 0.01)

        # Уровень топлива (медленно уменьшается)
        fuel_consumption = self.state.fuel_rate / 3600 * self.dt  # Литры за шаг
        self.state.fuel_level -= fuel_consumption / self.profile.fuel_tank_capacity * 100
        self.state.fuel_level = max(5, min(100, self.state.fuel_level))

        # Атмосферное давление (медленно меняется)
        self.state.baro_pressure = 101.3 + self.rng.gauss(0, 0.1)

    def _add_noise(self):
        """Добавляет случайный шум к показаниям"""
        # Небольшой шум ко всем параметрам
        for attr in ['rpm', 'speed', 'load', 'throttle', 'maf', 'map']:
            value = getattr(self.state, attr)
            if isinstance(value, (int, float)):
                noise = self.rng.gauss(0, abs(value) * 0.01)
                setattr(self.state, attr, value + noise)

    def set_mode(self, mode: DrivingMode):
        """Устанавливает режим движения"""
        self.mode = mode

    def get_state_dict(self) -> Dict[str, Any]:
        """Возвращает состояние в виде словаря"""
        return {
            'rpm': round(self.state.rpm),
            'speed': round(self.state.speed, 1),
            'load': round(self.state.load, 1),
            'throttle': round(self.state.throttle, 1),
            'coolant_temp': round(self.state.coolant_temp, 1),
            'intake_temp': round(self.state.intake_temp, 1),
            'oil_temp': round(self.state.oil_temp, 1),
            'fuel_level': round(self.state.fuel_level, 1),
            'fuel_rate': round(self.state.fuel_rate, 2),
            'maf': round(self.state.maf, 2),
            'map': round(self.state.map, 1),
            'o2_b1s1': round(self.state.o2_voltage_b1s1, 3),
            'o2_b1s2': round(self.state.o2_voltage_b1s2, 3),
            'stft_b1': round(self.state.stft_b1, 1),
            'ltft_b1': round(self.state.ltft_b1, 1),
            'timing': round(self.state.timing_advance, 1),
            'voltage': round(self.state.voltage, 2),
            'baro': round(self.state.baro_pressure, 1),
            'lambda_cmd': round(self.state.commanded_lambda, 3),
            'lambda_b1s1': round(self.state.o2_lambda_b1s1, 3),
            'egr': round(self.state.egr_command, 1),
            'runtime': self.state.runtime,
        }

    def get_obd_response(self, pid: str) -> str:
        """
        Генерирует реалистичный OBD2 ответ для PID

        Формат ответа: 41 [PID] [DATA]
        """
        response_prefix = f"41 {pid}"

        pid_upper = pid.upper().replace(' ', '')

        try:
            if pid_upper == '00':
                # Поддерживаемые PID 00-20
                return f"{response_prefix} 98 3A 80 13"

            elif pid_upper == '04':
                # Нагрузка двигателя
                value = int(self.state.load * 255 / 100)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '05':
                # Температура ОЖ
                value = int(self.state.coolant_temp + 40)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '0B':
                # Давление впускного коллектора
                value = int(self.state.map)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '0C':
                # Обороты двигателя
                value = int(self.state.rpm * 4)
                return f"{response_prefix} {value:04X}"

            elif pid_upper == '0D':
                # Скорость
                value = int(self.state.speed)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '0E':
                # Угол зажигания
                value = int((self.state.timing_advance + 64) * 2)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '0F':
                # Температура воздуха на впуске
                value = int(self.state.intake_temp + 40)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '10':
                # MAF расход воздуха
                value = int(self.state.maf * 100)
                return f"{response_prefix} {value:04X}"

            elif pid_upper == '11':
                # Положение дросселя
                value = int(self.state.throttle * 255 / 100)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '14':
                # O2 B1S1 напряжение
                value = int(self.state.o2_voltage_b1s1 * 200)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '15':
                # O2 B1S2 напряжение
                value = int(self.state.o2_voltage_b1s2 * 200)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '1F':
                # Время работы
                value = int(self.state.runtime)
                return f"{response_prefix} {value:04X}"

            elif pid_upper == '2F':
                # Уровень топлива
                value = int(self.state.fuel_level * 255 / 100)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '33':
                # Барометрическое давление
                value = int(self.state.baro_pressure)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '42':
                # Напряжение модуля управления
                value = int(self.state.voltage * 1000)
                return f"{response_prefix} {value:04X}"

            elif pid_upper == '44':
                # Командная лямбда
                value = int(self.state.commanded_lambda * 32768)
                return f"{response_prefix} {value:04X}"

            elif pid_upper == '45':
                # Относительное положение дросселя
                value = int(self.state.throttle_rel * 255 / 100)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '46':
                # Температура окружающей среды
                value = int(self.state.intake_temp + 40)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '5A':
                # Положение педали акселератора
                value = int(self.state.accelerator_pedal * 255 / 100)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '5C':
                # Температура масла
                value = int(self.state.oil_temp + 40)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '5E':
                # Расход топлива
                value = int(self.state.fuel_rate * 20)
                return f"{response_prefix} {value:04X}"

            elif pid_upper == '06':
                # STFT B1
                value = int((self.state.stft_b1 + 100) * 128 / 100)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '07':
                # LTFT B1
                value = int((self.state.ltft_b1 + 100) * 128 / 100)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '0A':
                # Давление топлива
                value = int(self.state.fuel_pressure / 3)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '4C':
                # Команда EGR
                value = int(self.state.egr_command * 255 / 100)
                return f"{response_prefix} {value:02X}"

            elif pid_upper == '01':
                # Статус MIL и количество ошибок
                mil_byte = 0x80 if self.profile.mil_on else 0x00
                dtc_count = len(self.state.dtc_codes)
                return f"{response_prefix} {mil_byte | dtc_count:02X} 00 00 00"

            elif pid_upper == '03':
                # Статус топливной системы
                if self.state.coolant_temp < 60:
                    status = "01"  # Open loop - прогрев
                else:
                    status = "02"  # Closed loop
                return f"{response_prefix} {status} 00"

            elif pid_upper == '1C':
                # Стандарт OBD
                return f"{response_prefix} 01"  # OBD-II

            elif pid_upper == '21':
                # Пробег с MIL
                value = int(self.profile.total_distance)
                return f"{response_prefix} {value:04X}"

            elif pid_upper == '30':
                # Прогревы после сброса
                return f"{response_prefix} {self.profile.warmups_since_dtc_clear:02X}"

            elif pid_upper == '31':
                # Пробег после сброса ошибок
                value = int(self.profile.distance_since_dtc_clear)
                return f"{response_prefix} {value:04X}"

            else:
                # Неизвестный PID
                return "NO DATA"

        except Exception as e:
            return "?"

    def get_dtc_response(self, mode: str = '03') -> str:
        """Генерирует ответ с кодами ошибок"""
        if not self.state.dtc_codes:
            return "NO DATA"

        mode_prefix = {'03': '43', '07': '47', '0A': '4A'}
        prefix = mode_prefix.get(mode, '43')

        # Конвертируем коды в HEX
        dtc_hex_codes = []
        for code in self.state.dtc_codes:
            # Пример: P0420 -> 04 20
            try:
                if len(code) == 5 and code[0] in 'PCBU':
                    num = int(code[1:])
                    byte1 = num >> 8
                    byte2 = num & 0xFF
                    dtc_hex_codes.append(f"{byte1:02X}{byte2:02X}")
            except:
                pass

        if not dtc_hex_codes:
            return "NO DATA"

        response = prefix + " " + " ".join(dtc_hex_codes)
        # Дополняем до стандартной длины
        while len(response.replace(' ', '')) < 12:
            response += " 00"

        return response

    def get_vehicle_info_response(self, info_type: str) -> str:
        """Генерирует ответ с информацией об автомобиле (Mode 09)"""
        prefix = f"49 {info_type}"

        if info_type == '02':
            # VIN номер
            vin_hex = ' '.join(f'{ord(c):02X}' for c in self.profile.vin)
            return f"{prefix} 01 {vin_hex}"

        elif info_type == '0A':
            # Имя ECU
            name_hex = ' '.join(f'{ord(c):02X}' for c in self.profile.ecu_name)
            return f"{prefix} {name_hex}"

        elif info_type == '03':
            # Калибровочный ID
            return f"{prefix} 00 00 00 00"

        else:
            return "NO DATA"
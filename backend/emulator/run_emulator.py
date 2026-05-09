#!/usr/bin/env python3
"""
Скрипт для запуска эмулятора ELM327
"""

import sys
import os
import signal
import asyncio
import logging
import argparse

# Добавляем путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emulator.server import ELM327EmulatorServer
from emulator.vehicle_profile import VEHICLE_PROFILES

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('emulator.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='ELM327 OBD2 Emulator Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python run_emulator.py
  python run_emulator.py --port 35001 --profile bmw_330i
  python run_emulator.py --host 127.0.0.1 --port 35000
  python run_emulator.py --list-profiles
        """
    )

    parser.add_argument(
        '--host', default='0.0.0.0',
        help='Хост (по умолчанию: 0.0.0.0)'
    )
    parser.add_argument(
        '--port', type=int, default=35000,
        help='Порт (по умолчанию: 35000, стандартный порт ELM327 WiFi)'
    )
    parser.add_argument(
        '--profile', default='toyota_camry',
        choices=list(VEHICLE_PROFILES.keys()),
        help='Профиль автомобиля'
    )
    parser.add_argument(
        '--list-profiles', action='store_true',
        help='Показать доступные профили и выйти'
    )

    args = parser.parse_args()

    # Показываем профили
    if args.list_profiles:
        print("\nДоступные профили автомобилей:")
        print("=" * 60)
        for key, profile in VEHICLE_PROFILES.items():
            print(f"\n  [{key}]")
            print(f"    Название: {profile.name}")
            print(f"    VIN: {profile.vin}")
            print(f"    Двигатель: {profile.engine}")
            print(f"    Топливо: {profile.fuel_type}")
            print(f"    Протокол: {profile.obd_protocol}")
            if profile.mil_on:
                print(f"    MIL: ВКЛЮЧЁН (ошибки: {', '.join(profile.dtc_codes)})")
        print()
        return

    # Создаём сервер
    server = ELM327EmulatorServer(
        host=args.host,
        port=args.port,
        profile_name=args.profile,
    )

    profile = VEHICLE_PROFILES[args.profile]

    print("=" * 60)
    print("  ELM327 OBD2 Emulator")
    print("=" * 60)
    print(f"  Хост: {args.host}")
    print(f"  Порт: {args.port}")
    print(f"  Автомобиль: {profile.name}")
    print(f"  Двигатель: {profile.engine}")
    print(f"  VIN: {profile.vin}")
    print(f"  Протокол: {profile.obd_protocol}")
    if profile.mil_on:
        print(f"  Check Engine: ВКЛЮЧЁН")
        print(f"  Коды ошибок: {', '.join(profile.dtc_codes)}")
    print("=" * 60)
    print(f"\n  Для подключения используйте:")
    print(f"  WiFi: telnet {args.host} {args.port}")
    print(f"  Или подключите FastAPI сервер к эмулятору")
    print(f"\n  Нажмите Ctrl+C для остановки")
    print("=" * 60)

    # Обработчик сигналов
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler():
        print("\n\nЗавершение работы эмулятора...")
        server.running = False
        loop.stop()

    try:
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    except NotImplementedError:
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())

    try:
        loop.run_until_complete(server.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(server.stop())
        loop.close()

        print("\nЭмулятор остановлен.")
        print(f"Статистика:")
        print(f"  Подключений: {server.stats['connections']}")
        print(f"  Команд выполнено: {server.stats['commands']}")
        print(f"  Ошибок: {server.stats['errors']}")


if __name__ == '__main__':
    main()
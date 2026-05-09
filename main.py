#!/usr/bin/env python3
"""
ELM327 OBD2 Scanner - Профессиональный сканер диагностики автомобиля

Версия: 1.0.0
Поддержка: ELM327 v1.5
Протоколы: CAN, ISO, J1850, KWP, J1939

Использование:
    python main.py
"""

import sys
import os
import logging
from datetime import datetime

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.menu import InteractiveMenu
from src.ui.display import ConsoleDisplay
from src.utils.helpers import ColorScheme


def setup_logging():
    """Настройка логирования"""
    os.makedirs('logs', exist_ok=True)

    log_filename = f"logs/elm327_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            # logging.StreamHandler()  # Раскомментировать для отладки
        ]
    )

    # Уменьшаем уровень для шумных библиотек
    logging.getLogger('bleak').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


def check_dependencies():
    """Проверяет наличие зависимостей"""
    missing = []

    try:
        import serial
    except ImportError:
        missing.append('pyserial')

    try:
        import bleak
    except ImportError:
        missing.append('bleak (для Bluetooth)')

    if missing:
        print(f"{ColorScheme.warning('⚠️  Отсутствуют зависимости:')}")
        for dep in missing:
            print(f"   - {dep}")
        print(f"\n   Установите командой: pip install {' '.join(missing)}")
        print()

        response = input("   Продолжить без недостающих модулей? (y/n): ")
        if response.lower() not in ['y', 'yes', 'да']:
            sys.exit(1)


def main():
    """Точка входа"""
    try:
        # Настройка логирования
        setup_logging()

        # Проверка зависимостей
        check_dependencies()

        # Запуск приложения
        app = InteractiveMenu()
        app.run()

    except KeyboardInterrupt:
        print(f"\n\n{ColorScheme.info('Программа прервана пользователем')}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{ColorScheme.error(f'Критическая ошибка: {str(e)}')}")
        logging.critical(f"Необработанное исключение: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
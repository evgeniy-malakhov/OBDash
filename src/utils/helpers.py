"""
Вспомогательные утилиты
"""

import os
import time
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ColorScheme:
    """Цветовая схема для консоли"""

    # Базовые цвета
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

    # Стандартные цвета
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Яркие цвета
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'

    @classmethod
    def colorize(cls, text: str, color: str, bold: bool = False) -> str:
        """Окрашивает текст"""
        prefix = cls.BOLD if bold else ''
        return f"{prefix}{color}{text}{cls.RESET}"

    @classmethod
    def success(cls, text: str) -> str:
        return cls.colorize(text, cls.GREEN)

    @classmethod
    def error(cls, text: str) -> str:
        return cls.colorize(text, cls.RED)

    @classmethod
    def warning(cls, text: str) -> str:
        return cls.colorize(text, cls.YELLOW)

    @classmethod
    def info(cls, text: str) -> str:
        return cls.colorize(text, cls.CYAN)

    @classmethod
    def highlight(cls, text: str) -> str:
        return cls.colorize(text, cls.MAGENTA, bold=True)


class Spinner:
    """Анимированный спиннер для консоли"""

    SPINNERS = {
        'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        'line': ['|', '/', '-', '\\'],
        'arrow': ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'],
        'bounce': ['⠁', '⠂', '⠄', '⡀', '⢀', '⠠', '⠐', '⠈'],
    }

    def __init__(self, message: str = "Загрузка", style: str = 'dots'):
        self.message = message
        self.frames = self.SPINNERS.get(style, self.SPINNERS['dots'])
        self.running = False

    def spin(self):
        """Генератор для спиннера"""
        import itertools
        for frame in itertools.cycle(self.frames):
            if not self.running:
                break
            yield f"\r{frame} {self.message}..."

    def __enter__(self):
        self.running = True
        return self

    def __exit__(self, *args):
        self.running = False
        print('\r' + ' ' * (len(self.message) + 10) + '\r', end='')


class DataSaver:
    """Сохранение данных в файлы"""

    @staticmethod
    def save_to_json(data: Any, filename: str = None, subfolder: str = 'data') -> str:
        """Сохраняет данные в JSON файл"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"obd_data_{timestamp}.json"

        os.makedirs(subfolder, exist_ok=True)
        filepath = os.path.join(subfolder, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Данные сохранены в {filepath}")
        return filepath

    @staticmethod
    def save_to_csv(data: List[Dict], filename: str = None, subfolder: str = 'data') -> str:
        """Сохраняет данные в CSV файл"""
        import csv

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"obd_data_{timestamp}.csv"

        os.makedirs(subfolder, exist_ok=True)
        filepath = os.path.join(subfolder, filename)

        if not data:
            logger.warning("Нет данных для сохранения")
            return filepath

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Данные сохранены в {filepath}")
        return filepath


def clear_screen():
    """Очищает экран консоли"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str, width: int = 60):
    """Выводит заголовок"""
    print()
    print("╔" + "═" * (width - 2) + "╗")
    print("║" + f"  {title}".center(width - 2) + "║")
    print("╚" + "═" * (width - 2) + "╝")


def print_divider(width: int = 60, char: str = "─"):
    """Выводит разделитель"""
    print(char * width)


def confirm_action(message: str) -> bool:
    """Запрашивает подтверждение действия"""
    response = input(f"{ColorScheme.warning(message)} (y/n): ").lower().strip()
    return response in ['y', 'yes', 'да', 'д']


def format_bytes(bytes_data: List[int]) -> str:
    """Форматирует байты в HEX строку"""
    return ' '.join(f'{b:02X}' for b in bytes_data)


def get_timestamp() -> str:
    """Возвращает текущую временную метку"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
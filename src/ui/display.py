"""
Отображение данных в консоли
"""

import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import textwrap

from ..utils.helpers import ColorScheme, print_header, print_divider, get_timestamp
from ..obd.parser import ParsedValue, ValueStatus


class ConsoleDisplay:
    """Класс для красивого отображения данных в консоли"""

    # Ширина консоли по умолчанию
    DEFAULT_WIDTH = 80

    @staticmethod
    def clear_screen():
        """Очищает экран"""
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def print_banner():
        """Выводит баннер приложения"""
        ConsoleDisplay.clear_screen()

        banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███████╗██╗     ███╗   ███╗██████╗ ██████╗ ██████╗  ██╗   ║
║   ██╔════╝██║     ████╗ ████║╚════██╗╚════██╗╚════██╗███║   ║
║   █████╗  ██║     ██╔████╔██║ █████╔╝ █████╔╝ █████╔╝╚██║   ║
║   ██╔══╝  ██║     ██║╚██╔╝██║██╔═══╝ ██╔═══╝ ██╔═══╝  ██║   ║
║   ███████╗███████╗██║ ╚═╝ ██║███████╗███████╗███████╗ ██║   ║
║   ╚══════╝╚══════╝╚═╝     ╚═╝╚══════╝╚══════╝╚══════╝ ╚═╝   ║
║                                                              ║
║              OBD2 Сканер на базе ELM327 v1.5                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(ColorScheme.colorize(banner, ColorScheme.CYAN))
        print()

    @staticmethod
    def print_value_card(value: ParsedValue):
        """Выводит карточку с одним значением"""
        # Определяем цвет в зависимости от статуса
        if value.status == ValueStatus.NORMAL:
            status_color = ColorScheme.GREEN
            value_color = ColorScheme.BRIGHT_GREEN
        elif value.status == ValueStatus.WARNING:
            status_color = ColorScheme.YELLOW
            value_color = ColorScheme.BRIGHT_YELLOW
        elif value.status == ValueStatus.ERROR:
            status_color = ColorScheme.RED
            value_color = ColorScheme.BRIGHT_RED
        else:
            status_color = ColorScheme.DIM
            value_color = ColorScheme.WHITE

        # Форматируем значение
        if isinstance(value.value, float):
            if abs(value.value) < 10:
                value_str = f"{value.value:.2f}"
            elif abs(value.value) < 100:
                value_str = f"{value.value:.1f}"
            else:
                value_str = f"{value.value:.0f}"
        else:
            value_str = str(value.value)

        width = 36

        print("  ╔" + "═" * (width - 2) + "╗")
        print(f"  ║ {value.icon} {value.name:<{width - 6}} ║")
        print("  ╠" + "─" * (width - 2) + "╣")
        print(
            f"  ║   {ColorScheme.BOLD}{value_color}{value_str:>{width - 10}}{value.unit if value.unit else '':<4}{ColorScheme.RESET} ║")
        print("  ╠" + "─" * (width - 2) + "╣")
        print(
            f"  ║   Статус: {status_color}{value.status.value} {'НОРМА' if value.status == ValueStatus.NORMAL else 'ВНИМАНИЕ' if value.status == ValueStatus.WARNING else 'ОШИБКА'}{ColorScheme.RESET}{' ' * (width - 31)} ║")
        if value.description:
            desc_wrapped = textwrap.wrap(value.description, width=width - 6)
            for line in desc_wrapped[:2]:  # Максимум 2 строки описания
                print(f"  ║   {ColorScheme.DIM}{line:<{width - 6}}{ColorScheme.RESET} ║")
        print("  ╚" + "═" * (width - 2) + "╝")

    @staticmethod
    def print_values_table(values: List[ParsedValue], title: str = "📊 Текущие параметры"):
        """Выводит таблицу значений"""
        if not values:
            print(f"\n  {ColorScheme.warning('Нет данных для отображения')}")
            return

        width = 78
        print(f"\n  ╔{'═' * (width - 2)}╗")
        print(f"  ║  {title.center(width - 4)}  ║")
        print(f"  ╠{'═' * (width - 2)}╣")
        print(f"  ║ {'Параметр':<32} {'Значение':<15} {'Ед.изм':<8} {'Статус':<12} ║")
        print(f"  ╠{'─' * (width - 2)}╣")

        for v in values:
            if isinstance(v.value, float):
                if abs(v.value) < 10:
                    val_str = f"{v.value:.2f}"
                elif abs(v.value) < 100:
                    val_str = f"{v.value:.1f}"
                else:
                    val_str = f"{v.value:.0f}"
            else:
                val_str = str(v.value)[:14]

            # Цвет статуса
            if v.status == ValueStatus.NORMAL:
                status_str = f"{ColorScheme.GREEN}✓ НОРМА{ColorScheme.RESET}"
            elif v.status == ValueStatus.WARNING:
                status_str = f"{ColorScheme.YELLOW}⚠ ВНИМ.{ColorScheme.RESET}"
            elif v.status == ValueStatus.ERROR:
                status_str = f"{ColorScheme.RED}✗ ОШИБ.{ColorScheme.RESET}"
            else:
                status_str = f"{ColorScheme.DIM}? Н/Д{ColorScheme.RESET}"

            # Обрезаем название с иконкой
            name_with_icon = f"{v.icon} {v.name}"
            if len(name_with_icon) > 31:
                name_with_icon = name_with_icon[:28] + '...'

            print(f"  ║ {name_with_icon:<32} {val_str:<15} {v.unit:<8} {status_str:<22} ║")

        print(f"  ╚{'═' * (width - 2)}╝")

    @staticmethod
    def print_errors_table(errors: List[Dict], title: str = "❌ Коды ошибок (DTC)"):
        """Выводит таблицу ошибок"""
        width = 78

        print(f"\n  ╔{'═' * (width - 2)}╗")
        print(f"  ║  {title.center(width - 4)}  ║")
        print(f"  ╠{'═' * (width - 2)}╣")

        if not errors:
            print(f"  ║  {ColorScheme.success('✅ Ошибок не обнаружено').center(width - 4)}  ║")
        else:
            print(f"  ║ {'Код':<8} {'Категория':<25} {'Описание':<37} ║")
            print(f"  ╠{'─' * (width - 2)}╣")

            for err in errors:
                code = err.get('code', 'N/A')
                category = err.get('category', 'Неизвестно')[:24]
                description = err.get('description', '')[:36]

                code_color = ColorScheme.BRIGHT_RED if 'P' in str(code) else ColorScheme.YELLOW
                print(f"  ║ {code_color}{code:<8}{ColorScheme.RESET} {category:<25} {description:<37} ║")

        print(f"  ╚{'═' * (width - 2)}╝")

    @staticmethod
    def print_vehicle_info(info: Dict[str, str]):
        """Выводит информацию об автомобиле"""
        width = 50

        print(f"\n  ╔{'═' * (width - 2)}╗")
        print(f"  ║  {'🚗 ИНФОРМАЦИЯ ОБ АВТОМОБИЛЕ'.center(width - 4)}  ║")
        print(f"  ╠{'═' * (width - 2)}╣")

        for key, value in info.items():
            if value and value != 'N/A' and 'NODATA' not in str(value).upper():
                print(f"  ║  {ColorScheme.BOLD}{key}:{ColorScheme.RESET} {ColorScheme.info(str(value))}")

        print(f"  ╚{'═' * (width - 2)}╝")

    @staticmethod
    def print_realtime_header(pids: List[str], descriptions: List[str]):
        """Выводит заголовок для real-time мониторинга"""
        width = 78

        print(f"\r  ╔{'═' * (width - 2)}╗")
        print(f"\r  ║  {'📈 МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ'.center(width - 4)}  ║")
        print(f"\r  ╠{'═' * (width - 2)}╣")

        # Формируем заголовок колонок
        header = "  ║ "
        for desc in descriptions:
            header += f"{desc[:15]:^16}"
        header += " " * (width - len(header) - 2) + "║"
        print(f"\r{header}")
        print(f"\r  ╠{'─' * (width - 2)}╣")

    @staticmethod
    def print_realtime_values(values: List[ParsedValue], pids: List[str]):
        """Выводит одну строку real-time данных"""
        width = 78
        timestamp = datetime.now().strftime('%H:%M:%S')

        line = f"\r  ║ {ColorScheme.DIM}{timestamp}{ColorScheme.RESET} "

        for pid in pids:
            matching = [v for v in values if v.pid == pid.replace('01 ', '')]
            if matching:
                v = matching[0]
                if isinstance(v.value, float):
                    val_str = f"{v.value:.1f}"
                else:
                    val_str = str(v.value)[:12]

                # Цвет в зависимости от статуса
                if v.status == ValueStatus.NORMAL:
                    line += f"{ColorScheme.GREEN}{val_str:>8}{v.unit:<4}{ColorScheme.RESET} "
                elif v.status == ValueStatus.WARNING:
                    line += f"{ColorScheme.YELLOW}{val_str:>8}{v.unit:<4}{ColorScheme.RESET} "
                else:
                    line += f"{ColorScheme.RED}{val_str:>8}{v.unit:<4}{ColorScheme.RESET} "
            else:
                line += f"{ColorScheme.DIM}{'N/A':>8}{ColorScheme.RESET}    "

        line += " " * (width - len(line.replace('\033[91m', '').replace('\033[92m', '')
                                   .replace('\033[93m', '').replace('\033[94m', '')
                                   .replace('\033[95m', '').replace('\033[96m', '')
                                   .replace('\033[2m', '').replace('\033[0m', '')) - 2) + "║"
        print(line, end='')

    @staticmethod
    def print_progress_bar(iteration: int, total: int, prefix: str = '', suffix: str = '', length: int = 50):
        """Выводит прогресс-бар"""
        percent = f"{100 * (iteration / float(total)):.0f}"
        filled_length = int(length * iteration // total)
        bar = '█' * filled_length + '░' * (length - filled_length)

        print(f'\r  {prefix} |{ColorScheme.CYAN}{bar}{ColorScheme.RESET}| {percent}% {suffix}', end='')

        if iteration == total:
            print()

    @staticmethod
    def print_menu_item(number: int, title: str, description: str = '', indent: int = 2):
        """Выводит пункт меню"""
        spaces = ' ' * indent
        if description:
            print(f"{spaces}{ColorScheme.highlight(f'[{number}]')} {ColorScheme.BOLD}{title}{ColorScheme.RESET}")
            print(f"{spaces}    {ColorScheme.DIM}{description}{ColorScheme.RESET}")
        else:
            print(f"{spaces}{ColorScheme.highlight(f'[{number}]')} {title}")

    @staticmethod
    def print_success(message: str):
        """Выводит сообщение об успехе"""
        print(f"  {ColorScheme.success('✓')} {message}")

    @staticmethod
    def print_error(message: str):
        """Выводит сообщение об ошибке"""
        print(f"  {ColorScheme.error('✗')} {message}")

    @staticmethod
    def print_warning(message: str):
        """Выводит предупреждение"""
        print(f"  {ColorScheme.warning('⚠')} {message}")

    @staticmethod
    def print_info(message: str):
        """Выводит информационное сообщение"""
        print(f"  {ColorScheme.info('ℹ')} {message}")

    @staticmethod
    def print_divider(title: str = '', width: int = 78):
        """Выводит разделитель с заголовком"""
        if title:
            line = '─' * ((width - len(title) - 4) // 2)
            print(f"\n  {line} {ColorScheme.BOLD}{title}{ColorScheme.RESET} {line}")
        else:
            print(f"\n  {'─' * width}")
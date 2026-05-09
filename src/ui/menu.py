"""
Интерактивное меню приложения
"""

import time
import sys
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime

from ..core.connection import ELM327Connection
from ..core.scanner import DeviceScanner, DeviceInfo, DeviceNotFoundError
from ..core.exceptions import ELM327Error, ConnectionError, CommandError
from ..obd.commands import ELM327CommandDatabase, Command, CommandGroup
from ..obd.parser import OBDParser, DTCFormatter, ParsedValue
from .display import ConsoleDisplay
from ..utils.helpers import (ColorScheme, Spinner, DataSaver,
                             clear_screen, confirm_action, get_timestamp)


class InteractiveMenu:
    """Интерактивное меню ELM327 сканера"""

    def __init__(self):
        self.connection: Optional[ELM327Connection] = None
        self.device: Optional[DeviceInfo] = None
        self.db = ELM327CommandDatabase()
        self.parser = OBDParser()
        self.display = ConsoleDisplay()
        self.data_log: List[Dict] = []
        self.running = True

    def run(self):
        """Запускает приложение"""
        try:
            self._show_banner()
            self._connect_device()
            self._initialize_device()
            self._main_loop()
        except KeyboardInterrupt:
            self._exit_gracefully()
        except ELM327Error as e:
            self.display.print_error(str(e))
            sys.exit(1)
        except Exception as e:
            self.display.print_error(f"Неожиданная ошибка: {str(e)}")
            sys.exit(1)

    def _show_banner(self):
        """Показывает баннер"""
        ConsoleDisplay.print_banner()

    def _connect_device(self):
        """Процесс подключения к устройству"""
        from ..core.connection import create_connection

        print(f"\n  {ColorScheme.info('ШАГ 1: Поиск устройства ELM327')}")
        print(f"  {'─' * 50}")

        scanner = DeviceScanner()

        try:
            devices = scanner.scan_all()
            scanner.display_devices()

            if len(devices) == 1:
                self.device = devices[0]
                print(f"\n  Автоматически выбрано: {ColorScheme.highlight(str(self.device))}")
            else:
                self.device = scanner.select_device()

            # Создаём соединение
            print(f"\n  {ColorScheme.info('ШАГ 2: Подключение к устройству')}")
            print(f"  {'─' * 50}")

            self.connection = create_connection(self.device)
            self.connection.connect()

        except DeviceNotFoundError as e:
            raise ConnectionError(str(e))

    def _initialize_device(self):
        """Инициализирует устройство"""
        print(f"\n  {ColorScheme.info('ШАГ 3: Инициализация ELM327')}")
        print(f"  {'─' * 50}")

        self.connection.initialize()

        # Проверяем связь
        if not self.connection.test_connection():
            raise ConnectionError("Устройство не отвечает на тестовые команды")

        print(f"\n  {ColorScheme.success('✓ Устройство готово к работе!')}")

        # Небольшая пауза перед меню
        time.sleep(1)

    def _main_loop(self):
        """Главный цикл меню"""
        while self.running:
            try:
                self._show_main_menu()
            except CommandError as e:
                self.display.print_warning(f"Ошибка команды: {str(e)}")
                time.sleep(1)
            except ConnectionError as e:
                self.display.print_error(f"Соединение потеряно: {str(e)}")
                if confirm_action("Попробовать переподключиться?"):
                    self._connect_device()
                    self._initialize_device()
                else:
                    self.running = False
            except Exception as e:
                self.display.print_error(f"Ошибка: {str(e)}")
                time.sleep(1)

    def _show_main_menu(self):
        """Главное меню"""
        clear_screen()
        ConsoleDisplay.print_banner()

        # Статус подключения
        status_color = ColorScheme.GREEN if self.connection and self.connection.connected else ColorScheme.RED
        print(f"  Статус: {status_color}● Подключено{ColorScheme.RESET}")
        if self.connection and hasattr(self.connection, 'protocol'):
            print(f"  Протокол: {ColorScheme.info(self.connection.protocol or 'N/A')}")
            print(f"  Напряжение: {ColorScheme.info((self.connection.voltage or 'N/A') + 'V')}")
        print(f"  {'═' * 60}")

        # Пункты меню
        menu_items = [
            ('📊', 'Датчики и параметры', 'Чтение текущих данных двигателя', self._menu_sensors),
            ('❌', 'Диагностика ошибок', 'Чтение и сброс кодов DTC', self._menu_errors),
            ('ℹ️', 'Информация об авто', 'VIN, ECU, версии', self._menu_vehicle_info),
            ('📈', 'Мониторинг', 'Отслеживание параметров в реальном времени', self._menu_monitoring),
            ('⚙️', 'Настройки адаптера', 'AT команды для ELM327', self._menu_at_commands),
            ('💾', 'Сохранить данные', 'Экспорт в JSON/CSV', self._menu_save_data),
            ('🔌', 'Переподключиться', 'Сменить устройство', self._menu_reconnect),
            ('🚪', 'Выход', 'Завершить работу', self._menu_exit),
        ]

        for i, (icon, name, desc, _) in enumerate(menu_items, 1):
            self.display.print_menu_item(i, f"{icon} {name}", desc)

        print()

        try:
            choice = input(f"  {ColorScheme.BOLD}Выберите действие [1-{len(menu_items)}]:{ColorScheme.RESET} ").strip()
            if choice == 'q':
                self._menu_exit()
                return

            idx = int(choice)
            if 1 <= idx <= len(menu_items):
                menu_items[idx - 1][3]()
            else:
                self.display.print_warning(f"Введите число от 1 до {len(menu_items)}")
                time.sleep(1)
        except ValueError:
            self.display.print_warning("Неверный ввод. Введите число.")
            time.sleep(1)

    # ============================================================
    # МЕНЮ ДАТЧИКОВ
    # ============================================================
    def _menu_sensors(self):
        """Меню датчиков и параметров"""
        while True:
            clear_screen()
            print_header("📊 ДАТЧИКИ И ПАРАМЕТРЫ")

            groups = self.db.current_data.subgroups

            group_list = list(groups.items())
            for i, (key, group) in enumerate(group_list, 1):
                self.display.print_menu_item(i, group.name, group.description)

            self.display.print_menu_item(len(group_list) + 1, "🔙 Назад в главное меню")

            try:
                choice = input(f"\n  {ColorScheme.BOLD}Выберите группу:{ColorScheme.RESET} ").strip()
                if choice.lower() == 'q':
                    return

                idx = int(choice)
                if 1 <= idx <= len(group_list):
                    self._show_sensor_group(group_list[idx - 1][1])
                elif idx == len(group_list) + 1:
                    break
            except ValueError:
                self.display.print_warning("Неверный ввод")
                time.sleep(1)

    def _show_sensor_group(self, group: CommandGroup):
        """Показывает группу датчиков"""
        while True:
            clear_screen()
            print_header(group.name)
            print(f"  {ColorScheme.DIM}{group.description}{ColorScheme.RESET}\n")

            commands = group.commands

            for i, cmd in enumerate(commands, 1):
                self.display.print_menu_item(i, str(cmd))

            bottom_options = [
                ('📊 Прочитать всю группу', self._read_all_group),
                ('🔙 Назад', None),
            ]

            for i, (desc, _) in enumerate(bottom_options, len(commands) + 1):
                self.display.print_menu_item(i, desc)

            try:
                choice = input(f"\n  {ColorScheme.BOLD}Выберите PID:{ColorScheme.RESET} ").strip()
                if choice.lower() == 'q':
                    return

                idx = int(choice)
                if 1 <= idx <= len(commands):
                    self._read_single_pid(commands[idx - 1])
                elif idx == len(commands) + 1:
                    self._read_all_group(group)
                elif idx == len(commands) + 2:
                    break
            except ValueError:
                self.display.print_warning("Неверный ввод")
                time.sleep(1)

    def _read_single_pid(self, cmd: Command):
        """Читает один PID"""
        print(f"\n  🔍 {cmd.description}")

        try:
            response = self.connection.send_command(cmd.command)
            pid = cmd.command.replace('01 ', '')
            result = self.parser.parse_response(pid, response)

            if result:
                self.display.print_value_card(result)
                self._log_data(result)
            else:
                self.display.print_warning(f"Не удалось распарсить ответ: {response}")
        except Exception as e:
            self.display.print_error(f"Ошибка: {str(e)}")

        input(f"\n  {ColorScheme.DIM}Нажмите Enter для продолжения...{ColorScheme.RESET}")

    def _read_all_group(self, group: CommandGroup):
        """Читает все PID в группе"""
        print(f"\n  📊 Чтение группы: {ColorScheme.BOLD}{group.name}{ColorScheme.RESET}")
        print(f"  {'─' * 50}\n")

        results = []
        commands = group.commands

        for i, cmd in enumerate(commands):
            try:
                print(f"  [{i + 1}/{len(commands)}] {cmd.description}...", end=' ')
                response = self.connection.send_command(cmd.command)
                pid = cmd.command.replace('01 ', '')
                result = self.parser.parse_response(pid, response)

                if result:
                    results.append(result)
                    print(f"{ColorScheme.success(result.value)} {result.unit}")
                    self._log_data(result)
                else:
                    print(ColorScheme.warning('Нет данных'))

                time.sleep(0.05)
            except Exception as e:
                print(ColorScheme.error(f'Ошибка: {str(e)}'))

        # Показываем сводную таблицу
        if results:
            self.display.print_values_table(results, f"📊 {group.name}")

        input(f"\n  {ColorScheme.DIM}Нажмите Enter для продолжения...{ColorScheme.RESET}")

    # ============================================================
    # МЕНЮ ОШИБОК
    # ============================================================
    def _menu_errors(self):
        """Меню диагностики ошибок"""
        while True:
            clear_screen()
            print_header("❌ ДИАГНОСТИКА ОШИБОК")

            # Проверяем MIL
            try:
                mil_response = self.connection.send_command('01 01')
                mil_status = DTCFormatter.get_mil_status(mil_response)
                if mil_status.get('mil_on'):
                    print(
                        f"  {ColorScheme.error('⚠ CHECK ENGINE ВКЛЮЧЕН! Обнаружено ошибок: ' + str(mil_status.get('dtc_count', '?')))}\n")
                else:
                    print(f"  {ColorScheme.success('✅ Check Engine выключен')}\n")
            except:
                pass

            self.display.print_menu_item(1, '📋 Подтверждённые ошибки (Mode 03)', 'Сохранённые коды неисправностей')
            self.display.print_menu_item(2, '⚠️ Ожидающие ошибки (Mode 07)', 'Обнаруженные, но не подтверждённые')
            self.display.print_menu_item(3, '🔒 Постоянные ошибки (Mode 0A)', 'Подтверждённые и сохранённые')
            self.display.print_menu_item(4, '🧹 Сбросить ошибки (Mode 04)', 'Очистка кодов и выключение MIL')
            self.display.print_menu_item(5, '🔧 Специализированные системы', 'SRS, ABS, Трансмиссия')
            self.display.print_menu_item(6, '🔙 Назад')

            try:
                choice = input(f"\n  {ColorScheme.BOLD}Выберите действие:{ColorScheme.RESET} ").strip()

                if choice == '1':
                    self._read_errors('03', 'Подтверждённые ошибки')
                elif choice == '2':
                    self._read_errors('07', 'Ожидающие ошибки')
                elif choice == '3':
                    self._read_errors('0A', 'Постоянные ошибки')
                elif choice == '4':
                    self._clear_errors()
                elif choice == '5':
                    self._menu_specialized()
                elif choice == '6':
                    break
            except ValueError:
                pass

    def _read_errors(self, mode: str, title: str):
        """Читает ошибки в указанном режиме"""
        print(f"\n  🔍 Чтение: {ColorScheme.BOLD}{title}{ColorScheme.RESET}")

        try:
            response = self.connection.send_command(mode)
            errors = DTCFormatter.parse_dtc_response(response, mode)
            self.display.print_errors_table(errors, title)
        except Exception as e:
            self.display.print_error(f"Ошибка чтения: {str(e)}")

        input(f"\n  {ColorScheme.DIM}Нажмите Enter для продолжения...{ColorScheme.RESET}")

    def _clear_errors(self):
        """Сбрасывает ошибки"""
        if not confirm_action("⚠️ Вы уверены? Это сбросит все коды ошибок и выключит Check Engine!"):
            return

        print(f"\n  🧹 Сброс ошибок...")

        try:
            response = self.connection.send_command('04')
            if '44' in response:
                self.display.print_success("Ошибки успешно сброшены!")
            else:
                self.display.print_warning(f"Ответ: {response}")
        except Exception as e:
            self.display.print_error(f"Ошибка сброса: {str(e)}")

        input(f"\n  {ColorScheme.DIM}Нажмите Enter для продолжения...{ColorScheme.RESET}")

    def _menu_specialized(self):
        """Меню специализированных систем"""
        while True:
            clear_screen()
            print_header("🔧 СПЕЦИАЛИЗИРОВАННЫЕ СИСТЕМЫ")

            self.display.print_menu_item(1, '🛡️ SRS (Подушки безопасности)', 'Запрос ошибок подушек')
            self.display.print_menu_item(2, '🛞 ABS (Антиблокировочная система)', 'Запрос ошибок ABS')
            self.display.print_menu_item(3, '⚙️ Трансмиссия', 'Запрос ошибок КПП')
            self.display.print_menu_item(4, '🔙 Назад')

            try:
                choice = input(f"\n  {ColorScheme.BOLD}Выберите систему:{ColorScheme.RESET} ").strip()

                systems = {
                    '1': ('7B0', 'SRS (Подушки безопасности)'),
                    '2': ('7A0', 'ABS'),
                    '3': ('7E0', 'Трансмиссия'),
                }

                if choice in systems:
                    header, name = systems[choice]
                    self._read_specialized_errors(header, name)
                elif choice == '4':
                    break
            except ValueError:
                pass

    def _read_specialized_errors(self, header: str, system_name: str):
        """Читает ошибки специализированной системы"""
        print(f"\n  🔍 Система: {ColorScheme.BOLD}{system_name}{ColorScheme.RESET}")

        try:
            # Устанавливаем заголовок
            self.connection.send_command(f'AT SH {header}')
            time.sleep(0.1)

            # Запрашиваем ошибки
            response = self.connection.send_command('19 02 01')

            # Возвращаем стандартный заголовок
            self.connection.send_command('AT SH 7DF')

            self.display.print_info(f"Ответ системы: {response}")
        except Exception as e:
            self.display.print_error(f"Ошибка: {str(e)}")

        input(f"\n  {ColorScheme.DIM}Нажмите Enter для продолжения...{ColorScheme.RESET}")

    # ============================================================
    # МЕНЮ ИНФОРМАЦИИ
    # ============================================================
    def _menu_vehicle_info(self):
        """Информация об автомобиле"""
        clear_screen()
        print_header("ℹ️ ИНФОРМАЦИЯ ОБ АВТОМОБИЛЕ")

        info_queries = [
            ('09 02', 'VIN номер'),
            ('09 0A', 'Имя ECU'),
            ('09 03', 'Калибровочный ID'),
            ('09 04', 'Калибровочные числа (CVN)'),
        ]

        results = {}

        for cmd, name in info_queries:
            try:
                print(f"  🔍 {name}...", end=' ')
                response = self.connection.send_command(cmd)
                print(f"{ColorScheme.info(response[:50])}")
                results[name] = response
                time.sleep(0.1)
            except Exception as e:
                print(ColorScheme.error(f'Ошибка'))
                results[name] = f'Ошибка: {str(e)}'

        # Дополнительная информация
        try:
            response = self.connection.send_command('01 1C')
            results['Стандарт OBD'] = response
        except:
            pass

        self.display.print_vehicle_info(results)

        input(f"\n  {ColorScheme.DIM}Нажмите Enter для продолжения...{ColorScheme.RESET}")

    # ============================================================
    # МЕНЮ МОНИТОРИНГА
    # ============================================================
    def _menu_monitoring(self):
        """Меню мониторинга в реальном времени"""
        while True:
            clear_screen()
            print_header("📈 МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ")

            presets = self.db.get_monitoring_presets()

            preset_items = list(presets.items())
            for i, (key, preset) in enumerate(preset_items, 1):
                self.display.print_menu_item(
                    i,
                    preset['name'],
                    f"{preset['description']} (интервал: {preset['interval']}с)"
                )

            self.display.print_menu_item(len(presets) + 1, '🔧 Свой набор PID', 'Введите PID вручную')
            self.display.print_menu_item(len(presets) + 2, '🔙 Назад')

            try:
                choice = input(f"\n  {ColorScheme.BOLD}Выберите пресет:{ColorScheme.RESET} ").strip()
                if choice.lower() == 'q':
                    return

                idx = int(choice)
                if 1 <= idx <= len(presets):
                    preset = preset_items[idx - 1][1]
                    self._run_monitoring(
                        preset['commands'],
                        preset['interval'],
                        preset['name']
                    )
                elif idx == len(presets) + 1:
                    self._custom_monitoring()
                elif idx == len(presets) + 2:
                    break
            except ValueError:
                self.display.print_warning("Неверный ввод")
                time.sleep(1)

    def _run_monitoring(self, command_list: List[tuple], interval: float, title: str):
        """Запускает мониторинг"""
        clear_screen()

        pids = [cmd for cmd, _ in command_list]
        descriptions = [desc for _, desc in command_list]

        self.display.print_realtime_header(pids, descriptions)
        print(f"\r  ║  {ColorScheme.DIM}Нажмите Ctrl+C для остановки{ColorScheme.RESET}".ljust(78) + "║")
        print(f"\r  ╚{'═' * 76}╝")

        try:
            while True:
                results = []

                for cmd, _ in command_list:
                    try:
                        response = self.connection.send_command(cmd, timeout=2)
                        pid = cmd.replace('01 ', '')
                        result = self.parser.parse_response(pid, response)
                        if result:
                            results.append(result)
                            self._log_data(result)
                    except:
                        pass
                    time.sleep(0.02)  # Минимальная задержка

                if results:
                    self.display.print_realtime_values(results, pids)

                time.sleep(interval - len(command_list) * 0.02)

        except KeyboardInterrupt:
            print(f"\n\n  {ColorScheme.info('⏹️ Мониторинг остановлен')}")
            time.sleep(1)

    def _custom_monitoring(self):
        """Пользовательский мониторинг"""
        print(f"\n  Введите PID через запятую (например: 0C,0D,05)")
        print(f"  {ColorScheme.DIM}Популярные: 04,05,0B,0C,0D,0F,10,11,2F,46,5C{ColorScheme.RESET}")

        pids_input = input(f"  PID: ").strip()
        if not pids_input:
            return

        try:
            interval = float(input(f"  Интервал обновления (сек, по умолчанию 1.0): ") or "1.0")
        except:
            interval = 1.0

        pids = [pid.strip() for pid in pids_input.split(',')]
        command_list = [(f'01 {pid}', f'PID {pid}') for pid in pids]

        self._run_monitoring(command_list, interval, "Пользовательский мониторинг")

    # ============================================================
    # МЕНЮ AT КОМАНД
    # ============================================================
    def _menu_at_commands(self):
        """Меню AT команд"""
        while True:
            clear_screen()
            print_header("⚙️ НАСТРОЙКИ АДАПТЕРА (AT КОМАНДЫ)")

            at_groups = self.db.at_commands.subgroups
            group_items = list(at_groups.items())

            for i, (key, group) in enumerate(group_items, 1):
                self.display.print_menu_item(i, group.name, group.description)

            self.display.print_menu_item(len(group_items) + 1, '📝 Своя AT команда', 'Ввести AT команду вручную')
            self.display.print_menu_item(len(group_items) + 2, '🔙 Назад')

            try:
                choice = input(f"\n  {ColorScheme.BOLD}Выберите группу:{ColorScheme.RESET} ").strip()
                if choice.lower() == 'q':
                    return

                idx = int(choice)
                if 1 <= idx <= len(group_items):
                    self._show_at_group(group_items[idx - 1][1])
                elif idx == len(group_items) + 1:
                    self._send_custom_at()
                elif idx == len(group_items) + 2:
                    break
            except ValueError:
                self.display.print_warning("Неверный ввод")
                time.sleep(1)

    def _show_at_group(self, group: CommandGroup):
        """Показывает группу AT команд"""
        while True:
            clear_screen()
            print_header(f"⚙️ {group.name}")

            for i, cmd in enumerate(group.commands, 1):
                self.display.print_menu_item(i, f"{cmd.icon} {cmd.description}")
                print(f"      {ColorScheme.DIM}Команда: {ColorScheme.highlight(cmd.command)}{ColorScheme.RESET}")

            self.display.print_menu_item(len(group.commands) + 1, '🔙 Назад')

            try:
                choice = input(f"\n  {ColorScheme.BOLD}Выберите команду:{ColorScheme.RESET} ").strip()
                if choice.lower() == 'q':
                    return

                idx = int(choice)
                if 1 <= idx <= len(group.commands):
                    self._send_at_command(group.commands[idx - 1])
                elif idx == len(group.commands) + 1:
                    break
            except ValueError:
                self.display.print_warning("Неверный ввод")
                time.sleep(1)

    def _send_at_command(self, cmd: Command):
        """Отправляет AT команду"""
        print(f"\n  ⚙️ {cmd.description}")
        print(f"  Команда: {ColorScheme.highlight(cmd.command)}")

        try:
            response = self.connection.send_command(cmd.command)
            print(f"  Ответ: {ColorScheme.info(response)}")
        except Exception as e:
            self.display.print_error(f"Ошибка: {str(e)}")

        input(f"\n  {ColorScheme.DIM}Нажмите Enter для продолжения...{ColorScheme.RESET}")

    def _send_custom_at(self):
        """Отправляет свою AT команду"""
        command = input(f"\n  Введите AT команду (например, ATI): ").strip()
        if not command:
            return

        if not command.upper().startswith('AT'):
            print(f"  {ColorScheme.warning('Предупреждение: команда не начинается с AT')}")

        try:
            response = self.connection.send_command(command)
            print(f"  Ответ: {ColorScheme.info(response)}")
        except Exception as e:
            self.display.print_error(f"Ошибка: {str(e)}")

        input(f"\n  {ColorScheme.DIM}Нажмите Enter для продолжения...{ColorScheme.RESET}")

    # ============================================================
    # ПРОЧИЕ МЕНЮ
    # ============================================================
    def _menu_save_data(self):
        """Меню сохранения данных"""
        clear_screen()
        print_header("💾 СОХРАНЕНИЕ ДАННЫХ")

        if not self.data_log:
            self.display.print_warning("Нет данных для сохранения. Сначала прочитайте параметры.")
            time.sleep(2)
            return

        print(f"  Записей в логе: {ColorScheme.highlight(str(len(self.data_log)))}")
        print(f"\n  Выберите формат:")
        self.display.print_menu_item(1, '📄 JSON формат', 'Рекомендуется для дальнейшей обработки')
        self.display.print_menu_item(2, '📊 CSV формат', 'Удобно для Excel')
        self.display.print_menu_item(3, '🔙 Назад')

        try:
            choice = input(f"\n  {ColorScheme.BOLD}Выберите формат:{ColorScheme.RESET} ").strip()

            if choice == '1':
                filepath = DataSaver.save_to_json(self.data_log)
                self.display.print_success(f"Данные сохранены: {filepath}")
            elif choice == '2':
                filepath = DataSaver.save_to_csv(self.data_log)
                self.display.print_success(f"Данные сохранены: {filepath}")
        except Exception as e:
            self.display.print_error(f"Ошибка сохранения: {str(e)}")

        time.sleep(2)

    def _menu_reconnect(self):
        """Переподключение"""
        if self.connection:
            self.connection.disconnect()

        self.data_log = []
        self._connect_device()
        self._initialize_device()
        self.display.print_success("Переподключение выполнено успешно!")
        time.sleep(1)

    def _menu_exit(self):
        """Выход из программы"""
        if confirm_action("Выйти из программы?"):
            self._exit_gracefully()

    def _exit_gracefully(self):
        """Корректное завершение"""
        self.running = False

        print(f"\n  {ColorScheme.info('Завершение работы...')}")

        if self.connection:
            try:
                self.connection.send_command('ATPC')  # Сохраняем протокол
            except:
                pass
            self.connection.disconnect()

        if self.data_log:
            try:
                filepath = DataSaver.save_to_json(
                    self.data_log,
                    f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                print(f"  {ColorScheme.info('Данные сессии сохранены: ' + filepath)}")
            except:
                pass

        print(f"  {ColorScheme.success('👋 До свидания!')}")
        sys.exit(0)

    # ============================================================
    # Вспомогательные методы
    # ============================================================
    def _log_data(self, value: ParsedValue):
        """Сохраняет значение в лог"""
        self.data_log.append({
            'timestamp': get_timestamp(),
            **value.to_dict()
        })
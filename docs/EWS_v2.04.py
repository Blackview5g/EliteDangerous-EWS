import os
import sys
import json
import time
import queue
import configparser
import threading
from pathlib import Path
import pygame

# Графическая библиотека
import customtkinter as ctk
from tkinter import filedialog

# ------------------------------------------------------------
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ПУТИ К ПАПКЕ С .EXE (или .py)
# ------------------------------------------------------------
def get_base_path() -> Path:
    """Возвращает директорию, где находится исполняемый файл (или скрипт)."""
    if getattr(sys, 'frozen', False):
        # Запущено как скомпилированный .exe
        return Path(sys.executable).parent
    else:
        # Запущено как скрипт .py
        return Path(__file__).parent

# ------------------------------------------------------------
# ВЕРСИЯ ПРОГРАММЫ
# ------------------------------------------------------------
VERSION = "v2.04"

# ------------------------------------------------------------
# ПУТИ (динамические)
# ------------------------------------------------------------
BASE_DIR = get_base_path()
DEFAULT_LOG_PATH = (
    Path(os.path.expanduser("~"))
    / "Saved Games"
    / "Frontier Developments"
    / "Elite Dangerous"
)
CONFIG_FILE = BASE_DIR / "EWSconfig.ini"
DEFAULT_SOUNDS_PATH = BASE_DIR / "EWSsounds"

# Инициализация звуковой системы
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Предупреждение: не удалось инициализировать звук: {e}")

# ------------------------------------------------------------
# ЛОКАЛИЗАЦИЯ (словари)
# ------------------------------------------------------------
LOCALIZATION = {
    "RU": {
        "title": f"Elite Dangerous - EWS {VERSION}",
        "game_logs_title": "Путь к журналам Elite Dangerous",
        "mode_auto": "Автоматически",
        "mode_manual": "Вручную",
        "browse_btn": "Обзор",
        "sound_settings_title": "Настройки звуковых пакетов",
        "lang_label": "Язык пакета:",
        "sound_dir_label": "Папка со звуками:",
        "sound_ews_off_cb": "Звук слепого прыжка (EWS_off)",
        "sound_unstable_cb": "Звук нестабильности (unstable)",
        "sound_dropped_cb": "Звук выдергивания (dropped)",
        "sound_targoid_cb": "Звук контакта с таргоидами (targoid)",
        "monitor_title": "Монитор состояния системы безопасности",
        "start_btn": "ЗАПУСТИТЬ МОНИТОРИНГ",
        "stop_btn": "ОСТАНОВИТЬ",
        "log_err_no_audio": "[Ошибка] Файл звука не найден: {path}",
        "log_err_no_logs": "[Ошибка] Лог-файлы игры не найдены в указанной директории.",
        "log_err_internal": "[Внутренняя ошибка]: {msg}",
        "log_engine_started": "Модуль EWS запущен. Отслеживание лога: {name}",
        "log_engine_stopped": "Модуль EWS остановлен.",
        "log_log_rotated": ">>> Переключение на новый лог: {name}",
        "evt_route_jump": ">>> МАРШРУТНЫЙ прыжок в {system} (Цель A:{addr}). СРП активен.",
        "evt_blind_jump": ">>> СЛЕПОЙ одиночный прыжок в {system} (Цель A:{addr}). СРП отключен.",
        "evt_unstable": "!!! ТРЕВОГА: Пространство нестабильно, возможен перехват (A == B) !!!",
        "evt_route_confirmed": "--- Ответ сервера: Маршрут подтвержден (B:{addr}) ---",
        "evt_final_confirmed": "--- Ответ сервера: Финальный прыжок подтвержден ---",
        "evt_dropped": "!!! ТРЕВОГА: Нас выдернули из прыжка в {system} !!!",
        "evt_jump_success_blind": "Выход из слепого прыжка в {system} штатно.",
        "evt_jump_success_route": "Выход из маршрутного прыжка в {system} штатно.",
        "evt_thargoid": "!!! ПОДТВЕРЖДЕН КОНТАКТ С ТАРГОИДАМИ: Обнаружена сигнатура !!!",
        "evt_timeout": "!!! ТАЙМАУТ СЕРВЕРА (60с): Сервер завис, сброс ожидания !!!",
    },
    "EN": {
        "title": f"Elite Dangerous - EWS {VERSION}",
        "game_logs_title": "Elite Dangerous Journals Path",
        "mode_auto": "Automatic",
        "mode_manual": "Manual",
        "browse_btn": "Browse",
        "sound_settings_title": "Audio Pack Settings",
        "lang_label": "Voice Pack Language:",
        "sound_dir_label": "Sounds Folder:",
        "sound_ews_off_cb": "Blind jump sound (EWS_off)",
        "sound_unstable_cb": "Unstable space sound (unstable)",
        "sound_dropped_cb": "Dropped sound (dropped)",
        "sound_targoid_cb": "Thargoid contact sound (targoid)",
        "monitor_title": "Security System Status Monitor",
        "start_btn": "START MONITORING",
        "stop_btn": "STOP",
        "log_err_no_audio": "[Error] Audio file not found: {path}",
        "log_err_no_logs": "[Error] Game log files not found in the specified directory.",
        "log_err_internal": "[Internal Error]: {msg}",
        "log_engine_started": "EWS Module started. Tracking log: {name}",
        "log_engine_stopped": "EWS Module stopped.",
        "log_log_rotated": ">>> Switched to a new log file: {name}",
        "evt_route_jump": ">>> ROUTE jump to {system} (Target A:{addr}). EWS active.",
        "evt_blind_jump": ">>> BLIND single jump to {system} (Target A:{addr}). EWS disabled.",
        "evt_unstable": "!!! WARNING: Hyper-space unstable, interdiction imminent (A == B) !!!",
        "evt_route_confirmed": "--- Server response: Route confirmed (B:{addr}) ---",
        "evt_final_confirmed": "--- Server response: Final jump confirmed ---",
        "evt_dropped": "!!! WARNING: Dropped out of jump in {system} !!!",
        "evt_jump_success_blind": "Exited blind jump in {system} normally.",
        "evt_jump_success_route": "Exited route jump in {system} normally.",
        "evt_thargoid": "!!! THARGOID CONTACT CONFIRMED: Signature detected !!!",
        "evt_timeout": "!!! SERVER TIMEOUT (60s): Server hung, resetting state !!!",
    },
}

# ------------------------------------------------------------
# ДВИЖОК EWS
# ------------------------------------------------------------
class EWS_Engine:
    def __init__(self, log_callback):
        self.log_callback = log_callback
        self.running = False
        self.lang = "RU"

        # Индивидуальные настройки звуков
        self.sound_ews_off = True
        self.sound_unstable = True
        self.sound_dropped = True
        self.sound_targoid = True

        # Логика игры
        self.self_in_route = False
        self.addr_a = None
        self.addr_b = None
        self.target_system_name = None
        self.jump_start_time = 0
        self.is_jumping = False
        self.blind_jump = False
        self.alert_played = False
        self.interdiction_occurred = False
        self._sound_cache = {}
        self.last_nav_mtime = 0
        self.log_dir = None          # будет сохранён при старте

    def get_msg(self, key, **kwargs):
        template = LOCALIZATION[self.lang].get(key, "")
        return template.format(**kwargs)

    def log(self, key, tag="normal", **kwargs):
        self.log_callback(self.get_msg(key, **kwargs), tag)

    def play(self, sound_dir, sound_name):
        if sound_name == "EWS_off" and not self.sound_ews_off:
            return
        if sound_name == "unstable" and not self.sound_unstable:
            return
        if sound_name == "dropped" and not self.sound_dropped:
            return
        if sound_name == "targoid" and not self.sound_targoid:
            return

        lang_subfolder = Path(sound_dir) / self.lang.lower()
        target_file = None
        for ext in [".ogg", ".mp3"]:
            test_path = lang_subfolder / f"{sound_name}{ext}"
            if test_path.exists():
                target_file = test_path
                break

        if not target_file:
            target_file = lang_subfolder / f"{sound_name}.ogg"

        str_path = str(target_file)
        if target_file.exists():
            if str_path not in self._sound_cache:
                try:
                    self._sound_cache[str_path] = pygame.mixer.Sound(str_path)
                except Exception as e:
                    self.log_callback(f"[Sound error] {e}", "error")
                    return
            self._sound_cache[str_path].play()
        else:
            self.log_callback(self.get_msg("log_err_no_audio", path=str_path), "error")

    def reset_logic(self):
        self.addr_a = None
        self.addr_b = None
        self.jump_start_time = 0
        self.is_jumping = False
        self.blind_jump = False
        self.alert_played = False
        # interdiction_occurred не сбрасываем здесь – только при завершении перехвата или таймауте

    def process_event(self, event, sound_dir):
        name = event.get("event")

        if name == "StartJump" and event.get("JumpType") == "Hyperspace":
            self.reset_logic()
            self.is_jumping = True
            self.addr_a = event.get("SystemAddress")
            self.target_system_name = event.get("StarSystem")

            if self.self_in_route:
                self.jump_start_time = time.time()
                self.log(
                    "evt_route_jump",
                    "info",
                    system=self.target_system_name,
                    addr=self.addr_a,
                )
            else:
                self.blind_jump = True
                self.log(
                    "evt_blind_jump",
                    "warning",
                    system=self.target_system_name,
                    addr=self.addr_a,
                )
                self.play(sound_dir, "EWS_off")

        elif name == "FSDTarget" and self.is_jumping and not self.blind_jump:
            self.addr_b = event.get("SystemAddress")
            self.jump_start_time = 0

            # Если мы получили FSDTarget – значит, маршрут точно есть (обновляем флаг)
            self.self_in_route = True

            if self.addr_a == self.addr_b:
                self.log("evt_unstable", "danger")
                self.play(sound_dir, "unstable")
                self.alert_played = True
                self.interdiction_occurred = True
            else:
                self.log("evt_route_confirmed", "success", addr=self.addr_b)

        elif name == "NavRouteClear" and self.is_jumping and not self.blind_jump:
            self.addr_b = 0
            self.jump_start_time = 0
            # Маршрут закончился
            self.self_in_route = False
            self.log("evt_final_confirmed", "success")

        elif name == "FSDJump":
            current_system = event.get("StarSystem")
            current_address = event.get("SystemAddress")
            self.jump_start_time = 0

            if self.blind_jump and current_address != self.addr_a:
                self.log("evt_dropped", "danger", system=current_system)
                self.play(sound_dir, "dropped")
                self.interdiction_occurred = True
            elif self.alert_played:
                self.log("evt_dropped", "danger", system=current_system)
                self.play(sound_dir, "dropped")
            else:
                if self.blind_jump:
                    self.log("evt_jump_success_blind", "success", system=current_system)
                else:
                    self.log("evt_jump_success_route", "success", system=current_system)
                # Штатный прыжок – сбрасываем флаг перехвата, если он случайно остался
                self.interdiction_occurred = False

            self.reset_logic()

        elif name == "Music" and event.get("MusicTrack") == "Unknown_Encounter":
            if self.interdiction_occurred:
                self.log("evt_thargoid", "danger")
                self.play(sound_dir, "targoid")
                self.interdiction_occurred = False
            # иначе игнорируем

    def update_timers(self):
        if self.is_jumping and self.jump_start_time > 0:
            if time.time() - self.jump_start_time > 60:
                self.log("evt_timeout", "error")
                self.reset_logic()
                self.interdiction_occurred = False

    def check_nav_route(self, log_dir):
        if not log_dir:
            return
        nav_file = Path(log_dir) / "NavRoute.json"
        if not nav_file.exists():
            return

        try:
            current_mtime = nav_file.stat().st_mtime
            if current_mtime > self.last_nav_mtime:
                self.last_nav_mtime = current_mtime
                with open(nav_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if data.get("event") == "NavRouteClear" or not data.get("Route"):
                            self.self_in_route = False
                        else:
                            self.self_in_route = True
                    else:
                        self.self_in_route = False
        except Exception:
            pass

    def start_loop(
        self,
        log_dir,
        sound_dir,
        current_lang,
        sound_ews_off,
        sound_unstable,
        sound_dropped,
        sound_targoid,
    ):
        self.running = True
        self.lang = current_lang
        self.sound_ews_off = sound_ews_off
        self.sound_unstable = sound_unstable
        self.sound_dropped = sound_dropped
        self.sound_targoid = sound_targoid
        self.log_dir = Path(log_dir)

        log_path = self.log_dir
        def get_latest_log():
            files = list(log_path.glob("Journal.*.log"))
            return max(files, key=os.path.getmtime) if files else None

        current_log = get_latest_log()
        if not current_log:
            self.log_callback(self.get_msg("log_err_no_logs"), "error")
            self.running = False
            return

        self.log("log_engine_started", "success", name=current_log.name)

        nav_file = log_path / "NavRoute.json"
        if nav_file.exists():
            self.last_nav_mtime = nav_file.stat().st_mtime
        self.check_nav_route(log_path)

        file_ptr = open(current_log, "r", encoding="utf-8")
        file_ptr.seek(0, 2)

        last_periodic_check = time.time()

        while self.running:
            now = time.time()

            if now - last_periodic_check > 2.0:
                last_periodic_check = now
                latest_log = get_latest_log()
                if latest_log and latest_log != current_log:
                    self.log("log_log_rotated", "info", name=latest_log.name)
                    file_ptr.close()
                    current_log = latest_log
                    file_ptr = open(current_log, "r", encoding="utf-8")
                    file_ptr.seek(0, 2)
                    continue

                self.check_nav_route(log_path)

            self.update_timers()

            line = file_ptr.readline()
            if not line:
                time.sleep(0.1)
                continue

            try:
                event = json.loads(line)
                self.process_event(event, sound_dir)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                self.log_callback(self.get_msg("log_err_internal", msg=str(e)), "error")

        file_ptr.close()
        self.log("log_engine_stopped", "info")

# ------------------------------------------------------------
# ГЛАВНОЕ ОКНО (customtkinter)
# ------------------------------------------------------------
class EWS_App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("670x720" if os.name == "nt" else "680x740")
        self.resizable(False, False)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.engine = EWS_Engine(self.queue_log_message)
        self.log_queue = queue.Queue()
        self.engine_thread = None
        self._text_widget = None

        # Переменные настроек
        self.log_mode = ctk.StringVar(value="auto")
        self.log_dir_path = ctk.StringVar(value=str(DEFAULT_LOG_PATH))
        self.lang = ctk.StringVar(value="RU")
        self.sound_dir_path = ctk.StringVar(value=str(DEFAULT_SOUNDS_PATH))
        self.sound_ews_off = ctk.BooleanVar(value=True)
        self.sound_unstable = ctk.BooleanVar(value=True)
        self.sound_dropped = ctk.BooleanVar(value=True)
        self.sound_targoid = ctk.BooleanVar(value=True)

        # Гарантируем создание папки для звуков по умолчанию (пустая, но существует)
        DEFAULT_SOUNDS_PATH.mkdir(parents=True, exist_ok=True)

        # Загружаем конфиг (создаёт, если нет)
        self._ensure_config()
        self.load_config()
        self.create_widgets()
        self.setup_text_tags()
        self.update_ui_strings()

        self.after(100, self.process_log_queue)

    def _ensure_config(self):
        """Создаёт конфиг со значениями по умолчанию, если файл отсутствует."""
        if not CONFIG_FILE.exists():
            config = configparser.ConfigParser()
            config["Settings"] = {
                "log_mode": "auto",
                "log_dir": str(DEFAULT_LOG_PATH),
                "language": "RU",
                "sound_dir": str(DEFAULT_SOUNDS_PATH),
                "sound_ews_off": "True",
                "sound_unstable": "True",
                "sound_dropped": "True",
                "sound_targoid": "True",
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                config.write(f)

    def get_text_widget(self):
        if self._text_widget is not None:
            return self._text_widget
        if hasattr(self.txt_monitor, "_textbox"):
            self._text_widget = self.txt_monitor._textbox
        elif hasattr(self.txt_monitor, "_textwidget"):
            self._text_widget = self.txt_monitor._textwidget
        elif hasattr(self.txt_monitor, "text"):
            self._text_widget = self.txt_monitor.text
        else:
            for attr in ("_tkinter_text", "_tk_text", "entry"):
                if hasattr(self.txt_monitor, attr):
                    self._text_widget = getattr(self.txt_monitor, attr)
                    break
            else:
                self._text_widget = self.txt_monitor
        return self._text_widget

    def setup_text_tags(self):
        text_widget = self.get_text_widget()
        text_widget.tag_config("normal", foreground="#FFFFFF")
        text_widget.tag_config("info", foreground="#3399FF")
        text_widget.tag_config("success", foreground="#00FF66")
        text_widget.tag_config("warning", foreground="#FFCC00")
        text_widget.tag_config("danger", foreground="#FF3333")
        text_widget.tag_config("error", foreground="#FF00FF")

    def create_widgets(self):
        # БЛОК ЛОГОВ
        self.frame_logs = ctk.CTkFrame(self)
        self.frame_logs.pack(fill="x", padx=15, pady=10)

        self.lbl_game_logs = ctk.CTkLabel(self.frame_logs, text="", font=("Arial", 14, "bold"))
        self.lbl_game_logs.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=5)

        self.rb_auto = ctk.CTkRadioButton(
            self.frame_logs, text="", variable=self.log_mode, value="auto",
            command=self.toggle_log_mode
        )
        self.rb_auto.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.rb_manual = ctk.CTkRadioButton(
            self.frame_logs, text="", variable=self.log_mode, value="manual",
            command=self.toggle_log_mode
        )
        self.rb_manual.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        self.entry_log_dir = ctk.CTkEntry(self.frame_logs, textvariable=self.log_dir_path, width=450)
        self.entry_log_dir.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="we")

        self.btn_browse_log = ctk.CTkButton(self.frame_logs, text="", width=80, command=self.browse_log_dir)
        self.btn_browse_log.grid(row=2, column=2, padx=10, pady=5)

        # БЛОК ЗВУКОВ
        self.frame_sounds = ctk.CTkFrame(self)
        self.frame_sounds.pack(fill="x", padx=15, pady=10)

        self.lbl_sound_title = ctk.CTkLabel(self.frame_sounds, text="", font=("Arial", 14, "bold"))
        self.lbl_sound_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=5)

        self.lbl_lang = ctk.CTkLabel(self.frame_sounds, text="")
        self.lbl_lang.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.combo_lang = ctk.CTkComboBox(
            self.frame_sounds, values=["RU", "EN"], variable=self.lang,
            command=self.on_language_changed, width=100
        )
        self.combo_lang.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        self.cb_ews_off = ctk.CTkCheckBox(self.frame_sounds, text="", variable=self.sound_ews_off)
        self.cb_ews_off.grid(row=2, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.cb_unstable = ctk.CTkCheckBox(self.frame_sounds, text="", variable=self.sound_unstable)
        self.cb_unstable.grid(row=3, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.cb_dropped = ctk.CTkCheckBox(self.frame_sounds, text="", variable=self.sound_dropped)
        self.cb_dropped.grid(row=4, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.cb_targoid = ctk.CTkCheckBox(self.frame_sounds, text="", variable=self.sound_targoid)
        self.cb_targoid.grid(row=5, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.lbl_sound_dir = ctk.CTkLabel(self.frame_sounds, text="")
        self.lbl_sound_dir.grid(row=6, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.entry_sound_dir = ctk.CTkEntry(self.frame_sounds, textvariable=self.sound_dir_path, width=450)
        self.entry_sound_dir.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky="we")

        self.btn_browse_sounds = ctk.CTkButton(self.frame_sounds, text="", width=80, command=self.browse_sound_dir)
        self.btn_browse_sounds.grid(row=7, column=2, padx=10, pady=5)

        # МОНИТОР
        self.frame_monitor = ctk.CTkFrame(self)
        self.frame_monitor.pack(fill="both", expand=True, padx=15, pady=10)

        self.lbl_monitor = ctk.CTkLabel(self.frame_monitor, text="", font=("Arial", 12, "italic"))
        self.lbl_monitor.pack(anchor="w", padx=10, pady=2)

        self.txt_monitor = ctk.CTkTextbox(self.frame_monitor, height=120, font=("Consolas", 11), state="disabled")
        self.txt_monitor.pack(fill="both", expand=True, padx=10, pady=5)

        # КНОПКИ
        self.frame_ctrl = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_ctrl.pack(fill="x", padx=15, pady=10)

        self.btn_start = ctk.CTkButton(
            self.frame_ctrl, text="", fg_color="green", hover_color="darkgreen",
            height=35, font=("Arial", 13, "bold"), command=self.start_monitoring
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_stop = ctk.CTkButton(
            self.frame_ctrl, text="", fg_color="red", hover_color="darkred",
            height=35, font=("Arial", 13, "bold"), command=self.stop_monitoring, state="disabled"
        )
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=5)

        self.toggle_log_mode()

    def update_ui_strings(self):
        lng = self.lang.get()
        strings = LOCALIZATION[lng]

        self.title(strings["title"])
        self.lbl_game_logs.configure(text=strings["game_logs_title"])
        self.rb_auto.configure(text=strings["mode_auto"])
        self.rb_manual.configure(text=strings["mode_manual"])
        self.btn_browse_log.configure(text=strings["browse_btn"])

        self.lbl_sound_title.configure(text=strings["sound_settings_title"])
        self.lbl_lang.configure(text=strings["lang_label"])
        self.cb_ews_off.configure(text=strings["sound_ews_off_cb"])
        self.cb_unstable.configure(text=strings["sound_unstable_cb"])
        self.cb_dropped.configure(text=strings["sound_dropped_cb"])
        self.cb_targoid.configure(text=strings["sound_targoid_cb"])
        self.lbl_sound_dir.configure(text=strings["sound_dir_label"])
        self.btn_browse_sounds.configure(text=strings["browse_btn"])

        self.lbl_monitor.configure(text=strings["monitor_title"])
        self.btn_start.configure(text=strings["start_btn"])
        self.btn_stop.configure(text=strings["stop_btn"])

    def toggle_log_mode(self):
        if self.log_mode.get() == "auto":
            self.log_dir_path.set(str(DEFAULT_LOG_PATH))
            self.entry_log_dir.configure(state="disabled")
            self.btn_browse_log.configure(state="disabled")
        else:
            self.entry_log_dir.configure(state="normal")
            self.btn_browse_log.configure(state="normal")

    def browse_log_dir(self):
        dir_selected = filedialog.askdirectory(initialdir=self.log_dir_path.get())
        if dir_selected:
            self.log_dir_path.set(dir_selected)

    def browse_sound_dir(self):
        dir_selected = filedialog.askdirectory(initialdir=self.sound_dir_path.get())
        if dir_selected:
            self.sound_dir_path.set(dir_selected)

    def on_language_changed(self, choice):
        self.update_ui_strings()

    def load_config(self):
        config = configparser.ConfigParser()
        if CONFIG_FILE.exists():
            config.read(CONFIG_FILE, encoding="utf-8")
            self.log_mode.set(config.get("Settings", "log_mode", fallback="auto"))
            self.log_dir_path.set(config.get("Settings", "log_dir", fallback=str(DEFAULT_LOG_PATH)))
            self.lang.set(config.get("Settings", "language", fallback="RU"))
            self.sound_dir_path.set(config.get("Settings", "sound_dir", fallback=str(DEFAULT_SOUNDS_PATH)))
            self.sound_ews_off.set(config.getboolean("Settings", "sound_ews_off", fallback=True))
            self.sound_unstable.set(config.getboolean("Settings", "sound_unstable", fallback=True))
            self.sound_dropped.set(config.getboolean("Settings", "sound_dropped", fallback=True))
            self.sound_targoid.set(config.getboolean("Settings", "sound_targoid", fallback=True))

    def save_config(self):
        config = configparser.ConfigParser()
        config["Settings"] = {
            "log_mode": self.log_mode.get(),
            "log_dir": self.log_dir_path.get(),
            "language": self.lang.get(),
            "sound_dir": self.sound_dir_path.get(),
            "sound_ews_off": str(self.sound_ews_off.get()),
            "sound_unstable": str(self.sound_unstable.get()),
            "sound_dropped": str(self.sound_dropped.get()),
            "sound_targoid": str(self.sound_targoid.get()),
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)

    def queue_log_message(self, text, tag="normal"):
        timestamp = time.strftime("[%H:%M:%S]")
        self.log_queue.put((f"{timestamp} {text}\n", tag))

    def process_log_queue(self):
        text_widget = self.get_text_widget()
        while not self.log_queue.empty():
            msg, tag = self.log_queue.get_nowait()
            self.txt_monitor.configure(state="normal")
            text_widget.insert("end", msg, tag)
            self.txt_monitor.configure(state="disabled")
            text_widget.see("end")
        self.after(100, self.process_log_queue)

    def start_monitoring(self):
        self.save_config()

        sound_directory = self.sound_dir_path.get()
        log_directory = self.log_dir_path.get()
        current_lang = self.lang.get()
        ews_off = self.sound_ews_off.get()
        unstable = self.sound_unstable.get()
        dropped = self.sound_dropped.get()
        targoid = self.sound_targoid.get()

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.combo_lang.configure(state="disabled")
        self.cb_ews_off.configure(state="disabled")
        self.cb_unstable.configure(state="disabled")
        self.cb_dropped.configure(state="disabled")
        self.cb_targoid.configure(state="disabled")
        self.entry_log_dir.configure(state="disabled")
        self.btn_browse_log.configure(state="disabled")
        self.entry_sound_dir.configure(state="disabled")
        self.btn_browse_sounds.configure(state="disabled")

        self.engine_thread = threading.Thread(
            target=self.engine.start_loop,
            args=(
                log_directory, sound_directory, current_lang,
                ews_off, unstable, dropped, targoid
            ),
            daemon=True
        )
        self.engine_thread.start()

    def stop_monitoring(self):
        if self.engine:
            self.engine.running = False

        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.combo_lang.configure(state="normal")
        self.cb_ews_off.configure(state="normal")
        self.cb_unstable.configure(state="normal")
        self.cb_dropped.configure(state="normal")
        self.cb_targoid.configure(state="normal")
        self.entry_sound_dir.configure(state="normal")
        self.btn_browse_sounds.configure(state="normal")
        self.toggle_log_mode()

# ------------------------------------------------------------
# ТОЧКА ВХОДА
# ------------------------------------------------------------
if __name__ == "__main__":
    app = EWS_App()
    app.mainloop()
#!/usr/bin/env python3
"""
Elite Dangerous EWS (Early Warning System) Module
Based on two specification documents:
- v1: RemainingJumpsInRoute comparison
- v2: SystemAddress comparison + blind jump detection
"""

import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any

# Для воспроизведения звука (установите simpleaudio или pygame)
try:
    import simpleaudio as sa
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    print("simpleaudio not installed. Sound disabled.")

# Константы
JOURNAL_DIR = Path.home() / "Saved Games" / "Frontier Developments" / "Elite Dangerous"
TIMEOUT_SECONDS = 60
FSDTARGET_DELAY_SECONDS = 7  # для информационных сообщений, не критично


class EWS:
    def __init__(self, sound_enabled=True):
        self.A: Optional[int] = None          # SystemAddress из StartJump
        self.B: Optional[int] = None          # SystemAddress из FSDTarget или 0 из NavRouteClear
        self.in_route: bool = False           # флаг из NavRoute.json
        self.timer: Optional[threading.Timer] = None
        self.waiting_for_response: bool = False
        self.last_start_system: Optional[int] = None
        self.route_mode_this_jump: bool = False
        self.alert_triggered: bool = False
        self.sound_enabled = sound_enabled and SOUND_AVAILABLE
        self._stop_event = threading.Event()

    def _reset_timer(self):
        """Сброс 60-секундного таймера, если он запущен."""
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.waiting_for_response = False

    def _start_timer(self):
        """Запуск таймера на 60 секунд."""
        self._reset_timer()
        self.waiting_for_response = True
        self.timer = threading.Timer(TIMEOUT_SECONDS, self._on_timer_expired)
        self.timer.daemon = True
        self.timer.start()

    def _on_timer_expired(self):
        """Таймаут: сервер не ответил, прыжок считается слепым или зависшим."""
        self.waiting_for_response = False
        self.route_mode_this_jump = False
        print("[EWS] Таймаут 60 сек: ответа от сервера не получено. Прыжок считается слепым или игра выкинула в меню.")
        # Логика: сбрасываем состояние, ждём следующий StartJump

    def _play_sound(self, sound_name: str):
        """Воспроизведение .ogg файла из папки sounds/"""
        if not self.sound_enabled:
            return
        sound_path = Path(__file__).parent.parent / "sounds" / f"{sound_name}.ogg"
        if sound_path.exists():
            try:
                wave_obj = sa.WaveObject.from_wave_file(str(sound_path.with_suffix(".wav")))
                # simpleaudio не поддерживает .ogg, нужно конвертировать в .wav.
                # Для простоты: используем pygame или playsound.
                # Здесь заглушка:
                print(f"[SOUND] Playing {sound_name}.ogg")
            except Exception as e:
                print(f"[SOUND] Error: {e}")
        else:
            print(f"[SOUND] File {sound_path} not found")

    def on_navroute(self, event: Dict[str, Any]):
        """Обработка события NavRoute (из NavRoute.json)."""
        # В реальном Journal.json события NavRoute нет, но есть NavRoute.json файл.
        # Здесь подразумеваем, что внешний код вызывает этот метод при изменении маршрута.
        self.in_route = True
        print("[EWS] Маршрут построен (in_route = True)")

    def on_navroute_clear(self, event: Dict[str, Any]):
        """Событие NavRouteClear — конец маршрута."""
        if self.waiting_for_response:
            # Это ответ сервера для финального прыжка
            self.B = 0
            print("[EWS] Ответ сервера: Финальный прыжок подтверждён (NavRouteClear)")
            self._reset_timer()
            self.route_mode_this_jump = False
        self.in_route = False
        print("[EWS] Маршрут сброшен (in_route = False)")

    def on_fsd_target(self, event: Dict[str, Any]):
        """Событие FSDTarget — подтверждение сервера во время прыжка."""
        if not self.waiting_for_response:
            # Игнорируем FSDTarget не во время прыжка (например, на карте)
            return
        self.B = event.get("SystemAddress")
        if self.B is None:
            return

        print(f"[EWS] FSDTarget: B = {self.B}, A = {self.A}")
        # Проверка по логике v2: если A == B -> перехват
        if self.route_mode_this_jump and self.A is not None:
            if self.A == self.B:
                # Тревога!
                self.alert_triggered = True
                print("[EWS] ПРОСТРАНСТВО НЕСТАБИЛЬНО, ВОЗМОЖЕН ПЕРЕХВАТ!")
                self._play_sound("unstable")
            else:
                print("[EWS] Ответ сервера: Маршрут подтверждён, всё штатно.")
        # Сброс таймера в любом случае
        self._reset_timer()

    def on_start_jump(self, event: Dict[str, Any]):
        """Событие StartJump (JumpType = Hyperspace)."""
        if event.get("JumpType") != "Hyperspace":
            return
        self.last_start_system = event.get("SystemAddress")
        self.A = self.last_start_system
        self.alert_triggered = False
        self.route_mode_this_jump = self.in_route

        if self.route_mode_this_jump:
            print(f"[EWS] Маршрутный прыжок. Цель A = {self.A}")
            self._start_timer()
        else:
            print(f"[EWS] Слепой прыжок (без маршрута). Цель A = {self.A}")
            # В слепом прыжке таймер не ждём FSDTarget, но запускаем для защиты от полного зависания
            self._start_timer()   # можно не запускать, но по инструкции лучше запустить, просто не ждать событий
            # Однако в слепом прыжке мы не получим FSDTarget/NavRouteClear, таймер просто истечёт
            # Но это нормально, мы обработаем факт прибытия в FSDJump.

    def on_fsd_jump(self, event: Dict[str, Any]):
        """Событие FSDJump — выход из гиперпространства."""
        arrived_system = event.get("SystemAddress")
        print(f"[EWS] FSDJump: прибыли в систему {arrived_system}")

        # Сначала сброс таймера (чтобы не истек после прибытия)
        self._reset_timer()

        # Определение, был ли перехват
        interdicted = False
        if self.route_mode_this_jump:
            # Маршрутный прыжок
            if self.alert_triggered:
                interdicted = True
            else:
                # Если тревоги не было, но прибыли не в ту систему (редко, но возможно)
                if self.last_start_system is not None and self.last_start_system != arrived_system:
                    interdicted = True
                else:
                    interdicted = False
        else:
            # Слепой прыжок: сравниваем целевую и фактическую системы
            if self.last_start_system is not None and self.last_start_system != arrived_system:
                interdicted = True
            else:
                interdicted = False

        if interdicted:
            print(f"[EWS] !!! ТРЕВОГА: Нас выдернули из прыжка в систему {arrived_system} !!!")
            self._play_sound("dropped")
            # После этого игра вызовет Unknown_Encounter и SystemsShutdown
        else:
            print(f"[EWS] Выход из прыжка в систему {arrived_system} штатно.")

        # Сброс переменных для следующего прыжка
        self.A = None
        self.B = None
        self.route_mode_this_jump = False
        self.alert_triggered = False
        self.last_start_system = None

    def stop(self):
        """Остановка модуля."""
        self._stop_event.set()
        self._reset_timer()


# Пример использования с чтением журнала (не входит в модуль, для демонстрации)
def monitor_journal(journal_path: Path, ews: EWS):
    """Простой монитор журнала — читает новые строки и парсит JSON."""
    journal_path = journal_path / "Journal.2026-06-04.log"  # пример
    with open(journal_path, 'r') as f:
        f.seek(0, 2)  # конец файла
        while not ews._stop_event.is_set():
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            try:
                event = json.loads(line)
                e_type = event.get("event")
                if e_type == "StartJump":
                    ews.on_start_jump(event)
                elif e_type == "FSDTarget":
                    ews.on_fsd_target(event)
                elif e_type == "NavRouteClear":
                    ews.on_navroute_clear(event)
                elif e_type == "FSDJump":
                    ews.on_fsd_jump(event)
                # Другие события (Music, Unknown_Encounter) игнорируются EWS
            except json.JSONDecodeError:
                pass


if __name__ == "__main__":
    ews = EWS(sound_enabled=False)  # отключим звук для теста
    print("EWS Module Started. Waiting for journal events...")
    # В реальном коде нужно динамически находить последний журнал.
    # Здесь заглушка.
    try:
        # Для теста можно вручную вызвать методы с примерами из инструкции
        # ews.on_start_jump({"JumpType":"Hyperspace","SystemAddress":224644818084})
        # time.sleep(8)
        # ews.on_fsd_target({"SystemAddress":224644818306})
        # ews.on_fsd_jump({"SystemAddress":224644818306})
        pass
    except KeyboardInterrupt:
        ews.stop()
        print("EWS Stopped.")
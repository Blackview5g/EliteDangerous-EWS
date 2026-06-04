# 🛰️ Elite Dangerous: EWS Module Logic (v2 — SystemAddress-based)

This is an alternative/updated technical specification of the **EWS (Early Warning System)** module logic for *Elite Dangerous*. It uses `SystemAddress` comparison instead of `RemainingJumpsInRoute`, includes real journal examples, and clarifies "blind jump" detection.

Это альтернативная/обновлённая спецификация логики модуля **EWS (Early Warning System)** для игры *Elite Dangerous*. В ней используется сравнение `SystemAddress` вместо `RemainingJumpsInRoute`, приведены реальные примеры журналов и уточнено детектирование «слепого прыжка».

---

## 🇷🇺 Русский

### 1. Базовые принципы (дополнение к первой инструкции)

* Основной идентификатор системы — **`SystemAddress`** (числовой). Сравнение строковых имён (`StarSystem`) допускается, но `SystemAddress` надёжнее.
* **Переменные:**
  * **`A`** — `SystemAddress` из `StartJump` (куда игрок целится).
  * **`B`** — `SystemAddress` из `FSDTarget` (подтверждение сервера во время прыжка) или `0` при `NavRouteClear`.
* **Таймер 60 секунд** — защита от лагов. Запускается по `StartJump` (`JumpType: Hyperspace`). Сбрасывается при любом релевантном событии (`FSDTarget`, `NavRouteClear`, `FSDJump`).
* **Маршрутный прыжок** — есть активный маршрут (переменная `in_route = true` из `NavRoute.json`). Сервер присылает `FSDTarget` или `NavRouteClear` в течение 7–10 секунд.
* **Слепой прыжок** — маршрута нет. Сервер не присылает `FSDTarget`/`NavRouteClear`. Детекция перехвата происходит только по факту выхода (`FSDJump`).

---

### 2. Нормальный маршрутный прыжок (много шагов)

1. **Перед прыжком** — переменная `in_route = true`. Есть `NavRoute` + `FSDTarget` (необязательно).
2. `StartJump` → запоминаем `A = SystemAddress`. Запуск таймера 60 с. Вывод: *"Маршрутный прыжок"*.
3. Через ~7 секунд приходит `FSDTarget` с `SystemAddress = B`.  
   - Если `A != B` → всё штатно. Вывод: *"Ответ сервера: Маршрут подтвержден"*. Сброс таймера.  
   - Если `A == B` → **ТРЕВОГА**: *"Пространство нестабильно, возможен перехват"* (проигрывается `unstable.ogg`). Сброс таймера. Через 4–5 секунд — анимация болтанки.
4. Через некоторое время `FSDJump`.  
   - Если была тревога → после `FSDJump` выводим: *"Нас выдернули из прыжка"* (`dropped.ogg`). Затем игра генерирует `Unknown_Encounter`, `SystemsShutdown`.  
   - Если тревоги не было → *"Выход из прыжка штатно"*.
5. Цикл повторяется со следующим `StartJump` и новым `A` из следующей системы.

**Пример нормального маршрутного прыжка (2 прыжка)** см. в логах 10.3.

---

### 3. Перехваченный маршрутный прыжок

1. Маршрут активен. `StartJump` со значением `A = SystemAddress_цели`.
2. Через ~7 секунд приходит `FSDTarget` с **тем же** `SystemAddress` (`B == A`).  
   → Тревога. Вывод: *"Пространство нестабильно, возможен перехват"*.
3. Через 4–5 секунд — анимация. Затем `FSDJump` в **другой** системе (или реже в той же, но перехват факт).
4. После выхода — `Unknown_Encounter`, `SystemsShutdown`.
5. Далее игрок продолжает полёт: новый `StartJump` с сохранённым маршрутом — сервер присылает уже `B != A` (нормально).

**Пример перехваченного прыжка (1 прыжок)** см. в логах 10.1.

---

### 4. Финальный прыжок по маршруту

1. После `StartJump` вместо `FSDTarget` приходит `NavRouteClear` — сигнал, что это последний прыжок. Логически `B = 0`.
2. Проверка: `A != 0` → всё штатно. Вывод: *"Ответ сервера: Финальный прыжок подтвержден"*.
3. После `FSDJump` — *"Выход из прыжка штатно"*.

**Пример финального прыжка** см. 10.3 (второй прыжок) и 10.2 (одиночный прыжок без перехвата).

---

### 5. Слепой прыжок (без маршрута)

1. `in_route = false`. При `StartJump` выводим: *"Слепой прыжок"*.
2. Таймер 60 с переводим в «спящий режим» — он не сбрасывается, но и не вызывает тревогу до `FSDJump`.
3. Никаких `FSDTarget` или `NavRouteClear` в течение прыжка не будет.
4. При `FSDJump` сравниваем `StartJump.SystemAddress` и `FSDJump.SystemAddress`:
   - Если равны → *"Выход из прыжка в {system} штатно"*.
   - Если не равны → *"ТРЕВОГА: Нас выдернули из прыжка в {current_system}"* (`dropped.ogg`).

**Пример слепого прыжка** см. в логах 10.4.

---

### 6. Логика сравнения (единая)

* **Для маршрутных прыжков** (кроме финального):  
  `if A == B then тревога else норма`
* **Для финального маршрутного прыжка**:  
  `if пришёл NavRouteClear → норма` (т.к. `B = 0`, `A != 0` всегда)
* **Для слепого прыжка**:  
  `if StartJump.SystemAddress == FSDJump.SystemAddress then норма else тревога`

---

### 7. Таймер и защита от лагов

* Запускается на `StartJump` (60 сек).
* Останавливается при:
  1. `FSDTarget` (любой)
  2. `NavRouteClear`
  3. `FSDJump`
* Если за 60 секунд ни одно событие не пришло — прыжок считается «зависшим» (игра выкинет в меню). Логика EWS сбрасывается и ждёт нового `StartJump`.

---

### 8. Обработка событий (примеры полей)

| Событие | Поля для логики | Примечание |
|---------|----------------|-------------|
| `StartJump` | `JumpType`, `StarSystem`, `SystemAddress` | Только `Hyperspace` |
| `FSDTarget` | `SystemAddress`, `RemainingJumpsInRoute` | Не приходит при финальном прыжке |
| `NavRouteClear` | нет доп. полей | Означает `B = 0` |
| `FSDJump` | `StarSystem`, `SystemAddress` | Фактическое прибытие |
| `Unknown_Encounter` | – | Отдельный модуль, не в EWS |

---

### 9. Переменные и состояние

* `in_route` — глобальная переменная, отслеживается по файлу `NavRoute.json` (событие `NavRoute` → `in_route = true`, `NavRouteClear` → `false`).
* `A`, `B` — хранятся внутри модуля EWS.
* Никаких общих фильтров (`time.sleep` на весь скрипт). Ограничения только локальные, например `and not GalaxyMap`.

---

### 10. Примеры логов из игры (реальные)

Приведены в исходном тексте инструкции (пункт 10). Они подтверждают все сценарии:

* **10.1** — перехваченный маршрутный прыжок (1 прыжок)
* **10.2** — обычный маршрутный прыжок (1 прыжок)
* **10.3** — обычный маршрутный прыжок (2 прыжка)
* **10.4** — слепой прыжок без перехвата

---

### 11. Рекомендации по реализации

* Модуль должен **сам отслеживать ротацию лог-файла** (если файл не меняется 20–30 секунд — переключаться на новый).
* Воспроизведение `.ogg` аудиофайлов:
  * `unstable.ogg` — при срабатывании тревоги в `FSDTarget` (равенство адресов).
  * `dropped.ogg` — при подтверждении перехвата в `FSDJump` (несовпадение систем).
* Мониторинг `NavRoute.json` по факту изменения (редко, но нужно).
* Вывод информации в интерфейс (текст + звук).

---

## 🇬🇧 English

### 1. Core Principles (supplement to first spec)

* Primary system identifier — **`SystemAddress`** (numeric). String comparison (`StarSystem`) is possible but less reliable.
* **Variables:**
  * **`A`** — `SystemAddress` from `StartJump` (target the player is jumping to).
  * **`B`** — `SystemAddress` from `FSDTarget` (server confirmation during jump) or `0` on `NavRouteClear`.
* **60-second timer** — network lag protection. Starts on `StartJump` (`JumpType: Hyperspace`). Reset on any relevant event (`FSDTarget`, `NavRouteClear`, `FSDJump`).
* **Route jump** — an active route exists (`in_route = true` from `NavRoute.json`). Server sends `FSDTarget` or `NavRouteClear` within ~7–10 seconds.
* **Blind jump** — no route. Server sends no `FSDTarget`/`NavRouteClear`. Interdiction detection only after `FSDJump`.

---

### 2. Normal Route Jump (multi-step)

1. **Before jump** — `in_route = true`. `NavRoute` + `FSDTarget` may exist.
2. `StartJump` → store `A = SystemAddress`. Start 60s timer. Output: *"Route jump"*.
3. After ~7 sec, `FSDTarget` arrives with `SystemAddress = B`.
   - If `A != B` → normal. Output: *"Server response: Route confirmed"*. Reset timer.
   - If `A == B` → **ALERT**: *"Space unstable, interdiction imminent"* (play `unstable.ogg`). Reset timer. In 4–5 sec, ship shaking animation.
4. Later `FSDJump`:
   - If alert triggered → output: *"Pulled out of hyperspace"* (`dropped.ogg`). Then `Unknown_Encounter`, `SystemsShutdown`.
   - If no alert → *"Jump exit normal"*.
5. Repeat with next `StartJump` and new `A`.

**Example**: see logs 10.3.

---

### 3. Interdicted Route Jump

1. Route active. `StartJump` with `A = target SystemAddress`.
2. After ~7 sec, `FSDTarget` arrives with **same** `SystemAddress` (`B == A`).  
   → Alert. Output: *"Space unstable, interdiction imminent"*.
3. After 4–5 sec, animation. Then `FSDJump` into a different system (or rarely same, but interdiction happened).
4. After exit — `Unknown_Encounter`, `SystemsShutdown`.
5. Player continues: next `StartJump` — server sends `B != A` (normal).

**Example**: see logs 10.1.

---

### 4. Final Route Jump

1. After `StartJump`, instead of `FSDTarget`, `NavRouteClear` arrives — last jump. Logical `B = 0`.
2. Check: `A != 0` → normal. Output: *"Server response: Final jump confirmed"*.
3. After `FSDJump` — *"Jump exit normal"*.

**Examples**: 10.3 (second jump) and 10.2 (single-jump route).

---

### 5. Blind Jump (no route)

1. `in_route = false`. On `StartJump` output: *"Blind jump"*.
2. 60s timer goes into "sleep mode" — does not reset, but triggers no alert until `FSDJump`.
3. No `FSDTarget` or `NavRouteClear` will arrive.
4. On `FSDJump`, compare `StartJump.SystemAddress` vs `FSDJump.SystemAddress`:
   - If equal → *"Jump exit into {system} normal"*.
   - If not equal → *"ALERT: Pulled out of hyperspace into {current_system}"* (`dropped.ogg`).

**Example**: see logs 10.4.

---

### 6. Comparison Logic (unified)

* **For route jumps (except final):**  
  `if A == B then alert else normal`
* **For final route jump:**  
  `if NavRouteClear arrives → normal` (since `B = 0`, `A != 0`)
* **For blind jump:**  
  `if StartJump.SystemAddress == FSDJump.SystemAddress then normal else alert`

---

### 7. Timer and Lag Protection

* Started on `StartJump` (60 sec).
* Stopped by:
  1. `FSDTarget` (any)
  2. `NavRouteClear`
  3. `FSDJump`
* If no event after 60 sec — jump considered "stuck" (game will drop to menu). EWS logic resets, waits for new `StartJump`.

---

### 8. Event Fields Summary

| Event | Relevant fields | Note |
|-------|----------------|------|
| `StartJump` | `JumpType`, `StarSystem`, `SystemAddress` | Only `Hyperspace` |
| `FSDTarget` | `SystemAddress`, `RemainingJumpsInRoute` | Not sent on final jump |
| `NavRouteClear` | none | Means `B = 0` |
| `FSDJump` | `StarSystem`, `SystemAddress` | Actual arrival |
| `Unknown_Encounter` | – | Separate module, not in EWS |

---

### 9. Variables and State

* `in_route` — global variable from `NavRoute.json` (`NavRoute` → `true`, `NavRouteClear` → `false`).
* `A`, `B` — internal EWS variables.
* No global filters (e.g. `time.sleep`). Module-local restrictions only (e.g. `and not GalaxyMap`).

---

### 10. Real Game Log Examples

Provided in original text (section 10). They confirm all scenarios:

* **10.1** — interdicted route jump (1 jump)
* **10.2** — normal route jump (1 jump)
* **10.3** — normal route jump (2 jumps)
* **10.4** — blind jump without interdiction

---

### 11. Implementation Notes

* The module must **detect log file rotation** (if file unchanged for 20–30 seconds, switch to new journal file).
* Play `.ogg` audio files:
  * `unstable.ogg` — when alert triggers on `FSDTarget` (addresses equal).
  * `dropped.ogg` — when interdiction confirmed on `FSDJump` (system mismatch).
* Monitor `NavRoute.json` for changes (rare, but required).
* Output information (text + sound) to the user interface.
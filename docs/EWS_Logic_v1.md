# 🛰️ Elite Dangerous: EWS (Early Warning System) Thargoid, Module Specification

This document contains the functional specifications and logical architecture for the EWS Module, designed to track hyperspace jumps and detect Thargoid Hyperdictions using game journal logs.

Based on requirements specified in `Old_instructions_logic_EWS.TXT`.

---

<details>
<summary><b>🇷🇺 Нажмите, чтобы открыть Техническое Задание на русском языке</b></summary>
<p></p>

## Техническое задание: Модуль EWS (Early Warning System)

### 1. Общее описание
Модуль **EWS** (комбинированный навигационно-тревожный модуль) предназначен для автоматического анализа состояния прыжков корабля через гиперпространство (Hyperspace) на основе логов Elite Dangerous. Главная цель модуля — на этапе разгона и прыжка заблаговременно определить, идет ли прыжок штатно или корабль подвергся **гипердикции (перехвату таргоидами)**, и выдать соответствующее предупреждение.

---

### 2. Ключевые переменные и триггеры
* **`A`** (внутренний регистр): Ожидаемое количество прыжков до целевой системы. Накапливает значение из маршрута.
* **`B`** (текущий ответ): Фактическое количество оставшихся прыжков, полученное из промежуточного ответа сервера (`RemainingJumpsInRoute`).
* **Таймер лага (60 сек)**: Защитный таймер. Максимальное время ожидания ответа сервера в промежутке между инициацией прыжка и выходом из него.

---

### 3. Алгоритмы и логические сценарии

#### Сценарий 1: Штатный многоэтапный маршрут
1. Обнаружена пара событий: `NavRoute` + `FSDTarget` $
ightarrow$ Инициализируем переменную: `A = RemainingJumpsInRoute`.
2. Событие `StartJump` (`"JumpType":"Hyperspace"`) $
ightarrow$ Включается **защитный таймер на 60 секунд**.
3. В течение первых ~7 секунд прыжка сервер присылает промежуточный `FSDTarget` с обновленным счетчиком `RemainingJumpsInRoute` (записываем в `B`).
4. **Математическое сравнение**:
   * Если **$B < A$** — сервер подтвердил успешный полет. Тревоги нет.
   * Защитный таймер на 60 секунд немедленно сбрасывается.
   * Значение обновляется для следующей итерации: `A = B`.
5. Событие `FSDJump` $
ightarrow$ Выход в систему, остывание FSD. Цикл повторяется для следующей системы.

#### Сценарий 2: Перехваченный прыжок (Гипердикция)
1. Маршрут построен, мы находимся в прыжке. Переменная `A` хранит текущий остаток (например, `A = 2`).
2. Событие `StartJump` $
ightarrow$ Запуск таймера на 60 секунд.
3. Через ~7 секунд приходит лог `FSDTarget`, но значение прыжков **НЕ** уменьшилось (**$B == A$**, то есть `B = 2`).
4. **Критерий тревоги**: Условие $B < A$ нарушено.
5. **Реакция системы**:
   * Защитный таймер 60 секунд сбрасывается.
   * Отправка строки в модуль озвучки: ` "пространство не стабильно, возможен перехват" `.
   * *(Через 4-5 секунд в игре физически начнется болтанка корабля)*.
6. Событие `FSDJump` $
ightarrow$ Переход к логике сравнения систем (см. Сценарий 4).
7. Модуль фиксирует выход из подпространства и выдает: ` "нас выдернули из прыжка" `.
8. Событие `MusicTrack":"Unknown_Encounter"` $
ightarrow$ Выдача строки: ` "обнаружена сигнатура Таргоидов" `.
9. Событие `SystemsShutdown` $
ightarrow$ Ожидание перезагрузки и включения питания. Конец цепочки перехвата.

#### Сценарий 3: Финальный прыжок маршрута (или маршрут из 1 прыжка)
1. Маршрут построен: `A = 1`.
2. Событие `StartJump` $
ightarrow$ Запуск таймера на 60 секунд.
3. Вместо промежуточного `FSDTarget` сервер присылает событие `NavRouteClear` (маршрут завершен/очищен).
4. Система интерпретирует `NavRouteClear` как виртуальный ноль (**$B = 0$**).
5. Проверка: $0 < 1$ (условие **$B < A$** выполнено). Тревоги нет.
6. Защитный таймер сбрасывается, значения обнуляются (`A = 0`, `B = 0`).
7. Событие `FSDJump` $
ightarrow$ Успешное прибытие в финальную точку.

#### Сценарий 4: "Слепой прыжок" (Без построения маршрута)
* **Условие**: Игрок выбрал звезду вручную (через левую панель или HUD). События `NavRoute` в логах не было. Прыжки `FSDTarget` или `NavRouteClear` в течение 7 секунд после старта не придут.
* **Логика**:
  1. При фиксации `StartJump` логика сравнения $B < A$ и таймер на 60 секунд принудительно переходят в **режим сна** до момента выхода.
  2. Вывод оповещения: ` "СРП отключен, летим в слепую" `.
  3. Используется строгий метод валидации по именам систем:
     $$	ext{Результат} = egin{cases} 	ext{Все ОК}, & 	ext{если } 	ext{StartJump(StarSystem)} == 	ext{FSDJump(StarSystem)} \ 	ext{Перехват}, & 	ext{если } 	ext{StartJump(StarSystem)} 
eq 	ext{FSDJump(StarSystem)} \end{cases}$$
  4. Если системы не совпали, по триггеру `FSDJump` выводится: ` "Нас выдернули из прыжка" `.

---

### 4. Сетевой предохранитель (Защита от лагов)
Таймер на 60 секунд — это верхний потолок ожидания ответа от серверов Frontier. Чтобы скрипт не зависал, таймер принудительно прерывается (интер interrupt) при получении любого из 4-х событий-ключей:
1. `FSDTarget` при условии $B < A$ (Штатный полет).
2. `FSDTarget` при условии $A == B$ (Аномалия/Перехват).
3. `NavRouteClear` (Конец маршрута).
4. `FSDJump` (Физический выход в систему).

*Примечание: Если за 60 секунд ни одного ответа не получено, система принудительно переводит прыжок в разряд "слепых" (Сценарий 4) для предотвращения поломки логики.*

---

### 5. Архитектурные правила для разработчика (Python)
1. **Строгая изоляция**: Модуль должен быть полностью автономным. Запрещено использовать глобальные фильтры (например, на уровне чтения логов) или вызывать `time.sleep()` для всего скрипта, блокирующий поток. Ограничения реализуются внутри кода модуля через логические ветвления.
2. **Фильтрация спама карты**: При планировании маршрутов на карте галактики генерируется лог `"MusicTrack":"GalaxyMap"`. Во время активности карты модуль должен игнорировать промежуточный шум логов и брать в обработку только **последнее актуальное значение** связки `NavRoute` + `FSDTarget`. Реализовать проверку условий типа `and not GalaxyMap` локально для смежных функций.
3. **Сохранение состояния цепочки**: При ротации (смене) или поиске нового лог-файла игры модуль обязан бесшовно сохранять цепочку маршрута. Для верификации и восстановления переменной `A` на стыке файлов рекомендуется считывать текущий статус навигации из файла `Status.json` (сверка флага навигации и оставшихся систем). Цепочка также не должна сбрасываться/ломаться после завершения гипердикции.
4. **Интеграция с TTS (Озвучка)**: Каждая фраза оповещения должна отправляться в звуковой движок в виде единой монолитной строки (`string`). Запрещено дробить фразу на отдельные слова, чтобы избежать заиканий и наложений звука.
5. **Синхронизация Unknown Encounter**: Оповещение об обнаружении сигнатуры Таргоидов (`Unknown_Encounter`) должно вызываться исключительно после математического подтверждения перехвата, чтобы голосовое уведомление идеально совпадало с началом игровой анимации сбоя.

</details>

---

<details>
<summary><b>🇬🇧 Click to expand Technical Specification in English</b></summary>
<p></p>

## Technical Specification: EWS (Early Warning System) Thargoid, Module

### 1. General Overview
The **EWS** module (a combined navigation and early warning subsystem) automatically processes and monitors hyperspace jump states based on Elite Dangerous journal logs. Its core utility is to distinguish between a standard high-wake jump and a **Thargoid Hyperdiction (interdiction)** during the initial frame shift tunnel sequence, allowing for immediate tactical voice/text alerts.

---

### 2. Primary Variables & Triggers
* **`A`** (internal register): The expected remaining jumps to the final destination, initialized from the route plan.
* **`B`** (current telemetry): The actual remaining jumps returned in mid-jump by the server response (`RemainingJumpsInRoute`).
* **Lag Protection Timer (60s)**: A watchdog timer tracking the maximum allowable delta between jump initiation and hyperspace exit to mitigate network latency issues.

---

### 3. Logic Scenarios & State Machine

#### Scenario 1: Nominal Multi-Jump Navigation
1. Catch sequence: `NavRoute` + `FSDTarget` $
ightarrow$ Set internal state: `A = RemainingJumpsInRoute`.
2. Event `StartJump` (`"JumpType":"Hyperspace"`) $
ightarrow$ Fires up the **60-second watchdog timer**.
3. Within the first ~7 seconds, the transaction server responds with an intermediate `FSDTarget` log containing the current `RemainingJumpsInRoute` (mapped to `B`).
4. **Mathematical Validation**:
   * If **$B < A$** $
ightarrow$ Server confirms a valid progression. No threat detected.
   * The 60-second watchdog timer is instantly killed.
   * Shift register state: `A = B`.
5. Event `FSDJump` $
ightarrow$ Drop into system, initiate FSD cooldown, await next cycle.

#### Scenario 2: Hyperdicted Jump (Thargoid Ambush)
1. Route active, ship inside the hyperspace tunnel. Current jump budget tracked (e.g., `A = 2`).
2. Event `StartJump` $
ightarrow$ 60-second watchdog timer starts.
3. Within ~7 seconds, an intermediate `FSDTarget` log arrives, but the remaining jumps count remains stagnant (**$B == A$**, e.g., `B = 2`).
4. **Alarm Trigger**: The condition $B < A$ evaluates to **FALSE**.
5. **System Execution**:
   * Kill the 60-second watchdog timer.
   * Pipe string to voice engine: ` "space is unstable, possible interdiction detected" `.
   * *(Note: In-game cockpit severe shaking animation commences 4-5 seconds later)*.
6. Event `FSDJump` $
ightarrow$ Triggers cross-system validation logic (see Scenario 4).
7. Module detects drop out of hyperspace and broadcasts: ` "pulled out of hyperspace" `.
8. Event `MusicTrack":"Unknown_Encounter"` $
ightarrow$ Broadcasts: ` "thargoid signature detected" `.
9. Event `SystemsShutdown` $
ightarrow$ Monitor power loss. End of hyperdiction pipeline.

#### Scenario 3: Final Route Jump (or Single-Jump Path)
1. Route tracking initialized: `A = 1`.
2. Event `StartJump` $
ightarrow$ Watchdog timer initialized.
3. Instead of a mid-jump `FSDTarget`, the engine receives a `NavRouteClear` log (route finished/aborted by game context).
4. The system evaluates `NavRouteClear` as a virtual zero (**$B = 0$**).
5. Validation: $0 < 1$ (the condition **$B < A$** is satisfied). Safe state verified.
6. The watchdog timer clears; states reset (`A = 0`, `B = 0`).
7. Event `FSDJump` $
ightarrow$ Successful arrival at the designated terminus.

#### Scenario 4: "Blind Jump" (Direct Target Selection)
* **Condition**: The pilot manually targets a star system via the Left Panel or HUD. No `NavRoute` sequence exists in the log pipeline. No mid-jump `FSDTarget` or `NavRouteClear` will occur within the 7-second frame window.
* **Logic Execution**:
  1. Once `StartJump` hits, the $B < A$ validation routine and the 60s timer are set to **sleep mode** until hyperspace exit.
  2. Send alert string: ` "route tracker offline, flying blind" `.
  3. Engage strict name verification matrix:
     $$	ext{State} = egin{cases} 	ext{Nominal Drop}, & 	ext{if } 	ext{StartJump(StarSystem)} == 	ext{FSDJump(StarSystem)} \ 	ext{Interdicted Drop}, & 	ext{if } 	ext{StartJump(StarSystem)} 
eq 	ext{FSDJump(StarSystem)} \end{cases}$$
  4. If system names do not correlate, on `FSDJump` fire: ` "pulled out of hyperspace" `.

---

### 4. Network Fuse (Lag Safeguard)
The 60-second watchdog timer acts as a definitive limit for Frontier server response times. To prevent the module from getting stuck in an infinite polling loop, the timer is immediately interrupted upon detecting any of these 4 hardware keys:
1. `FSDTarget` while $B < A$ (Nominal Flight).
2. `FSDTarget` while $A == B$ (Anomaly/Hyperdiction).
3. `NavRouteClear` (Route Terminated).
4. `FSDJump` (Physical Drop).

*Note: If a 60-second timeout occurs without a single network key, the system forcefully drops the logic state into a "Blind Jump" routine (Scenario 4) to prevent core system lockup.*

---

### 5. Architectural & Python Development Rules
1. **Asynchronous Isolation**: The EWS module must operate completely autonomously. Global journal stream overrides or hard `time.sleep()` calls that halt the main execution stream are strictly prohibited. Threading or async tasks must handle limitations internally via localized conditional structures.
2. **Galaxy Map De-noising**: Opening the galaxy map triggers heavy log activity under the `"MusicTrack":"GalaxyMap"` key. The module must drop/ignore this intermediate transactional noise and parse only the **final, trailing occurrence** of the `NavRoute` + `FSDTarget` pairing. Use localized exclusions like `and not GalaxyMap` inside competing processing tasks.
3. **State & Chain Persistence**: During log file rotation or when hunting down a newly spawned journal file, the module must retain its active route index. To reconcile and restore the `A` variable seamlessly, cross-verify the navigation state flags within `Status.json`. The chain must remain completely unbroken across files and must gracefully recover post-hyperdiction.
4. **TTS (Text-to-Speech) Engineering**: Every voice alert must be compiled and sent to the audio wrapper as a **single monolithic string**. Do not pass split words or collections to prevent asynchronous stuttering or overlap audio glitches.
5. **Unknown Encounter Syncing**: The `Unknown_Encounter` signature flag must only alert *after* mathematical confirmation of a failed jump matrix, keeping the audio sequence flawlessly synchronized with the visual cockpit blackout and asset rendering.

</details>


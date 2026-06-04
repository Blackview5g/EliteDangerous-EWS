# Elite Dangerous — Early Warning System (EWS)

Early detection of Thargoid hyperdictions during hyperspace jumps.

## Features
- Detects hyperdictions before visual shaking starts.
- Works with plotted routes (SRS) and blind jumps.
- Uses `SystemAddress` comparison for reliability.
- 60-second network lag protection.

# EliteDangerous-EWS (Early Warning System)

[RU] Модуль раннего предупреждения о перехвате в гиперпространстве (Hyperdiction) для игры Elite Dangerous.
[EN] Early Warning System module for hyperspace interdictions (Hyperdiction) in Elite Dangerous.

---

## 🇷🇺 Описание проекта (Russian)

**EliteDangerous-EWS** — это прототип программного модуля на Python, который анализирует журнал (Journal) игры Elite Dangerous в реальном времени. Его главная цель — предупредить пилота о нестабильности гиперпространства и возможном перехвате Таргоидами (Hyperdiction) до того, как начнется визуальная анимация в игре.

### ⚙️ Как это работает (Логика EWS)

Модуль сравнивает количество оставшихся прыжков по построенному маршруту до старта прыжка (переменная `A`) и во время нахождения в гиперпространстве (переменная `B`), параллельно контролируя 60-секундный таймер безопасности.

1. **Штатный полет:**
   * Строится маршрут: событие `NavRoute` + `FSDTarget` (запоминаем `A = RemainingJumpsInRoute`).
   * Запуск FSD: событие `StartJump` (включается таймер на 60 секунд).
   * В гиперпространстве приходит ответ от сервера: новое событие `FSDTarget` с `B = RemainingJumpsInRoute`.
   * **Проверка:** Если `B < A`, всё в порядке. Таймер сбрасывается, значение обновляется (`A = B`). Пилот летит дальше.
   * На финальном прыжке событие `NavRouteClear` означает завершение маршрута (`B = 0`).

2. **Сценарий перехвата (Hyperdiction):**
   * Пилот прыгает, имея `A = 2` оставшихся прыжка. Запускается таймер 60 секунд.
   * В гиперпространстве сервер возвращает данные: `B = 2` (количество прыжков не уменьшилось).
   * **Проверка:** Условие `B < A` нарушено. **EWS мгновенно объявляет ТРЕВОГУ!**
   * Выводится предупреждение: *«Пространство нестабильно, возможен перехват»*.
   * Через 4–5 секунд в игре начинается визуальная болтанка корабля, подтверждающая прогноз EWS.
   * После выброса из гиперпространства фиксируются события `Unknown_Encounter` (сигнатура Таргоидов) и `SystemsShutdown` (отключение питания).

---

## en Project Description (English)

**EliteDangerous-EWS** is a prototype software module written in Python that analyzes the Elite Dangerous Journal log files in real-time. Its primary goal is to warn the pilot about hyperspace instability and imminent Thargoid Hyperdiction before the in-game visual effects begin.

### ⚙️ How It Works (EWS Logic)

The module compares the number of remaining jumps in the pre-calculated route before the jump starts (variable `A`) with the update received while inside hyperspace (variable `B`), while simultaneously monitoring a 60-second safety timer.

1. **Normal Flight:**
   * Route plotted: `NavRoute` + `FSDTarget` events (we store `A = RemainingJumpsInRoute`).
   * FSD charging/jump: `StartJump` event (starts a 60-second countdown timer).
   * Inside hyperspace, the server responds: a new `FSDTarget` event arrives with `B = RemainingJumpsInRoute`.
   * **Check:** If `B < A`, everything is normal. The timer resets, the value updates (`A = B`). The pilot proceeds safely.
   * On the final jump, the `NavRouteClear` event indicates the end of the route (`B = 0`).

2. **Interception Scenario (Hyperdiction):**
   * The pilot jumps with `A = 2` remaining jumps. The 60-second safety timer starts.
   * While in hyperspace, the server sends an update: `B = 2` (the jump count did not decrease).
   * **Check:** The condition `B < A` fails. **EWS instantly triggers an ALARM!**
   * Output message: *“Space is unstable, hyperdiction imminent”*.
   * 4–5 seconds later, the in-game ship shaking animation begins, confirming the EWS prediction.
   * After being pulled out of hyperspace, the module logs `Unknown_Encounter` (Thargoid signature detected) and `SystemsShutdown` events.

---

## 📂 Структура репозитория / Repository Structure

* `src/ews_module.py` — Основной исполняемый код логики на Python / Main Python logic script.
* `docs/` — Подробное описание версий логики (v1 и v2 based on SystemAddress) / Detailed logic documentation.
* `examples/journal_examples.json` — Примеры игровых логов для тестирования / Sample journal logs for testing.


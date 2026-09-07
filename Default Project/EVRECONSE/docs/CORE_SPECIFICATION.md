# EVRECONSE Core Specification v1.0

**Project:** EVRECONSE
**Status:** Draft v1.0
**Date:** 2026-07-25
**Owner:** Евгений Атаман

---

## 1. Purpose

EVRECONSE — исследовательская система обнаружения высоковероятных разворотных ситуаций на криптовалютном рынке.

Система не открывает сделки и не управляет капиталом. Она:

* получает рыночные данные;
* обнаруживает рыночные события;
* оценивает их качество;
* сохраняет результаты;
* отправляет уведомления пользователю.

---

## 2. Scope of MVP (Stage Alpha)

### Included

* Bybit USDT Perpetual
* Таймфрейм 15 минут (M15)
* Стратегия LW-001 (Long Lower Wick)
* Получение свечей и ликвидаций через официальный Bybit WebSocket API
* Оценка сигнала (Scoring)
* Telegram-уведомления
* Сохранение всех обнаруженных событий в локальную базу данных
* Автоматическая проверка исхода сигнала (TP/SL)

### Excluded

* Автоматическая торговля
* Поддержка нескольких бирж
* Веб-интерфейс
* Machine Learning
* Дополнительные фильтры (OI, Funding, Delta и др.)

---

## 3. Target Market

* Биржа: **Bybit**
* Инструменты: **USDT Perpetual**
* Монеты: **рыночная капитализация с 21-й по 250-ю позицию**
* Список обновляется автоматически **1 раз в сутки**.

---

## 4. Timeframe

* Анализ выполняется **после закрытия каждой M15 свечи**.
* Используются **только закрытые свечи**.

---

## 5. Event Model

### 5.1 Market Event

Любая закрытая M15 свеча, для которой вычислены все необходимые метрики.

### 5.2 Qualified Event

Market Event, удовлетворяющий минимальным условиям стратегии LW-001.

### 5.3 Signal

Qualified Event, у которого **Confidence Score ? Signal Threshold**.

### 5.4 Outcome

Результат сигнала после проверки TP/SL.

---

## 6. Strategy LW-001 (Summary)

Сигнал формируется при наличии:

1. Длинной нижней тени.
2. Аномально высоких лонг-ликвидаций.
3. Достаточного итогового Score.

Подробные формулы описываются в `docs/STRATEGIES/LW-001.md`.

---

## 7. Risk Parameters

* **Take Profit:** +3%
* **Stop Loss:** ?3%

TP/SL используются **только для оценки эффективности стратегии**, а не для автоматического открытия сделок.

---

## 8. Notification

Канал уведомлений: **Telegram**.

Каждое уведомление должно содержать:

* Symbol
* Exchange
* Timeframe
* Close Price
* Lower Wick %
* Body %
* Wick/Body Ratio
* Liquidation Volume
* Liquidation Reference Value
* Confidence Score
* Event Time (UTC)
* Event ID

---

## 9. Data Persistence

Сохраняются:

* **Все Market Events** (даже с низким Score).
* Все Signals.
* Все Outcomes.

Это позволяет пересчитывать статистику при изменении параметров стратегии.

---

## 10. Core Principles

1. **Documentation First**
2. **Architecture First**
3. **Data First**
4. **Scientific Validation**
5. **Everything Configurable**
6. **No Magic Numbers**
7. **Reliability Before Features**
8. **Explainability**
9. **Evolution Without Rewrite**

---

## 11. Success Criteria

MVP считается успешным, если:

1. Система непрерывно работает не менее 7 суток.
2. Не пропускает ни одной M15 свечи по отслеживаемым инструментам.
3. Отправляет Telegram-уведомление не позднее **10 секунд** после закрытия свечи.
4. Сохраняет 100% Market Events и Signals.
5. Автоматически рассчитывает Outcome для каждого Signal.

---

## 12. Versioning

Изменения этого документа фиксируются в `docs/CHANGELOG.md` и `docs/DECISION_LOG.md`.
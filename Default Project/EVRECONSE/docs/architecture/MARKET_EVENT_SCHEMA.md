# MARKET_EVENT_SCHEMA.md

# EVRECONSE Market Event Schema

**Document Version:** 1.0
**Status:** Draft
**Date:** 2026-07-25

---

## 1. Назначение Market Event

Market Event — единый объект данных, который проходит через все модули системы от создания до завершения. Он объединяет рыночные данные, результаты анализа стратегии, оценку качества, статус уведомления и результат отслеживания.

Событие создаётся при закрытии каждой M15 свечи и существует до тех пор, пока не будет завершён Outcome Tracker или пока событие не будет признано устаревшим.

**Принципы схемы:**

- единая структура для всех этапов жизненного цикла;
- поля добавляются поэтапно, но удаление невозможно;
- схема не привязана к конкретной бирже, API или языку программирования;
- обратная совместимость при добавлении новых полей.

---

## 2. Полный перечень полей

### 2.1 Metadata

| Поле | Описание | Тип | Обязательное | Заполняется | Изменяется |
|------|----------|-----|--------------|-------------|------------|
| Event ID | Уникальный идентификатор события | String | Да | Strategy Engine | Нет (Immutable) |
| Status | Текущий статус жизненного цикла | String | Да | Strategy Engine | Да, по цепочке модулей |
| Version | Версия схемы события | Number | Да | Strategy Engine | Нет (Immutable) |
| Created At | Время создания события | DateTime | Да | Strategy Engine | Нет (Immutable) |
| Updated At | Время последнего изменения | DateTime | Да | Модуль, изменивший статус | Да, при каждом изменении |

### 2.2 Market Data

Поля, заполняемые при создании события на основе рыночных данных.

| Поле | Описание | Тип | Обязательное | Заполняется | Изменяется |
|------|----------|-----|--------------|-------------|------------|
| Symbol | Тикер инструмента (например, BTCUSDT) | String | Да | Strategy Engine | Нет (Immutable) |
| Exchange | Название биржи (например, Bybit) | String | Да | Strategy Engine | Нет (Immutable) |
| Timeframe | Таймфрейм свечи (например, M15) | String | Да | Strategy Engine | Нет (Immutable) |
| Event Time | Время закрытия свечи (UTC) | DateTime | Да | Strategy Engine | Нет (Immutable) |
| Open | Цена открытия свечи | Number | Да | Strategy Engine | Нет (Immutable) |
| High | Максимальная цена свечи | Number | Да | Strategy Engine | Нет (Immutable) |
| Low | Минимальная цена свечи | Number | Да | Strategy Engine | Нет (Immutable) |
| Close | Цена закрытия свечи | Number | Да | Strategy Engine | Нет (Immutable) |
| Volume | Объём торгов за свечу | Number | Да | Strategy Engine | Нет (Immutable) |

### 2.3 Strategy Data

Поля, заполняемые Strategy Engine после подтверждения паттерна.

| Поле | Описание | Тип | Обязательное | Заполняется | Изменяется |
|------|----------|-----|--------------|-------------|------------|
| Strategy ID | Идентификатор стратегии, подтвердившей паттерн | String | Нет (только для Qualified Event) | Strategy Engine | Нет (Immutable) |
| Lower Wick | Размер нижней тени в пунктах | Number | Нет | Strategy Engine | Нет (Immutable) |
| Body | Размер тела свечи в пунктах | Number | Нет | Strategy Engine | Нет (Immutable) |
| Wick/Body Ratio | Отношение нижней тени к телу | Number | Нет | Strategy Engine | Нет (Immutable) |
| Lower Wick % | Процент нижней тени от всей свечи | Number | Нет | Strategy Engine | Нет (Immutable) |
| Body % | Процент тела от всей свечи | Number | Нет | Strategy Engine | Нет (Immutable) |
| Liquidation Volume | Объём ликвидаций на момент закрытия свечи | Number | Нет | Strategy Engine | Нет (Immutable) |
| Liquidation Reference Value | Референтное значение ликвидаций (среднее за N свечей) | Number | Нет | Strategy Engine | Нет (Immutable) |

### 2.4 Score Data

Поля, заполняемые Scoring Engine.

| Поле | Описание | Тип | Обязательное | Заполняется | Изменяется |
|------|----------|-----|--------------|-------------|------------|
| Confidence Score | Итоговая оценка качества (0–100) | Number | Нет (только для Scored Event) | Scoring Engine | Нет (Immutable) |
| Score Breakdown | Детализация оценки по каждому параметру | Array | Нет | Scoring Engine | Нет (Immutable) |

Score Breakdown содержит элементы с полями:

| Поле | Описание | Тип |
|------|----------|-----|
| Parameter Name | Название параметра (Lower Wick Quality, Liquidation Strength, Candle Confirmation) | String |
| Parameter Score | Оценка параметра | Number |
| Penalty | Штраф (если применимо) | Number |

### 2.5 Notification Data

Поля, заполняемые Notification Service.

| Поле | Описание | Тип | Обязательное | Заполняется | Изменяется |
|------|----------|-----|--------------|-------------|------------|
| Notification Timestamp | Время отправки уведомления (UTC) | DateTime | Нет (только для Signal) | Notification Service | Нет (Immutable) |

### 2.6 Outcome Data

Поля, заполняемые Outcome Tracker.

| Поле | Описание | Тип | Обязательное | Заполняется | Изменяется |
|------|----------|-----|--------------|-------------|------------|
| Outcome | Результат сделки | String | Нет (только для Completed) | Outcome Tracker | Нет (Immutable) |
| Actual Profit % | Фактический профит или убыток в процентах | Number | Нет | Outcome Tracker | Нет (Immutable) |
| Outcome Timestamp | Время завершения отслеживания (UTC) | DateTime | Нет | Outcome Tracker | Нет (Immutable) |

Допустимые значения Outcome: TP, SL.

---

## 3. Таблица всех полей (сводная)

| Группа | Поле | Тип | Обязательное | Источник | Immutable |
|--------|------|-----|--------------|----------|-----------|
| Metadata | Event ID | String | Да | Strategy Engine | Да |
| Metadata | Status | String | Да | Strategy Engine | Нет |
| Metadata | Version | Number | Да | Strategy Engine | Да |
| Metadata | Created At | DateTime | Да | Strategy Engine | Да |
| Metadata | Updated At | DateTime | Да | Любой модуль | Нет |
| Market Data | Symbol | String | Да | Strategy Engine | Да |
| Market Data | Exchange | String | Да | Strategy Engine | Да |
| Market Data | Timeframe | String | Да | Strategy Engine | Да |
| Market Data | Event Time | DateTime | Да | Strategy Engine | Да |
| Market Data | Open | Number | Да | Strategy Engine | Да |
| Market Data | High | Number | Да | Strategy Engine | Да |
| Market Data | Low | Number | Да | Strategy Engine | Да |
| Market Data | Close | Number | Да | Strategy Engine | Да |
| Market Data | Volume | Number | Да | Strategy Engine | Да |
| Strategy Data | Strategy ID | String | Условно | Strategy Engine | Да |
| Strategy Data | Lower Wick | Number | Условно | Strategy Engine | Да |
| Strategy Data | Body | Number | Условно | Strategy Engine | Да |
| Strategy Data | Wick/Body Ratio | Number | Условно | Strategy Engine | Да |
| Strategy Data | Lower Wick % | Number | Условно | Strategy Engine | Да |
| Strategy Data | Body % | Number | Условно | Strategy Engine | Да |
| Strategy Data | Liquidation Volume | Number | Условно | Strategy Engine | Да |
| Strategy Data | Liquidation Reference Value | Number | Условно | Strategy Engine | Да |
| Score Data | Confidence Score | Number | Условно | Scoring Engine | Да |
| Score Data | Score Breakdown | Array | Условно | Scoring Engine | Да |
| Notification Data | Notification Timestamp | DateTime | Условно | Notification Service | Да |
| Outcome Data | Outcome | String | Условно | Outcome Tracker | Да |
| Outcome Data | Actual Profit % | Number | Условно | Outcome Tracker | Да |
| Outcome Data | Outcome Timestamp | DateTime | Условно | Outcome Tracker | Да |

*Условно — поле заполняется только при достижении соответствующего статуса.*

---

## 4. Группы полей

### 4.1 Metadata

Служебные поля, обеспечивающие идентификацию и отслеживание изменений события.

Характеристики:
- заполняются при создании события;
- только Status и Updated At изменяются в течение жизни события;
- Event ID уникален в пределах всей системы.

### 4.2 Market Data

Рыночные данные, полученные от Data Provider.

Характеристики:
- заполняются при создании события;
- не изменяются после создания;
- соответствуют одной закрытой M15 свече;
- объём торгов и цены являются исходными данными для всех последующих расчётов.

### 4.3 Strategy Data

Метрики паттерна, рассчитанные стратегией.

Характеристики:
- заполняются только если стратегия подтвердила паттерн;
- если ни одна стратегия не подтвердила — группа остаётся пустой;
- содержат как сырые значения (Lower Wick в пунктах), так и относительные (Lower Wick %);
- все поля группы immutable после заполнения.

### 4.4 Score Data

Результаты оценки Scoring Engine.

Характеристики:
- заполняются только для Qualified Event;
- Confidence Score — единственное число от 0 до 100;
- Score Breakdown — массив объектов с детализацией;
- Explainability обеспечивается наличием Breakdown.

### 4.5 Notification Data

Данные об отправке уведомления.

Характеристики:
- заполняются только для события в статусе SIGNAL;
- содержат только метку времени отправки.

### 4.6 Outcome Data

Результат отслеживания сделки.

Характеристики:
- заполняются только после завершения мониторинга;
- Outcome фиксирует, что именно сработало: TP или SL;
- Actual Profit % отражает реальный результат.

---

## 5. Жизненный цикл заполнения полей

Поля заполняются последовательно по мере прохождения события через модули системы.

```
Создание                          → Metadata (Event ID, Status=NEW, Version, Created At, Updated At)
                                  → Market Data (Symbol, Exchange, Timeframe, Event Time, OHLC, Volume)

Проверка стратегией               → Status → QUALIFIED
                                  → Strategy Data (Strategy ID, Lower Wick, Body, Ratio, %, Liquidation)

Оценка Scoring Engine             → Status → SCORED
                                  → Score Data (Confidence Score, Score Breakdown)

Принятие решения                  → Status → SIGNAL или DISMISSED
(Notification Service)              → Notification Data (Notification Timestamp) [только SIGNAL]

Отслеживание Outcome Tracker      → Status → MONITORING → COMPLETED
                                  → Outcome Data (Outcome, Actual Profit %, Outcome Timestamp)
```

После каждого шага поле Updated At обновляется текущим модулем.

---

## 6. Immutable поля

Следующие поля не могут быть изменены после установки значения:

**Всегда immutable:**

- Event ID
- Version
- Created At
- Symbol
- Exchange
- Timeframe
- Event Time
- Open, High, Low, Close
- Volume

**Immutable после заполнения:**

- Strategy ID
- Lower Wick, Body, Wick/Body Ratio, Lower Wick %, Body %
- Liquidation Volume, Liquidation Reference Value
- Confidence Score, Score Breakdown
- Notification Timestamp
- Outcome, Actual Profit %, Outcome Timestamp

**Mutable:**

- Status (изменяется по цепочке: NEW → QUALIFIED → SCORED → SIGNAL → MONITORING → COMPLETED или DISMISSED)
- Updated At (обновляется при каждом изменении статуса)

Правило: если поле установлено в ненулевое/непустое значение, оно больше не может быть изменено. Исключение — Status и Updated At.

---

## 7. Версионирование схемы

### Принцип

Схема события версионируется независимо от версии проекта. Номер версии указывается в поле Version при создании события.

### Правила

| Изменение | Мажорная версия | Минорная версия |
|-----------|-----------------|-----------------|
| Добавление нового необязательного поля | — | +1 |
| Добавление нового обязательного поля | +1 | 0 |
| Удаление поля | +1 | 0 |
| Изменение типа поля | +1 | 0 |
| Изменение имени поля | +1 | 0 |
| Изменение правил заполнения поля | 0 | +1 |

### Обратная совместимость

- Все модули должны поддерживать текущую мажорную версию схемы.
- Добавление нового необязательного поля (минорное изменение) не должно ломать существующие модули.
- Модуль, получивший событие с неизвестным полем, должен игнорировать это поле.
- Модуль, получивший событие без ожидаемого поля, должен работать с учётом его отсутствия.

### Текущая версия

1.0 — MVP Foundation.

---

## 8. Допустимые будущие расширения схемы

### 8.1 Расширение Market Data

| Поле | Описание | Источник |
|------|----------|----------|
| Open Interest | Открытый интерес на момент закрытия свечи | Будущие параметры |
| Funding Rate | Ставка фондирования | Будущие параметры |
| Delta | Кумулятивная дельта | Будущие параметры |
| CVD | Cumulative Volume Delta | Будущие параметры |
| ATR | Средний истинный диапазон | Будущие параметры |
| Spread | Спред между ценой покупки и продажи | Будущие параметры |
| Volatility | Волатильность инструмента | Будущие параметры |
| BTC Correlation | Корреляция с биткоином | Будущие параметры |

### 8.2 Расширение Strategy Data

| Поле | Описание |
|------|----------|
| Multi-Strategy Support | Массив Strategy ID для событий, прошедших несколько стратегий |
| Parent Event ID | Ссылка на родительское событие (для каскадных событий) |
| Priority | Приоритет события (для обработки вне очереди) |

### 8.3 Расширение Score Data

| Поле | Описание |
|------|----------|
| ML Score | Оценка от ML Evaluator |
| Weighted Score | Взвешенная оценка с учётом весов параметров |

### 8.4 Расширение Notification Data

| Поле | Описание |
|------|----------|
| Channels | Массив каналов, в которые отправлено уведомление (Telegram, Email, Web) |
| Delivery Status | Статус доставки по каждому каналу |

### 8.5 Расширение Outcome Data

| Поле | Описание |
|------|----------|
| Entry Price | Цена входа (если добавится исполнение) |
| Exit Price | Цена выхода |
| Duration | Длительность сделки |
| Risk/Reward Ratio | Отношение риска к прибыли |

### 8.6 Расширение Metadata

| Поле | Описание |
|------|----------|
| Tags | Метки для фильтрации и группировки событий |
| Batch ID | Идентификатор пакета при пакетной обработке |
| Retry Count | Количество попыток обработки при сбоях |
| Error Log | Лог ошибок при обработке события |

# EVRECONSE — стратегия Capitulation / Absorption

**Статус:** ACTIVE / SHADOW MODE
**Дата описания:** 2026-10-22 (завершено 2026-10-23)
**Production entry point:**
`/home/evreconse/realtime_capitulation_monitor_fixed.py`
**Проверенный GitHub HEAD на начало описания:**
`fc131d7018da1e07031090ab7894e93b1a0875c1`
**Коммит синхронизации кода:**
`c6d00fa9623b83234c1674b8bf9bbbfe96500d96`

Документ описывает **фактический active path**. LW-001 присутствует в
репозитории, но не является работающей стратегией; его описание вынесено в
`LW001_PRODUCTION_SPEC.md`.

---

## 1. Назначение

Capitulation / Absorption ищет LONG-кандидатов на рынке BingX USDT Perpetual
на 15-минутном таймфрейме. Идея паттерна:

1. Цена делает резкое движение вниз от open к low (capitulation).
2. Объём свечи аномально высок относительно предыдущих 30 закрытых свечей.
3. Нижняя тень существенна относительно тела свечи (absorption).
4. Цена возвращается от low к close (reclaim).

Все условия должны выполняться одновременно. Это **не** mean-reversion
stratегия с отдельным score и **не** LW-001.

Режим — shadow: реальные ордера не отправляются. `AUTO_TRADER_AVAILABLE =
False`; в active monitor нет вызова торгового API. Уведомления идут в Telegram.

---

## 2. Простое объяснение

Свеча считается кандидатом, если одновременно:

- она **красная**: `close < open`;
- от open до low цена упала **не меньше чем на 5%**;
- объём свечи **не меньше чем в 2 раза** больше медианы объёмов предыдущих
  30 закрытых 15-минутных свечей;
- нижняя тень **не меньше тела** свечи;
- цена закрылась **не ниже 30%** диапазона свечи от low (то есть reclaim от
  low не меньше 30%).

Если хотя бы одно условие не выполнено, сигнала нет. Отдельного минимального
score нет.

---

## 3. Где это запускается

```text
systemd: evreconse.service
  ExecStart=/usr/bin/python3 /home/evreconse/realtime_capitulation_monitor_fixed.py
  WorkingDirectory=/home/evreconse
  User=evreconse
```

`main()`:

1. Импортирует `get_universe_provider()`.
2. Вызывает `await universe_provider.initialize()`.
3. Запускает `monitor_symbols(universe_provider)`.

`monitor_symbols()`:

1. Создаёт `BingXFetcher` (shared, с rate limiter).
2. Вызывает `retry_pending_signals()` — только перечисляет pending, не
   переотправляет.
3. В бесконечном цикле:
   - получает universe;
   - создаёт `CycleStats`;
   - параллельно проверяет символы с `asyncio.Semaphore(10)`;
   - для найденных сигналов делает SQLite claim;
   - отправляет Telegram;
   - обновляет статус;
   - спит до следующей закрытой M15 + 60 секунд.

Цикл обычно стартует около `:01/:16/:31/:46` UTC.

---

## 4. Источник данных и universe

### 4.1. BingX klines

Используется `BingXFetcher.get_klines()`:

```python
candles = await fetcher.get_klines(
    symbol=symbol,
    interval="15m",
    start_time=int((now - 4h).timestamp() * 1000),
    end_time=int(now.timestamp() * 1000),
)
```

Фактическая семантика:

- `limit` по умолчанию **500**;
- в запрос передаётся `limit=500` и `endTime`;
- `startTime` **не передаётся** в API при таком limit и не фильтрует результат;
- ответ BingX разворачивается через `reversed()`;
- возвращается до **500** последних M15-свечей (примерно 5 суток), а не строго
  4 часа;
- явной сортировки по timestamp нет; предполагается порядок ответа API.

Для требования 32 свечей этого достаточно, но документация не должна называть
окно строго четырёхчасовым.

`BingXFetcher.__init__` требует `EVRECONSE_EXCHANGE_API_KEY` и
`EVRECONSE_EXCHANGE_API_SECRET` даже для публичных klines. На сервере они
берутся из `.env` через `load_dotenv()`. В GitHub секретов нет; есть
`.env.example`.

### 4.2. Universe

`UniverseProvider.get_universe()`:

- читает active snapshot из `data/cmc_universe.db`;
- если active snapshot отсутствует — пытается `last_good_universe.json`;
- если нет и fallback — возвращает пустой список;
- **не проверяет возраст/expiry active snapshot** перед выдачей.

`initialize()` не делает немедленный refresh. Фоновый `_auto_refresh_loop`
сначала спит `refresh_interval_hours` (24h), затем вызывает `refresh()`.

Фильтры при refresh:

- только `-USDT` perpetual;
- только trading status;
- исключение stablecoin, wrapped, leveraged, synthetic;
- без TOP-500 ограничения.

На проверенном сервере active snapshot: `id=5`, 574 символа,
`fetched_at=2026-10-08T09:25:51Z`. Он stale. Причина — не код GitHub, а права:
`data/cmc_universe.db` принадлежит `root:root` с режимом `0644`, процесс
`evreconse` не может писать; journal фиксирует
`attempt to write a readonly database`. Это эксплуатационный риск, описанный в
`PROJECT_VERSION_COMPARISON.md`.

---

## 5. Выбор свечи

`get_last_completed_candle(candles)`:

- если `candles` пуст или `< 2` — `(None, None)`;
- идёт с конца массива;
- пропускает `timestamp <= 0`;
- считает свечу закрытой, если
  `timestamp + 15 * 60 * 1000 <= now_ms`;
- возвращает первую подходящую с конца и её индекс.

Текущая незакрытая свеча не используется. Если в массиве есть более поздняя
незакрытая свеча, она будет пропущена, и будет взята предыдущая закрытая.

После выбора:

- `timestamp <= 0` → `invalid_timestamp`;
- `(symbol, timestamp)` уже в памяти → `already_processed`;
- `candle_index < 31` → `insufficient_history` (нужно минимум 32 свечи
  включая оцениваемую);
- предыдущие 30 объёмов: `candles[candle_index - 30 : candle_index]`.

---

## 6. Формулы

Все цены приводятся к `float`. `open` — знаменатель процентных метрик.

```python
candle_range    = high - low
range_pct       = candle_range / open * 100
open_to_low_pct = (low - open) / open * 100
body            = abs(close - open)
body_pct        = body / open * 100
lower_wick      = min(open, close) - low
lw_body_ratio   = lower_wick / body                 # 0.0 при body == 0
lw_range_pct    = lower_wick / candle_range * 100   # 0.0 при range <= 0
reclaim_pct     = (close - low) / candle_range * 100  # 0.0 при range <= 0
is_red          = close < open

median30        = median(previous 30 completed M15 volumes)
volume_30_ratio = volume / median30                 # 0.0 при median30 <= 0
```

Единицы:

| Метрика | Единица |
|---|---|
| `range_pct` | % |
| `open_to_low_pct` | % (отрицательное значение) |
| `body_pct` | % |
| `lower_wick` | цена |
| `lw_body_ratio` | x |
| `lw_range_pct` | % |
| `reclaim_pct` | % |
| `volume_30_ratio` | x |

`close_position_pct` в detector вычисляется той же формулой, что
`reclaim_pct`, но в active qualification не используется.

`range_pct_min` и `body_pct_max` присутствуют в config, но detector не
применяет их как активные фильтры. Нельзя описывать их как действующие условия.

### 6.1. Нулевые и отсутствующие данные

- `open == 0`: процентные метрики detector возвращают `0.0`, исключение не
  бросается; такая свеча не проходит пороги.
- `body == 0`: `lw_body_ratio = 0.0`; обычно не проходит `>= 1.0`.
- `range <= 0`: `lw_range_pct = 0.0`, `reclaim_pct = 0.0`; не проходит
  `reclaim >= 30.0`.
- `median30 <= 0`: `volume_30_ratio = 0.0`; не проходит `>= 2.0`.
- Пустой ответ или `< 2` свечей: `insufficient_candles`.
- Нет закрытой свечи: `no_completed_candle`.
- Некорректный timestamp: `invalid_timestamp`.

---

## 7. Пороги и операторы

| Условие | Значение | Оператор | Комментарий |
|---|---:|---|---|
| Red candle | `close < open` | обязательное | отдельная проверка monitor |
| Open → Low | **-5.0%** | `<=` | граница включительна |
| Volume30Ratio | **2.0x** | `>=` | граница включительна |
| LW / Body | **1.0x** | `>=` | граница включительна |
| Reclaim from Low | **30.0%** | `>=` | граница включительна |

Все условия объединяются через **AND**. Отдельного score-гейта нет; score не
рассчитывается для этого решения.

### 7.1. Границы

- `open_to_low_pct == -5.0` → PASS.
- `open_to_low_pct == -4.99` → FAIL.
- `volume_30_ratio == 2.0` → PASS.
- `volume_30_ratio == 1.999` → FAIL.
- `lw_body_ratio == 1.0` → PASS.
- `lw_body_ratio == 0.999` → FAIL.
- `reclaim_pct == 30.0` → PASS.
- `reclaim_pct == 29.999` → FAIL.

---

## 8. Примеры

### 8.1. Проходящий сигнал

```text
open=100, high=102, low=94, close=98, volume=1000
previous 30 volumes = [500] * 30
```

```text
range        = 8
range_pct    = 8.0%
open_to_low  = -6.0%      PASS (<= -5.0)
body         = 2
lw_body      = 4 / 2 = 2.0x  PASS (>= 1.0)
reclaim      = (98-94)/8 = 50.0%  PASS (>= 30.0)
volume_ratio = 1000/500 = 2.0x  PASS (>= 2.0)
is_red       = True       PASS
```

Итог: сигнал квалифицирован.

### 8.2. Точная граница

```text
open=100, high=103.3333333333, low=95, close=97.5, volume=1000
previous 30 volumes = [500] * 30
```

```text
open_to_low = -5.0%      PASS
body        = 2.5
lower_wick  = 2.5
lw_body     = 1.0x       PASS
range       = 8.3333...
reclaim     = 2.5/8.3333 = 30.0%  PASS
volume      = 2.0x       PASS
```

Итог: сигнал квалифицирован, все границы включительны.

### 8.3. Отказ по каждому условию

| Причина | Пример | Результат |
|---|---|---|
| Не красная | `open=100, close=100.5` | FAIL |
| Слабый drop | `low=95.01` при `open=100` → `-4.99%` | FAIL |
| Нет объёма | `volume=999`, median=500 → `1.998x` | FAIL |
| Малая нижняя тень | `open=100, close=97.4, low=95` → `lw/body=0.923` | FAIL |
| Слабый reclaim | `high=103.34, low=95, close=97.5` → `29.976%` | FAIL |

---

## 9. Фактический путь принятия решения

В коде есть два слоя, и это важно:

```python
result = check_capitulation_signal(...)   # detector, config thresholds
metrics = result.metrics
passed, results = check_thresholds(metrics)  # monitor, FIXED_THRESHOLDS
```

Active monitor **не использует** `result.qualified` для финального решения. Он
использует `check_thresholds()` с `FIXED_THRESHOLDS`:

```python
FIXED_THRESHOLDS = {
    "drop_pct": -5.0,
    "wick_body_ratio": 1.0,
    "reclaim_pct": 30.0,
    "volume_30_ratio": 2.0,
}
```

Плюс до этого вызывается `check_red_candle(open, close)`.

Следовательно, фактический gate:

```text
close < open
AND open_to_low_pct <= -5.0
AND lw_body_ratio >= 1.0
AND reclaim_pct >= 30.0
AND volume_30_ratio >= 2.0
```

`result.qualified` и `result.failed_conditions` вычисляются, но не влияют на
отправку. Сейчас значения detector/config и `FIXED_THRESHOLDS` совпадают,
поэтому расхождения нет. Если изменить только config, active monitor продолжит
использовать свои значения — это **dual source of truth**, технический долг.
Он не исправлялся, чтобы не менять production-поведение.

Для проверки equivalence добавлен
`tests/test_monitor_threshold_equivalence.py`: 5 000 случайных свечей, границы
и вырожденные случаи; расхождений нет.

---

## 10. Dedup

- SQLite: `/home/evreconse/sent_signals.db`.
- Таблица `sent_signals`, primary key `(symbol, candle_timestamp)`.
- `claim_signal()`:

```text
INSERT INTO sent_signals (..., telegram_status)
VALUES (..., 'pending')
COMMIT
```

- `sqlite3.IntegrityError` → сигнал уже обрабатывался, отправка пропускается.
- Успешная отправка → `telegram_status='sent'`, `telegram_message_id`.
- Полный failure → `telegram_status='failed'`, затем `DELETE` строки; memory-set
  очищается; сигнал может быть обработан повторно.
- `SENT_SIGNALS` — in-memory set, загруженный на старте; SQLite остаётся
  источником истины для атомарного claim.
- Pending-сигналы при старте только перечисляются; автоматического resend нет.
  Если процесс упал между claim и отправкой, строка останется pending и
  потребует ручного вмешательства.

Снимок на 2026-10-22: 663 строки, 468 pending, 195 sent. Значения меняются.

---

## 11. Telegram

- Токен: `EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN` или
  `EVRECONSE_TELEGRAM_BOT_TOKEN`.
- Получатели: personal chat и optional channel.
- Успех, если доставлено хотя бы одно сообщение; сохраняется первый
  `message_id`.
- HTTP 200 + `ok=true` + `message_id` считается успехом.
- При ошибке одного получателя второй всё равно пытается отправиться.
- Отдельного retry-loop нет; ошибки HTTP/JSON логируются.
- `chat_id` печатается в journald — privacy/ops risk.
- В рамках проверки реальные сообщения **не отправлялись**.

Сообщение содержит символ, UTC-время, OHLCV, Drop, Wick/Body, Reclaim,
Volume30Ratio и статусы PASS/FAIL.

---

## 12. Ошибки, retry и concurrency

- `MAX_CONCURRENT_REQUESTS = 10` (semaphore).
- Общий `BingXFetcher` с rate limiter: 450 запросов / 10 секунд.
- Rate limit: retry с exponential backoff и jitter; `max_retries=5` на уровне
  `_make_request` и внутренний цикл `_request_with_rate_limit`.
- Network/timeout: retry до 5 попыток, backoff до 10 секунд.
- Offline symbol: без retry, классифицируется как `offline`.
- Ошибка одного символа не останавливает цикл.
- `asyncio.gather(..., return_exceptions=True)` изолирует исключения задач.
- `KeyboardInterrupt` завершает цикл штатно.
- Отдельного global circuit breaker нет.

Ошибки классифицируются в `check_latest_candle_with_stats` как rate limit,
offline, network, API/exception; статистика пишется в journald.

---

## 13. Ограничения и непроверенные сценарии

1. **Память процесса.** Работающий процесс загружен до stats-only правки;
   побайтовое содержимое памяти не извлекалось. Алгоритмическая идентичность
   доказана статически и тестами, но не дампом памяти.
2. **Live Telegram.** Реальная доставка не проверялась.
3. **Private BingX.** Приватные эндпоинты и торговые операции не вызывались.
4. **CMC/CoinGlass.** Не использовались.
5. **Universe stale.** Active snapshot от 2026-10-08; БД принадлежит root и не
   доступна для записи процессу `evreconse`; refresh падает с readonly database.
6. **TTL/fallback.** `get_universe()` не проверяет expiry; fallback только при
   отсутствии active snapshot.
7. **API order.** Нет явной сортировки свечей; используется порядок ответа
   BingX и `reversed()`.
8. **4h window.** `startTime` не ограничивает выдачу при `limit=500`; реально
   до 500 свечей.
9. **Dual thresholds.** detector/config и `FIXED_THRESHOLDS` не связаны
   автоматически; текущие значения совпадают.
10. **Duplicate function.** `get_last_completed_candle` определён дважды;
    определения идентичны, второе перекрывает первое. Поведение не меняется.
11. **Dead code.** `is_signal_sent`, `check_latest_candle` (legacy),
    `format_capitulation_telegram_message` в detector не используются active
    path.
12. **Hardcoded paths.** `/home/evreconse/...`; локальный запуск на другой
    машине требует адаптации.
13. **Pending claims.** Автоматического resend нет; pending требует ручного
    вмешательства.
14. **Telegram chat_id в journald.** Диагностические сообщения содержат
    идентификаторы получателей.
15. **Score.** Score не рассчитывается и не является гейтом.
16. **LW-001.** Не активен; его legacy volume/incompatible-keyword пути не
    входят в production.

---

## 14. Тестовые доказательства

- `tests/test_server_sync_algorithms.py` — 18 тестов:
  - точные значения active thresholds;
  - формулы;
  - inclusive boundaries;
  - red candle;
  - отсутствие score;
  - LW-001 canonical thresholds/formulas;
  - отсутствие volume gate у LW-001.
- `tests/test_monitor_threshold_equivalence.py` — 3 теста:
  - `FIXED_THRESHOLDS` совпадают с config;
  - 5 000 случайных свечей дают одинаковое решение detector и monitor;
  - границы и вырожденные свечи дают одинаковое решение.
- Дополнительно серверный detector (baseline, SHA-256 `3b239a00…`) и
  GitHub detector загружены раздельно и прогнаны на 5 007 одинаковых кейсах;
  `qualified`, `failed_conditions` и `metrics` совпали побайтово.

Полный прогон после добавления: **136 passed**. Тесты не вызывают внешние
сервисы и не используют production-БД.

---

## 15. Итог

Активная стратегия — Capitulation / Absorption, 15m, LONG shadow mode.
Формулы, пороги, операторы, фильтры, порядок решения, dedup и Telegram-flow
совпадают с опубликованным GitHub-кодом. Побайтовая идентичность работающего
процесса не доказана; stats-only правка и безопасные адаптации описаны выше.

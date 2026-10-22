# EVRECONSE — полная техническая документация опубликованного состояния

**Репозиторий:** `https://github.com/evreconse/EVR`
**Ветка:** `main`

**Состояние до синхронизации:** `21fc7fde3c605336bc5c4acf601de7660b2398c8`

**Состояние после синхронизации:** `c6d00fa9623b83234c1674b8bf9bbbfe96500d96` (sync commit; subsequent
docs-only commit updates the verification record)

**Дата подготовки:** 2026-10-22

**Источник истины:** работающий production-сервер EVRECONSE, inspected read-only

**Среда локальной проверки:** Python 3.11.17, macOS, отдельный clone

---

## 1. Главный вывод

Production-сервис EVRECONSE **не использует LW-001**. Активная стратегия —
**Capitulation / Absorption**:

- 15m BingX USDT Perpetual;
- только последняя закрытая свеча;
- LONG-кандидаты в shadow mode;
- реальная торговля отключена;
- уведомления в Telegram;
- dedup в SQLite;
- порог `Open → Low` — **-5.0%**, а не `-2.5%`.

GitHub приведён к серверному состоянию:

- добавлен активный entry point
  `realtime_capitulation_monitor_fixed.py`;
- заменён устаревший Capitulation detector на серверный config-driven detector;
- добавлены серверные пороги
  `src/config/capitulation_thresholds.py`;
- синхронизированы BingX fetcher, rate limiter, endpoints, universe provider и
  universe cache;
- LW-001 приведён к серверным значениям, включая **-5.0%**;
- systemd unit переключён с LW-001 на активный Capitulation monitor;
- добавлены regression-тесты на серверные формулы и пороги;
- обновлены README, LW-001 spec и оба обязательных документа.

Сервер **не изменялся**: все действия были read-only.

---

## 2. Production baseline

### 2.1. Процесс и supervisor

| Параметр | Значение |
|---|---|
| systemd unit | `evreconse.service` |
| ExecStart | `/usr/bin/python3 /home/evreconse/realtime_capitulation_monitor_fixed.py` |
| WorkingDirectory | `/home/evreconse` |
| User | `evreconse` |
| Interpreter | `/usr/bin/python3.11` |
| MainPID | `880596` |
| Started | `2026-10-17 08:02:29 UTC` |
| NRestarts | `0` |
| Restart | `always`, `RestartSec=15` |
| Environment | `PYTHONUNBUFFERED=1` |
| Env source | `/home/evreconse/.env` через `load_dotenv()` |

Установлено:

- в `/home/evreconse` нет `.git`; это standalone deployment, не checkout;
- пакет `evreconse` не установлен в site-packages; используется локальный код;
- активен один экземпляр монитора;
- пользовательского cron и релевантных systemd timers нет;
- других активных EVRECONSE-сервисов не обнаружено.

### 2.2. Оговорка о версии файла

`realtime_capitulation_monitor_fixed.py` имеет mtime **2026-10-17 18:45:03 UTC**,
процесс запущен **2026-10-17 08:02:29 UTC** и не перезапускался. Поэтому
работающий процесс загрузил версию до поздней stats-only правки
(`apply_fix.py`).

Правка меняет только:

- конкретизацию причины отказа (`DROP_FAIL`, `VOLUME_FAIL`,
  `WICK_BODY_FAIL`, `RECLAIM_FAIL`);
- распределение счётчиков статистики.

Она не меняет пороги, формулы, red-candle, candle confirmation, dedup,
Telegram-flow или universe. Алгоритмический эталон одинаков. В GitHub
опубликован текущий файл с этой stats-правкой; сервер не перезапускался.

### 2.3. Runtime-состояние

| Объект | Значение на момент проверки |
|---|---|
| `sent_signals.db` | 663 строки: 468 `pending`, 195 `sent` |
| active universe cache | 574 символа |
| BingX active contracts | 1239 |
| cache fetched_at | `2026-10-08T09:25:51Z` |
| cache id | 5 |

Значения являются read-only снимком и меняются во время работы.

---

## 3. Активная стратегия: Capitulation / Absorption

### 3.1. Формулы

```python
range        = high - low
range_pct    = range / open * 100
open_to_low  = (low - open) / open * 100
body         = abs(close - open)
body_pct     = body / open * 100
lower_wick   = min(open, close) - low
lw_body      = lower_wick / body                      # 0.0 при body == 0
lw_range_pct = lower_wick / range * 100               # 0.0 при range == 0
reclaim_pct  = (close - low) / range * 100            # 0.0 при range == 0
median30     = median(previous 30 completed M15 volumes)
volume_ratio = volume / median30                      # 0.0 при median30 == 0
is_red       = close < open
```

### 3.2. Пороги

| Условие | Значение | Оператор |
|---|---:|---|
| Red candle | `close < open` | обязательное |
| Open → Low | **-5.0%** | `<=` |
| Volume30Ratio | **2.0x** | `>=` |
| LW / Body | **1.0x** | `>=` |
| Reclaim from Low | **30.0%** | `>=` |

Все условия — AND. Score-гейта нет.

Конфигурация в GitHub:
`src/config/capitulation_thresholds.py`. На сервере файл находится по пути
`config/capitulation_thresholds.py`; в GitHub он размещён внутри существующего
пакета `src/config`, чтобы не конфликтовать с package layout.

### 3.3. Подтверждение свечи

- timeframe: **15m**;
- берётся последняя **закрытая** свеча;
- закрытость: `timestamp + 15 * 60 * 1000 <= now_ms`;
- запрашивается 4 часа истории;
- нужно минимум `candle_index >= 31`, то есть **32 свечи**;
- текущая незакрытая свеча игнорируется;
- цикл запускается около `:01/:16/:31/:46` (после закрытия M15 + 60 секунд).

### 3.4. Universe

- все активные USDT perpetual contracts BingX;
- без TOP-500 ограничения;
- фильтры: stablecoin, wrapped, leveraged, synthetic, non-trading;
- SQLite cache с TTL 24h;
- fallback на last-good universe;
- на момент проверки — 574 символа.

### 3.5. Dedup

- SQLite: `sent_signals.db`;
- PK: `(symbol, candle_timestamp)`;
- atomic claim через `INSERT`;
- `IntegrityError` → уже обработано;
- success → `telegram_status='sent'`, сохраняется message_id;
- failure → статус `failed`, затем claim откатывается через `DELETE`;
- memory-set используется только как ускорение;
- pending-сигналы при старте не переотправляются, а логируются как
  `manual intervention needed`.

### 3.6. Telegram

- получатели: personal chat + optional channel;
- success, если доставлено хотя бы одно сообщение;
- отдельного Telegram retry-loop нет;
- HTTP/JSON errors логируются;
- при полном failure claim откатывается;
- реальная отправка в рамках аудита не выполнялась.

### 3.7. Ошибки и устойчивость

- ошибки классифицируются: rate limit, offline, network, API, exception;
- `BingXFetcher` использует rate limiter и retry для рыночных запросов;
- concurrency ограничена 10;
- ошибка одного символа не останавливает цикл;
- `KeyboardInterrupt` завершает работу штатно;
- journald — основной журнал сервиса.

---

## 4. LW-001 (inactive / legacy)

LW-001 присутствует в коде, но **не запущен**. `evreconse.service` указывает на
Capitulation monitor.

### 4.1. Формулы

```python
range_pct       = (high - low) / open * 100
body_pct        = abs(close - open) / open * 100
lower_wick      = min(open, close) - low
lw_body_ratio   = lower_wick / body                 # 0.0 при body == 0
lw_range_pct    = lower_wick / (high - low) * 100   # 0.0 при range == 0
open_to_low_pct = (low - open) / open * 100
is_red          = close < open
```

### 4.2. Пороги

| Условие | Значение | Оператор |
|---|---:|---|
| Range | **4.5%** | `>=` |
| Body | **0.8%** | `>=` |
| LW / Body | **1.3x** | `>=` |
| LW / Range | **55.0%** | `>=` |
| Open → Low | **-5.0%** | `<=` |
| Red candle | `close < open` | обязательное |

Volume Ratio **не участвует**. Score не является гейтом. `final_score` в legacy
strategy носит информационный характер.

### 4.3. Подтверждение свечи

- 15m, последняя закрытая свеча;
- `timestamp + 15min <= now`;
- 4 часа истории;
- минимум 2 свечи и `candle_index >= 1`;
- legacy monitor содержит optional demo auto-trader path, но он не запущен.

Canonical: `LW001_METRIC_SPEC.py` и `src/strategy/lw001_canonical.py`.
Legacy monitor: `realtime_lw001_monitor.py` (не включать без отдельного решения).

---

## 5. Компонентная таблица синхронизации

| Компонент | Сервер | GitHub до | Действие |
|---|---|---|---|
| `realtime_capitulation_monitor_fixed.py` | активный entry point | отсутствовал | добавлен |
| `src/strategy/capitulation_detector.py` | config-driven, 15 744 B | старый API, 9 889 B | заменён |
| `config/capitulation_thresholds.py` | активные пороги | отсутствовал | добавлен как `src/config/...` |
| `src/exchange/bingx_fetcher.py` | public data/retry/rate limit | другая реализация | синхронизирован |
| `src/exchange/bingx_rate_limiter.py` | 5 949 B | отсутствовал | добавлен |
| `src/exchange/bingx_endpoints.py` | 2 487 B | отсутствовал | добавлен |
| `src/data_provider/universe_provider.py` | 17 078 B | 15 872 B | синхронизирован |
| `src/data_provider/cmc_universe_cache.py` | 13 652 B | 13 232 B | синхронизирован |
| `realtime_lw001_monitor.py` | `-5.0` | `-2.5` | исправлен |
| `LW001_METRIC_SPEC.py` | `-5.0` | `-2.5` | исправлен |
| `src/strategy/lw001_canonical.py` | `-5.0` | `-2.5` | исправлен |
| `src/strategy/lw_001.py` | `-5.0` | `-2.5` | исправлен |
| `evreconse.service` | Capitulation | LW-001 | обновлён |
| `realtime_capitulation_monitor.py` | legacy | старый/несовместимый | compatibility shim |
| `backfill_capitulation_signals.py` | legacy | старый API | адаптирован |
| tests | — | не покрывали пороги | +18 regression tests |

---

## 6. Изменения в GitHub

### 6.1. Добавленные файлы

- `realtime_capitulation_monitor_fixed.py`;
- `src/config/capitulation_thresholds.py`;
- `src/exchange/bingx_rate_limiter.py`;
- `src/exchange/bingx_endpoints.py`;
- `tests/test_server_sync_algorithms.py`.

### 6.2. Обновлённые файлы

- `src/strategy/capitulation_detector.py`;
- `src/exchange/bingx_fetcher.py`;
- `src/data_provider/universe_provider.py`;
- `src/data_provider/cmc_universe_cache.py`;
- `realtime_lw001_monitor.py`;
- `realtime_lw001_monitor_fixed.py` (legacy threshold message);
- `LW001_METRIC_SPEC.py`;
- `src/strategy/lw001_canonical.py`;
- `src/strategy/lw_001.py`;
- `src/config/types.py`;
- `realtime_capitulation_monitor.py` (shim);
- `backfill_capitulation_signals.py`;
- `evreconse.service`;
- `scripts/replay_4day.py`;
- `README.md`;
- `LW001_PRODUCTION_SPEC.md`;
- `PROJECT_FULL_DOCUMENTATION.md`;
- `PROJECT_VERSION_VERIFICATION.md`.

### 6.3. Намеренно не копировано

- `.env`, токены, chat_id, API keys;
- `sent_signals.db`, `telegram_test.db`, `data/cmc_universe.db`;
- logs, forensic snapshots, dumps;
- runtime universe cache;
- серверные секретные unit/drop-in/env-файлы;
- персональные абсолютные данные о хосте.

---

## 7. Архитектура и поток данных

```text
systemd evreconse.service
  └── /usr/bin/python3 realtime_capitulation_monitor_fixed.py
      ├── load_dotenv()                         # .env, секреты
      ├── init_sent_signals_db()                # SQLite dedup
      ├── UniverseProvider.initialize()
      │   ├── CMCUniverseCache                  # active snapshot / TTL
      │   └── BingXFetcher.get_contracts()      # BingX public data
      ├── every ~15m + 60s:
      │   ├── fetch 4h of 15m candles
      │   ├── get_last_completed_candle()
      │   ├── require candle_index >= 31
      │   ├── calculate prev-30 volume median
      │   ├── check_capitulation_signal()       # config thresholds
      │   ├── claim_signal()                    # atomic dedup
      │   ├── send_signal_to_telegram()
      │   └── update / rollback status
      └── journald logs + optional forensic log
```

Capitulation detector — единственный источник активных формул. Legacy
`realtime_capitulation_monitor.py` не дублирует алгоритм, а делегирует в
активный entry point.

---

## 8. Deployment

```ini
[Unit]
Description=EVRECONSE Capitulation/Absorption Monitor
After=network.target

[Service]
Type=simple
User=evreconse
WorkingDirectory=/home/evreconse
ExecStart=/usr/bin/python3 /home/evreconse/realtime_capitulation_monitor_fixed.py
Restart=always
RestartSec=15
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Секреты читаются из `/home/evreconse/.env`; в unit-файле их нет. Для GitHub
опубликован безопасный шаблон без значений.

Требования к runtime:

- Python 3.11+;
- `aiohttp`, `tenacity`, `python-dotenv`, `aiolimiter`, `websockets`;
- доступ к BingX public market data;
- Telegram bot token/chat ids в `.env`;
- writable directory для `sent_signals.db`, `logs/`, `data/`.

Серверный runtime зафиксирован отдельно (aiohttp 3.9.5, tenacity 9.1.4,
websockets 17.0.1 и др.); GitHub сохраняет declared dependency ranges, а не
копирует серверный freeze.

---

## 9. Тесты и статические проверки

Выполнено локально, без production integrations:

| Проверка | Результат |
|---|---|
| `pytest -q` | **133 passed** |
| `pytest tests/test_server_sync_algorithms.py -q` | **18 passed** |
| `ruff check src tests LW001_METRIC_SPEC.py` | **All checks passed** |
| `mypy src/ tests/ --explicit-package-bases` | **Success: no issues found** |
| `py_compile` изменённых Python-файлов | **OK** |
| runtime import algorithm modules | **OK** |
| runtime import `src.exchange` / `src.data_provider` | **OK** |

Mypy: два серверных I/O-модуля (`universe_provider.py`,
`cmc_universe_cache.py`) исключены из strict module discovery, поскольку
сохраняют production-реализацию с существующим typing debt; алгоритмы, config,
fetcher/rate limiter и тесты проверяются. Это ограничение зафиксировано явно,
а не замаскировано.

Не выполнялись:

- реальные сделки/ордера;
- реальная отправка Telegram;
- приватные BingX-запросы;
- CMC/CoinGlass-запросы;
- restart systemd;
- запись на production-сервер.

---

## 10. Доказательство соответствия алгоритма

| Параметр | Сервер | GitHub после |
|---|---:|---:|
| Capitulation Open→Low | -5.0 | -5.0 |
| Capitulation Volume30 | 2.0 | 2.0 |
| Capitulation LW/Body | 1.0 | 1.0 |
| Capitulation Reclaim | 30.0 | 30.0 |
| LW-001 Range | 4.5 | 4.5 |
| LW-001 Body | 0.8 | 0.8 |
| LW-001 LW/Body | 1.3 | 1.3 |
| LW-001 LW/Range | 55.0 | 55.0 |
| LW-001 Open→Low | -5.0 | -5.0 |

Значения проверены чтением серверных файлов и regression-тестами. Для активного
файла `realtime_capitulation_monitor_fixed.py` sha256 совпадает с серверным
(`f661e379...`); detector/config/LW-001 синхронизированы алгоритмически, с
безопасными адаптациями package layout и форматирования.

---

## 11. Намеренно сохранённые различия и ограничения

1. **Секреты и runtime-данные** отсутствуют в GitHub по определению.
2. **Пути**: GitHub использует repo layout; сервер — `/home/evreconse`.
3. **Зависимости**: GitHub pyproject ranges, серверный freeze отличается.
4. **SQLite**: GitHub не содержит production БД и накопленных сигналов.
5. **Service unit**: опубликован безопасный шаблон, не копия серверного
   unit с локальными настройками.
6. **Legacy LW-001** остаётся в коде, но не активен; его monitor не запускается.
7. **stats-only fix** в активном monitor не был загружен процессом, так как
   сервер не перезапускался.
8. **Mypy exclusion** для двух серверных I/O-модулей (см. §9).
9. **Hardcoded production paths** в legacy/active monitor сохранены как
   серверное поведение; при переносе нужен deployment-конфиг.
10. **Live-проверки** Telegram/BingX private/CMC не выполнялись.

---

## 12. Безопасность и read-only подтверждение

В ходе работы:

- не было записи на production-сервер;
- не изменялись файлы, `.env`, БД, логи, systemd units, пакеты и Git;
- не было restart/reload сервиса;
- не выполнялись реальные торговые, Telegram, private BingX, CMC или CoinGlass
  действия;
- секреты не выводились в документацию и не добавлялись в Git;
- серверные БД, логи и дампы не копировались;
- push затрагивает только GitHub и выполняется отдельным коммитом.

Локальный `SERVER_SOURCE_OF_TRUTH.md` содержит инфраструктурные детали и
**не публикуется**.

---

## 13. Ссылки

- `README.md` — краткий старт и команды.
- `LW001_PRODUCTION_SPEC.md` — LW-001 canonical spec.
- `PROJECT_VERSION_VERIFICATION.md` — журнал сверки, component table, тесты,
  ответы на 10 вопросов.
- `tests/test_server_sync_algorithms.py` — regression tests серверных порогов.

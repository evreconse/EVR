# EVRECONSE — аудит опубликованного состояния

**Дата аудита:** 2026-10-22  
**Репозиторий:** https://github.com/evreconse/EVR  
**Ветка:** `main`  
**Проверенное состояние кода:** `bfb11f0210eaf6309a5a5d1eeb3267d5b0c53868`  
**Дерево проверенного состояния:** `654189c0c3d48465ba62e0fcf31a7005beaf03dc`  
**Предыдущий `origin/main` до публикации:** `55591942a570c83a9d10bf1b0d08d775d7ef49f4`

## 1. Краткий вывод

Опубликованное состояние собирается, проходит CI и содержит осмысленное ядро LW-001, но **не является готовой к промышленной эксплуатации end-to-end системой**. Это подтверждённый аудит кода, а не подтверждение реальной торговли.

Главный риск не в формулах LW-001: канонические формулы и пороги реализованы и покрыты unit-тестами. Главный риск в том, что основной `src`-конвейер не получает рыночные события:

1. WebSocket-клиент отправляет BingX подписку в формате, не соответствующем официальному протоколу BingX.
2. `BingXDataProvider.stream()` нигде не запускается.
3. Даже при появлении сообщения callback в lifecycle имеет неверный контракт: синхронный `process_event()` оборачивается в `asyncio.create_task`, а в event engine передаётся `MarketDataMessage`, тогда как `process_event()` ожидает `MarketEvent`.
4. Event pipeline принудительно ставит `confirm=True` и не проверяет `is_closed`, поэтому неполная свеча может быть обработана как закрытая.
5. Конфигурация использует timeframe `"15m"`, а модельный enum требует `"M15"`; на этом пути возможен `ValueError`.
6. Отдельный root-монитор LW-001, который запускается systemd, работает в обход `src`-конвейера; его можно использовать только после live-проверки, а второй root-монитор Capitulation в опубликованном виде сигнал выдать не может.

**Практический статус:** опубликованный код — «foundation / integration in progress», а не production-ready. Включать реальную отправку сигналов или тем более торговлю без исправлений нельзя.

### Что действительно работает / подтверждено

- Чистая публикация `main` и успешный remote CI для `bfb11f0`.
- 115 локальных unit-тестов проходят на Python 3.11.
- Каноническая функция LW-001 `check_lw001_signal()` корректно проверяет шесть условий, включая red candle.
- Загрузка конфигурации, DI-контейнер, базовый lifecycle и файловое JSON-хранилище имеют рабочие фрагменты и тесты.
- Root-монитор `realtime_lw001_monitor.py` содержит правдоподобную логику получения свечей, выбора последней закрытой свечи, расчёта LW-001, дедупликации в SQLite и прямой отправки в Telegram. Это **не** подтверждено live-запуском.

### Что не работает или не подтверждено

- Реальный поток BingX → event pipeline.
- Приватные запросы BingX с подписью.
- Гарантированная доставка Telegram и корректный результат `DeliveryResult`.
- Capitulation-монитор.
- Автоторговля: модуль `src.exchange.bingx_trader` отсутствует.
- CMC/CoinGlass: клиенты есть, но в рабочем конвейере не используются; live-проверки нет.
- systemd-запуск, реальные ключи, реальные API-лимиты, сетевые сбои и восстановление после рестарта.

## 2. Границы аудита, источник истины и доказательства

### 2.1. Источник истины

Аудит выполнен по чистому клону опубликованной ветки `origin/main`, а не по локальной рабочей копии:

- remote `refs/heads/main` на момент аудита: `bfb11f0210eaf6309a5a5d1eeb3267d5b0c53868`;
- локальный `HEAD` клона совпадает с remote;
- дерево: `654189c0c3d48465ba62e0fcf31a7005beaf03dc`;
- рабочее дерево клона чистое;
- проверено 1 576 tracked-файлов.

### 2.2. Уровни доказательств

В отчёте используются три разных уровня, которые нельзя смешивать:

| Уровень | Что означает | Что проверено |
|---|---|---|
| **Код** | Статический анализ конкретного опубликованного файла и строк | Все выводы о логике, ветвлениях, контрактах и конфигурации |
| **Локальный запуск** | Запуск в чистом клоне на Python 3.11 | `pytest`: 115 passed; сборка wheel; импорт/компиляция в рамках CI |
| **Remote CI** | GitHub Actions для точного SHA | Ruff, mypy, compileall, wheel, pytest — все шаги успешны |
| **Live-интеграция** | Реальные BingX/Telegram/CMC/CoinGlass и реальные ключи | **Не выполнялась**; выводы об этих системах основаны на коде и официальной документации, но не на живом обмене |

### 2.3. Remote CI

Успешный запуск для `bfb11f0`:

- https://github.com/evreconse/EVR/actions/runs/39669095081
- job: `Lint, type-check and test`
- успешные шаги: `Ruff`, `Mypy`, `Compile Python sources`, `Build wheel`, `Pytest`.

Предыдущий запуск `39668390952` для `ea6775e` падал на `ModuleNotFoundError: No module named 'websockets'`; он **не является** доказательством текущего состояния и заменён успешным запуском выше.

### 2.4. Что в аудит не входит

- Проверка реальных секретов, ключей и платёжных данных.
- Реальная торговля, вывод средств, проверка баланса.
- Нагрузочное тестирование и проверка задержек.
- Пентест и аудит инфраструктуры.
- Юридическая и финансовая оценка стратегии.
- Гарантия отсутствия всех возможных секретов в старых commit’ах: выполнялась целевая и типовая проверка, а не формальное доказательство.
- Реальный порядок/типы полей BingX kline и фактическая схема WS-сообщений: код предполагает, что klines приходят newest-first, а `time` — целое число; live-проверкой это не подтверждено.
- Реальные лимиты BingX, задержки, reconnect-поведение и поведение Telegram при 429/5xx.

### 2.5. Граница публикации отчёта

Проверенный код — `bfb11f0`. Этот отчёт добавляется **отдельным коммитом после** аудированного состояния. Коммит не может содержать собственный SHA, поэтому точный финальный SHA `origin/main` фиксируется после push в журнале публикации и в ответе владельцу. Содержательное отличие финального `origin/main` от аудированного состояния — только этот файл; код, конфигурация, CI и зависимости не меняются.

## 3. Публикация и целостность репозитория

### 3.1. Что опубликовано

- Старый `origin/main` `5559194...` заменён очищенной историей.
- Опубликован коммит `ea6775e` — курированный снимок проверенного состояния: 137 файлов, 3 138 вставок, 3 594 удаления.
- Затем добавлен `bfb11f0` — исправление публикационной блокировки CI: `websockets>=17.3` в `pyproject.toml` и установка `-e ".[dev]"` в workflow.
- Ветка `main` — единственная рабочая ветка; тегов нет; в опубликованной истории 19 коммитов.
- Remote и локальный клон совпадают по SHA и tree.

### 3.2. Проверка секретов

Проверка выполнялась без вывода значений:

- целевые известные литералы и старые credential-строки;
- типовые шаблоны GitHub/AWS/Google/Slack/Telegram/private-key;
- все уникальные blobs опубликованной истории (1 463 blob’а);
- 1 576 tracked-файлов текущего дерева.

Результат: совпадений по проверенным шаблонам не найдено. Это подтверждает отсутствие известных и типовых секретов в опубликованном состоянии, но не заменяет полноценный secret-scanning вроде GitHub Secret Scanning и не даёт абсолютной гарантии.

### 3.3. Что в репозитории осталось лишним

Репозиторий содержит значительно больше, чем рабочий код:

| Категория | Файлов | Размер |
|---|---:|---:|
| `.devin/` (IDE/расширения) | 480 | ~307 MB |
| `Microsoft Office/` | 250 | ~6.2 MB |
| `Default Project/` (старая копия проекта) | 250 | ~20.5 MB |
| `.codeium/` | 60 | ~0.6 MB |
| `data/*.json` (старые event-артефакты) | 85 | ~71 KB |
| **Итого мусора** | **1 040 из 1 576** | **~334 MB** |

Git-pack сжимает это до ~9.72 MiB, но clone checkout всё равно разворачивает ~350 MiB. В корне 185 Python-скриптов; 667 Python-файлов находятся вне `src/` и `tests/`. Многие из них — одноразовые research/analysis/check-скрипты, дубликаты и старые версии монитора.

В `.gitignore` есть `.devin/`, `.codeium/`, `Default Project/`, `Microsoft Office/`, но ранее добавленные файлы остаются tracked: `.gitignore` не удаляет уже отслеживаемые файлы. Это нужно исправлять отдельным коммитом, а не в аудиторском отчёте.

`LOCAL_TEST_READINESS_REPORT.md` в опубликованном дереве отсутствует. На момент создания этого отчёта `PROJECT_AUDIT_REPORT.md` также отсутствовал.

## 4. Архитектура

### 4.1. Две параллельные системы

В репозитории фактически сосуществуют два разных приложения.

#### A. Модульный `src`-конвейер

Предназначенная архитектура:

```text
BingX REST/WS
      │
      ▼
BingXDataProvider
      │  MarketDataMessage / stream
      ▼
EventEngine.process_event(MarketEvent)
      │
      ▼
EventContext
      │
      ├── PipelineStageStrategy  → LW001Strategy / canonical check
      ├── PipelineStageScorer    → ScoringEngine
      ├── PipelineStageNotifier  → NotificationEngine → Telegram
      ├── PipelineStageOutcome   → OutcomeTracker
      └── PipelineStageStorage   → FileStorageRepository
```

Фактически поток WS не подключён, а event pipeline получает данные только в тестах через вручную созданные `MarketEvent`. Поэтому схема выше — целевая, а не работающая.

#### B. Root-мониторы

Практический production-entry point по systemd:

```text
BingXFetcher.get_klines()
      │
      ▼
realtime_lw001_monitor.py
      │  локальная копия порогов
      ├── SQLite sent_signals.db (дедупликация)
      ├── прямой Telegram Bot API
      └── (опционально) отсутствующий AutoTraderManager
```

Этот путь не использует `StrategyEngine`, `ScoringEngine`, `EventEngine`, `OutcomeTracker` и файловое event-хранилище. Он дублирует LW-001-логику и фактически является отдельным приложением.

`realtime_capitulation_monitor.py` — второй root-монитор, также обходящий `src`-конвейер; в опубликованном виде он неработоспособен (см. раздел 13).

### 4.2. Пакеты `src`

| Пакет | Ключевые файлы | Назначение | Фактический статус |
|---|---|---|---|
| `application` | `bootstrap.py`, `lifecycle.py`, `service_container.py`, `application.py`, `health.py` | Сборка зависимостей, startup/shutdown, health | DI и bootstrap тестируются; lifecycle не запускает WS-поток |
| `config` | `config_manager.py`, `loader.py`, `types.py`, `validator.py` | YAML + `.env` + ENV, dataclass-конфиг, валидация | Работает частично; часть YAML-полей не доходит до dataclass |
| `core` | `logging/__init__.py` | Логирование | Реализовано |
| `data_provider` | `bingx_provider.py`, `websocket_client.py`, `universe_provider.py`, `cmc_universe_cache.py`, `rate_limiter.py`, `rest_client.py` | BingX REST/WS, universe, кэш | REST-снимки частично; WS неработоспособен; universe не прогревается; `RestClient` не используется |
| `event_engine` | `event_engine.py`, `event_pipeline.py`, `event_factory.py`, `event_scheduler.py`, `state_machine.py` | Event lifecycle и pipeline | Pipeline частично; factory-переходы не реализованы; WS-путь отсутствует |
| `exchange` | `bingx_fetcher.py`, `coinmarketcap_fetcher.py`, `coinglass_fetcher.py` | Внешние API | BingX fetcher с ошибками auth; CMC/CoinGlass не используются |
| `models` | `market_event.py`, `enums.py`, `identifiers.py`, `transition_guard.py` | Модели, статусы, ID | Реализовано и покрыто частью тестов |
| `notification` | `notification_engine.py`, `queue.py`, `telegram_service.py`, `retry_policy.py`, `rate_limiter.py`, `formatter.py` | Очередь и Telegram | Частично; движок возвращает PENDING, очередь нарушает приоритет, конфиг очереди игнорируется |
| `outcome` | `outcome_tracker.py` | TP/SL и expiry | Реализовано, но pipeline-stage — no-op |
| `scoring` | `scoring_engine.py`, `parameters/lower_wick.py`, `parameters/candle_confirmation.py` | Скоринг | Реализовано, но не влияет на qualification/отправку |
| `storage` | `storage_engine.py`, `file_repository.py` | JSON-хранение событий | Файловая запись есть; дедупликация отсутствует; rejected-события сохраняются как qualified |
| `strategy` | `lw001_canonical.py`, `lw_001.py`, `capitulation_detector.py`, `strategy_engine.py` | LW-001 и Capitulation | LW-001 реализован; Capitulation не интегрирован; логика дублируется |

### 4.3. Entry points

| Entry point | Как запускается | Статус |
|---|---|---|
| `src/main.py` | `python src/main.py` (нет `[project.scripts]`) | Инициализирует модульное приложение; `--testnet` игнорируется; при ошибке возвращает 1 без лога |
| `run.py` | `python run.py` | Сломан: `sys.exit(main())` на async-функции, корутина не awaited |
| `realtime_lw001_monitor.py` | systemd `ExecStart=/usr/bin/python3 realtime_lw001_monitor.py` | Фактический production-entry point; обходит `src` |
| `realtime_capitulation_monitor.py` | ручной запуск | В опубликованном виде не может выдать сигнал |
| `.github/workflows/ci.yml` | GitHub Actions | Lint/type-check/compile/wheel/pytest |
| Остальные root-скрипты | ручной запуск | Research/analysis, не packaged, не тестируются CI |

Systemd-юнит `evreconse.service` использует `WorkingDirectory=/home/evreconse`, `User=evreconse`, `EnvironmentFile=-/etc/evreconse/evreconse.env`. Секретов в unit-файле нет — это правильно. Но `ExecStart=/usr/bin/python3` не использует project venv из README; если зависимости установлены только в `.venv`, сервис не стартует. Путь к SQLite и universe-кэшу жёстко зашит под этого пользователя, поэтому запуск из другого каталога/пользователя не работает без правки кода.

## 5. Поток данных и подтверждённые разрывы

### 5.1. Что делает `src` при старте

`bootstrap.py` создаёт:

1. `ConfigurationManager` и `AppConfig`;
2. `StorageEngine` с `FileStorageRepository` в `config.storage.data_path`;
3. `BingXDataProvider` и вызывает `connect()`;
4. `StrategyEngine`, регистрирует `LW001Strategy`;
5. `ScoringEngine` с двумя параметрами;
6. `NotificationEngine` с Telegram-сервисом;
7. `OutcomeTracker`;
8. `EventEngine`;
9. lifecycle, который подписывается на символы и запускает health/heartbeat.

Но `BingXDataProvider.connect()` только выставляет `_connected = True`; WebSocket не открывается. `subscribe_symbols()` только сохраняет имена и timeframe. `stream()` существует, но его никто не вызывает.

Подтверждение:

- `src/application/lifecycle.py:176-195` — устанавливает callback, получает символы, вызывает `subscribe_symbols`, запускает heartbeat/health, но не `stream()`;
- `src/data_provider/bingx_provider.py:143-154` — `connect()` не создаёт WS;
- `src/data_provider/bingx_provider.py:167-187` — `subscribe_symbols()` только обновляет set;
- `src/data_provider/bingx_provider.py:296-333` — `stream()` есть, но вызовов в `src` нет.

### 5.2. WebSocket-протокол BingX

Клиент формирует topic:

```text
kline.15m.BTC-USDT
```

и отправляет:

```json
{"op": "subscribe", "args": ["kline.15m.BTC-USDT"]}
```

Официальная документация BingX swapV2 socket market показывает другой формат:

```json
{"id": "...", "reqType": "sub", "dataType": "BTC-USDT@kline_1min"}
```

Код: `src/data_provider/websocket_client.py:296`, `:403`; endpoint `:389-391`. Официальная страница: `https://bingx-api.github.io/docs/#/en-us/swapV2/socket/market.html` (проверена документация, не live-соединение).

Следствия:

- подписка, вероятно, не будет принята;
- даже при принятии сообщения BingX используют поле `dataType`, а `_on_ws_message()` проверяет `type == "kline"` или `topic.startswith("kline")` (`src/data_provider/bingx_provider.py:589-599`), поэтому сообщения будут отброшены;
- health-monitor при отсутствии первого сообщения только пишет warning и не инициирует reconnect (`src/data_provider/bingx_provider.py:505-529`), то есть соединение может оставаться «подписанным», но мёртвым.

### 5.3. Неверный контракт callback

`lifecycle.py:177-179` передаёт в провайдер:

```python
lambda event: self._context.event_engine.process_event(event)
```

`BingXDataProvider._on_ws_message()` делает:

```python
asyncio.create_task(self._candle_callback(message_obj))
```

Проблемы:

1. `process_event()` — синхронная функция, возвращающая `dict`, а не coroutine. `asyncio.create_task()` требует coroutine; будет `TypeError`.
2. Даже если бы callback был coroutine, `process_event()` ожидает `MarketEvent`, а провайдер передаёт `MarketDataMessage` (`_convert_kline_to_message`). `_create_context()` сразу обращается к `event.market_data` (`src/event_engine/event_engine.py:352-354`), чего у сообщения нет.
3. `process_event()` вызывается из WS-потока и внутри создаёт отдельный event loop/thread (`:295-305`), что дополнительно усложняет конкурентность и shutdown.

Это не «мелкий баг»: при текущем контракте реальное сообщение не может дойти до стратегии ни при каком содержимом свечи.

### 5.4. Закрытая свеча и timeframe

`PipelineStageStrategy` реконструирует `MarketEvent` и принудительно задаёт:

```python
confirm=True
```

(`src/event_engine/event_pipeline.py:172-180`).

При этом:

- `LW001Strategy.evaluate()` проверяет `strategy_data.confirm` и должен отвергать незакрытую свечу (`src/strategy/lw_001.py:184-186`), но pipeline обходит эту проверку, потому что сам ставит `confirm=True`;
- pipeline не проверяет `is_closed` / `is_closed`-флаг BingX;
- `PipelineStageScorer` и `PipelineStageStorage` также ставят `confirm=True` (`event_pipeline.py:252-260`, `:455-465`).

Дополнительно конфигурация задаёт `exchange.timeframe: "15m"` (`config.yaml:30`), а `models.enums.Timeframe` содержит только `"M15"` (`src/models/enums.py:39-48`). `BingXDataProvider.supported_timeframes` использует `"15m"` (`src/data_provider/bingx_provider.py:114-115`), а `LW001Strategy.supported_timeframes` возвращает `["15m"]` (`src/strategy/lw_001.py:80-82`). Pipeline вызывает `Timeframe(context.timeframe)` (`event_pipeline.py:146`, `:237`, `:443`). Если контекст пришёл из конфигурации/WS с `"15m"`, это `ValueError`; если вручную создан `MarketEvent` с `M15`, работает. Нормализации между форматами нет.

**Итог:** даже после исправления WS сообщение с незакрытой свечой может дать ложный сигнал, а `"15m"`-контекст может упасть на преобразовании enum.

### 5.5. Root-монитор LW-001: фактический поток

`realtime_lw001_monitor.py`:

1. При импорте инициализирует SQLite по жёсткому пути `/home/evreconse/sent_signals.db` (Windows: `C:/EVRECONSE_PROJECT/sent_signals.db`) — `:42-50`, `:108-123`.
2. В `main()` создаёт `UniverseProvider`, вызывает `initialize()` — `:632-635`.
3. `initialize()` не вызывает `refresh()`, а auto-refresh loop сначала спит 24 часа — `src/data_provider/universe_provider.py:137-169`.
4. На каждом цикле получает universe; при пустом кэше первые 24 часа universe пуст, сигналов нет.
5. Для каждого символа создаёт **новый** `BingXFetcher` (`:377-378`), то есть новую `aiohttp.ClientSession` на запрос.
6. Семантика `limit` в `get_klines()` фактически останавливает первую страницу на 500 свечах; для 15m это ~5 дней, поэтому история для LW-001 достаточна, но параметр `start_time` не ограничивает выборку так, как ожидается.
7. `get_last_completed_candle()` выбирает последнюю свечу по времени закрытия; затем `verify_signal_comprehensive_new()` считает канонические метрики и проверяет локальные пороги.
8. При сигнале — прямая отправка Telegram и запись в SQLite; модуль автоторговли отсутствует, поэтому `AUTO_TRADER_AVAILABLE=False`.

**Практический вывод:** root-монитор может быть рабочим только при наличии прогретого universe-кэша, рабочего Telegram и валидных ключей. Эти условия в аудите не проверялись live. Жёсткий путь и импорт-сайд-эффект делают его непереносимым и опасным для случайного запуска из другого окружения.

### 5.6. Root-монитор Capitulation: почему он не работает

`realtime_capitulation_monitor.py`:

- формально задаёт `start_time = now − 4h` (`:362-371`), но `BingXFetcher.get_klines()` **игнорирует `startTime`** и по умолчанию возвращает до 500 последних свечей; комментарий «4 hours = 16 candles» не соответствует фактическому запросу;
- вызывает `get_last_completed_candle(candles)` с одним аргументом (`:376`), а импортированная функция требует `(candles, now_ms)` (`src/strategy/capitulation_detector.py:206`); это гарантированный `TypeError`;
- затем требует `candle_index >= 31` и 30 предыдущих объёмов (`:388-391`). На фактических 500 свечах это могло бы пройти, но контракт окна неявный; если позже исправить `start_time` и ограничить выборку 4 часами, 16 свечей будет недостаточно;
- после `get_last_completed_candle` использует `.get()` на `latest_candle` в ветке, где допускается list/tuple (`:411`, `:414`), что даст `AttributeError` для не-dict;
- `get_fail_reason()` вызывается с заранее all-True результатами (`:431`), поэтому причина отказа всегда `None`;
- `results` в возвращаемом сигнале жёстко all-True (`:445-451`).

Итог: **в опубликованном виде Capitulation-монитор не может выдать сигнал**. Это подтверждено кодом, без необходимости live-запуска.

## 6. Функциональная матрица

| Функция | Статус | Комментарий |
|---|---|---|
| Загрузка YAML/.env/ENV | Реализовано | Приоритет ENV > `.env` > YAML > defaults |
| Валидация обязательных ключей | Реализовано | Требует BingX key/secret и Telegram token/chat даже для некоторых сценариев |
| DI/bootstrap | Реализовано, тестируется | 11 bootstrap + 15 DI тестов |
| Lifecycle start/stop | Частично | Тесты с фейками; реальный WS не стартует |
| MarketEvent/state machine | Реализовано | Часть тестов; event factory transition methods — `NotImplementedError` |
| BingX REST public data | Частично | Код есть, live-проверки нет; подпись/сессии имеют дефекты |
| BingX private API | Не работает | Подпись вычисляется и выбрасывается |
| BingX WebSocket | Не работает | Неверный формат подписки, фильтр сообщений, callback, отсутствие consumer’а |
| LW-001 canonical | Реализовано | 6 условий, unit-тесты |
| LW-001 root monitor | Реализовано, не проверено live | Фактический systemd-entry point |
| Capitulation detector | Частично | Формулы есть; не интегрирован; self-tests — no-op |
| Capitulation root monitor | Не работает | TypeError, `.get` на list/tuple, hardcoded results |
| Scoring | Реализовано, информационно | Не влияет на qualification и отправку |
| Telegram notification | Частично | Прямой сервис есть; движок возвращает PENDING; live нет |
| Notification queue/retry | Частично | Приоритет и конфиг сломаны; worker не обновляет stats |
| File storage | Частично | JSON + atomic write; дедупликация отсутствует |
| Outcome tracking | Частично | Класс есть; pipeline-stage no-op; live нет |
| Universe/CMC cache | Частично | Первый refresh не выполняется; TTL не enforced; CMC не используется |
| Auto-trading | Отсутствует | `src/exchange/bingx_trader.py` нет; import fallback отключает |
| CI | Работает | Один Python 3.11, без integration/security/coverage gate |
| Документация | Устарела | README/SETUP описывают Bybit/старую структуру |

## 7. Алгоритмы, метрики и пороги

### 7.1. LW-001: квалификация

Канонический источник: `src/strategy/lw001_canonical.py`; спецификация: `LW001_METRIC_SPEC.py`; обёртка стратегии: `src/strategy/lw_001.py`.

Все условия объединяются через **AND**; volume ratio в LW-001 **не используется**.

| Условие | Формула | Единица | Порог | Направление |
|---|---|---:|---:|---|
| Red candle | `Close < Open` | bool | — | обязательно |
| Range | `(High − Low) / Open × 100` | % | `>= 4.5` | минимум |
| Body | `abs(Close − Open) / Open × 100` | % | `>= 0.8` | минимум |
| Lower wick | `min(Open, Close) − Low` | цена | — | вычисляется |
| LW / Body | `LowerWick / abs(Close − Open)` | x | `>= 1.3` | минимум |
| LW / Range | `LowerWick / (High − Low) × 100` | % | `>= 55.0` | минимум |
| Open→Low | `(Low − Open) / Open × 100` | % | `<= −2.5` | максимум (отрицательное значение) |

Особенности реализации:

- при `Open == 0` каноническая функция возвращает `0.0` для процентных метрик, а `LW001_METRIC_SPEC` бросает `ValueError`;
- при `Body == 0` отношение LW/Body = `0.0`; при `Range == 0` LW/Range = `0.0`;
- отрицательный lower wick (если `Low` выше `min(Open, Close)`) не валидируется отдельно;
- формат сообщения `format_lw001_telegram_message()` жёстко дублирует пороги `4.5 / 0.8 / 1.3 / 55.0 / -2.5` и **не выводит red-candle condition** (`src/strategy/lw001_canonical.py:198-204`);
- `LW001Strategy.evaluate()` возвращает `final_score=0.0` (`src/strategy/lw_001.py:239-243`), потому что score не используется для квалификации; это осознанное решение, но оно означает, что `StrategyResult` не является оценкой качества.

### 7.2. Где LW-001 продублирован

| Место | Что содержит | Риск |
|---|---|---|
| `LW001_METRIC_SPEC.py` | формулы и 5 порогов; `check_all_conditions()` **без red candle** | «single source of truth» не является полным: проверка условий пропускает red |
| `src/strategy/lw001_canonical.py` | свои формулы + 6 условий + formatter | дублирование формул и порогов |
| `src/event_engine/event_pipeline.py` | прямой вызов canonical + собственные расчёты для текста | обходит `LW001Strategy` |
| `src/strategy/lw_001.py` | обёртка + текстовое объяснение с порогами | дублирование строк |
| `realtime_lw001_monitor.py` | `FIXED_THRESHOLDS`, `verify_signal_comprehensive_new`, `check_thresholds` | отдельная копия; не использует `check_lw001_signal` |
| `realtime_lw001_monitor_fixed.py` | старая копия с `volume_ratio: 1.5` | устаревшая логика, конфликтует с production |
| `format_lw001_telegram_message()` | жёсткие пороги в тексте | изменится spec — текст останется старым |

`LW001_METRIC_SPEC.check_all_conditions()` действительно проверяет только range/body/LW-body/LW-range/open-to-low; red-candle проверяется только в `lw001_canonical.check_lw001_signal()`. Если какой-либо код вызовет spec-функцию напрямую, green candle может пройти пять проверок.

### 7.3. Capitulation / Absorption

Источник: `src/strategy/capitulation_detector.py`.

Метрики:

| Метрика | Формула |
|---|---|
| Range % | `(High − Low) / Open × 100` |
| Open→Low % | `(Low − Open) / Open × 100` |
| Body % | `abs(Close − Open) / Open × 100` |
| Lower wick | `min(Open, Close) − Low` |
| LW/Body | `LowerWick / abs(Close − Open)` |
| LW/Range % | `LowerWick / (High − Low) × 100` |
| Reclaim % | `(Close − Low) / (High − Low) × 100` |
| Close position % | то же, что reclaim |
| Volume 30 median | медиана предыдущих 30 завершённых M15-объёмов |
| Volume 30 ratio | `Volume / Volume30Median` |

Пороги (`FIXED_THRESHOLDS`, `:13-19`):

| Условие | Порог |
|---|---:|
| Open→Low | `<= −2.5%` |
| LW/Body | `>= 1.0x` |
| Reclaim | `>= 30%` |
| Volume 30 ratio | `>= 2.0x` |
| Red candle | `Close < Open` |
| Окно медианы | 30 предыдущих свечей |

`check_thresholds()` требует все пять флагов, включая red. `range_pct`, `body_pct`, `lw_range_pct` вычисляются, но **не входят в capitulation-пороги**; это информационные метрики.

Состояние модуля:

- не импортируется в `src` pipeline и не экспортируется из `src/strategy/__init__.py`;
- не имеет pytest-тестов;
- `run_unit_tests()` содержит `if ...: pass else: pass` и всегда возвращает `True` (`:234-317`), то есть не является тестом;
- используется только root-монитором Capitulation, который сам неработоспособен;
- `format_telegram_message` в root-мониторе отдельно дублирует условия.

### 7.4. Scoring

Источник: `src/scoring/`.

Параметры и максимумы:

| Параметр | Max | Формула/поведение |
|---|---:|---|
| `lower_wick_quality` | 70 | Отношение lower wick / body |
| `candle_confirmation` | 30 | Body/range + позиция закрытия |

`lower_wick_quality`:

| Условие | Баллы |
|---|---:|
| `body <= 0` | 25 (doji-like) |
| ratio `>= 3.0` | 70 |
| `>= 2.5` | 60 |
| `>= 2.0` | 50 |
| `>= 1.5` | 35 |
| `>= 1.0` | 20 |
| `< 1.0` | 0 |

`candle_confirmation`:

| Условие | Баллы |
|---|---:|
| bullish, body/range `>= 0.6` | 30 |
| bullish, `>= 0.4` | 25 |
| bullish, `>= 0.2` | 20 |
| bullish, `>= 0.1` | 15 |
| bullish, `< 0.1` | 10 |
| бонус close near high (`close_position >= 0.8`) | `+5`, максимум 30 |
| bearish/doji, body/range `>= 0.4` | 20 |
| bearish/doji, иначе | 10 |

Итог:

```text
final_score = max(0, sum(score * weight) - penalties)
qualified = final_score >= min_confidence_score
```

Веса обоих параметров — `1.0`; максимум 100. В pipeline `min_confidence_score` жёстко `80.0` (`event_pipeline.py:267-275`).

Подтверждённые дефекты scoring:

1. **Scoring не гейтит отправку.** `LW001Strategy` возвращает `final_score=0`; pipeline выставляет score в контекст, но `PipelineStageNotifier` проверяет только `context.status == "qualified"` и не смотрит `confidence_score`. Порог 80 не влияет на отправку.
2. Для LW-001 обязательна red candle, а `candle_confirmation` для bearish даёт максимум 20 из 30; максимум 100 недостижим для валидной LW-001-свечи (70 + 20 = 90). Это не ошибка расчёта, но несоответствие названию «max 30» для red-сценария.
3. `config.yaml` кладёт `lower_wick_quality` и `candle_confirmation` на уровень `scoring`, а loader читает их из `scoring.parameters` (`config_manager.py:349-361`). Поэтому YAML-значения `max_score: 70/30` игнорируются, используются defaults 40/25; фактические классы всё равно дают 70/30. Это скрытая несогласованность.
4. `config.scoring.lower_wick_quality.max_score` не передаётся в `ScoringConfig` registry; bootstrap использует только `enabled` (`bootstrap.py:175-195`).

### 7.5. Risk / Outcome

| Параметр | Значение | Источник |
|---|---:|---|
| Take profit | `+3.0%` | `config.yaml:96`, `OutcomeConfig` |
| Stop loss | `-3.0%` | `config.yaml:97` |
| Max monitoring | 24 h | `config.yaml:99` |
| Expire after | 48 h | `config.yaml:100` |

`OutcomeTracker` умеет мониторить TP/SL/expiry, но `PipelineStageOutcomeTracker.process()` содержит `pass` (`event_pipeline.py:401-405`). `OutcomeTracker` не запускает реальный мониторинг цен; фактически outcome-трекинг не подключён.

Loader читает `monitoring.max_duration` / `expire_after`, а YAML содержит `max_duration_hours` / `expire_after_hours` (`config_manager.py:395-404`), поэтому значения совпадают только с defaults 24/48. Если изменить YAML, эффекта не будет.

### 7.6. Universe

`UniverseProvider.refresh()`:

1. `GET /openApi/swap/v2/quote/contracts`;
2. только символы, заканчивающиеся на `-USDT`;
3. статус `Trading` (значения `1`, `"Trading"`, `True`, `"true"`);
4. исключение stablecoin, wrapped, leveraged, synthetic;
5. **без top-N лимита**;
6. сохранение snapshot и fallback.

Кэш:

- `CMCUniverseCache.DB_PATH = data/cmc_universe.db` (относительный путь);
- `FALLBACK_FILE = data/last_good_universe.json`;
- TTL 24h, max stale 72h;
- `_init_db()` создаёт SQLite при конструировании; если `data/` отсутствует, будет `OperationalError`;
- `UniverseProvider.__init__` принимает `cache_db_path`/`fallback_file`, но игнорирует их и создаёт `CMCUniverseCache()` без аргументов (`universe_provider.py:120-129`);
- `initialize()` не вызывает `refresh()`, только запускает auto-refresh, который сначала спит 24h;
- `get_universe()` не проверяет TTL и возвращает stale бессрочно.

### 7.7. Notification, retry, rate limit

Конфигурация (`config.yaml:78-93`):

| Параметр | YAML | Фактически |
|---|---:|---|
| Queue max size | 1000 | `NotificationEngine` создаёт очередь на 10000 |
| Queue timeout | 5 s | Bootstrap создаёт `NotificationQueue` и выбрасывает |
| Rate limit requests | 30/s | Engine использует 10/s (или свои defaults) |
| Rate limit burst | отсутствует | default 30, но не применяется к engine |
| Retry attempts | 3 | Передаётся в engine |
| Retry base delay | 1.0 | Передаётся |
| Retry max delay | 60.0 | Передаётся |
| Multiplier | 2.0 | Передаётся |
| Delivery timeout | 30 s | Не используется в `send()` |
| Default priority | `"normal"` | dataclass ожидает `int`; не влияет на отправку |

`NotificationEngine.send()` ставит уведомление в очередь и сразу возвращает `DeliveryStatus.PENDING` (`notification_engine.py:194-221`). Pipeline логирует «Notification sent successfully» (`event_pipeline.py:367-376`), не проверяя статус. Worker может упасть при отправке, но результат уже потерян.

`NotificationQueue._insert_sorted()` никогда не увеличивает `insert_idx` (`queue.py:151-158`), поэтому каждый элемент вставляется в позицию 0; порядок приоритетов нарушен. `close()`/`remove()` вызывают `notify_all()` без захвата condition (`queue.py:240+`), что может дать `RuntimeError`; в текущем рабочем пути это не проявляется, потому что методы не используются.

## 8. Интеграции

| Интеграция | Реализация | Проверка | Статус |
|---|---|---|---|
| BingX public contracts | `GET /openApi/swap/v2/quote/contracts` | Только код/CI; live нет | Частично |
| BingX public klines | `GET /openApi/swap/v3/quote/klines` | Только код/CI; live нет | Частично |
| BingX private account/order | `X-BX-APIKEY`, HMAC | Live нет; подпись не добавляется в URL | **Не работает** |
| BingX WebSocket | URL + topic + JSON | Документация BingX + код; live нет | **Не работает** |
| Telegram Bot API | `sendMessage` напрямую и через service | Live нет | Не подтверждено |
| CoinMarketCap | `v1/cryptocurrency/listings/latest` | Live нет; в `src` не используется | Не интегрировано |
| CoinGlass | v4 liquidation history | Live нет; не используется | Не интегрировано |
| systemd | `evreconse.service` | Не запускался | Не подтверждено |

### 8.1. BingX REST: подпись и private API

В `BingXFetcher._request()`:

```python
timestamp = self._get_timestamp()
params["timestamp"] = timestamp
query_string = "&".join(...)
self._generate_signature(timestamp, query_string)
url = f"{BASE_URL}{endpoint}?{query_string}"
headers = {"X-BX-APIKEY": self.api_key}
```

`_generate_signature()` вычисляет HMAC, но возвращённое значение никуда не добавляется (`src/exchange/bingx_fetcher.py:104-108`). В итоге private-запросы не содержат `signature` и не могут пройти аутентификацию. Это подтверждено кодом, live не требуется.

Дополнительно:

- `get_balance()` ожидает `data.get("code")`, хотя `_request()` уже вернул `data` — двойная распаковка, поэтому баланс всегда `None` (`:286-296`);
- `get_order_status()` и `wait_for_order_fill()` имеют ту же проблему (`:315`, `:340-345`);
- каждый запрос создаёт новую `aiohttp.ClientSession` (`:115`), нет переиспользования соединений; для массового мониторинга это дорого;
- нет встроенного rate limiter в fetcher; root-монитор ограничивает только конкурентность 10 через semaphore, но создаёт fetcher на символ;
- `BingXFetcher` читает `EVRECONSE_EXCHANGE_API_KEY`/`SECRET` с одним подчёркиванием (`:47-48`), а `src`-конфиг использует `EVRECONSE_EXCHANGE__API_KEY`/`SECRET`; `.env.example` содержит оба варианта, но это хрупко.

### 8.2. Telegram

Прямой root-монитор использует `https://api.telegram.org/bot<token>/sendMessage`; token/chat читаются из `EVRECONSE_NOTIFICATION__TELEGRAM__BOT_TOKEN` или `EVRECONSE_TELEGRAM_BOT_TOKEN` (`realtime_lw001_monitor.py:290-294`). Секреты не печатаются.

`NotificationEngine`/`TelegramService` — отдельная реализация. В `src` pipeline send ставит в очередь и возвращает PENDING; фактическая доставка асинхронная. Live-проверка не выполнялась, поэтому нельзя утверждать, что Telegram работает в production.

### 8.3. CMC/CoinGlass

`CoinMarketCapFetcher` требует `EVRECONSE_CMC_API_KEY` и умеет `fetch_rankings()`, но в `src`/root-мониторе не вызывается. `CoinGlassFetcher` также не используется. `config.yaml` содержит секцию `cmc`, но `AppConfig` её не моделирует и loader её игнорирует. Это «код есть, интеграции нет».

### 8.4. Auto-trader

`realtime_lw001_monitor.py` пытается импортировать `src.exchange.bingx_trader.AutoTraderManager`, но файла нет. ImportError перехватывается, и торговля отключается. В `src` нет торгового модуля. Любые утверждения о «demo/VST auto-trading» в этом состоянии не соответствуют опубликованному коду.

## 9. Конфигурация

### 9.1. Источники и приоритет

`MultiSourceConfigLoader`:

```text
ENV > .env > config.yaml > defaults
```

Префикс `EVRECONSE_`; вложенность через двойное подчёркивание, например `EVRECONSE_EXCHANGE__API_KEY`. Обязательные параметры: BingX API key/secret, Telegram bot token/chat id (`src/config/types.py:445-450`).

### 9.2. Подтверждённые несогласованности

| Проблема | Где | Следствие |
|---|---|---|
| `exchange.name: "bingx"` vs `ExchangeName` только `BYBIT` | `config.yaml:25`, `src/config/types.py:46-50` | enum не используется для валидации; вводит в заблуждение; provider всё равно hardcoded BingX |
| Timeframe `"15m"` vs enum `"M15"` | `config.yaml:30`, `src/models/enums.py:39-48` | `Timeframe(...)` может бросить `ValueError` |
| `scoring.lower_wick_quality` вне `scoring.parameters` | `config.yaml:71-76`, `config_manager.py:349-361` | YAML max_score игнорируется, defaults 40/25 |
| `risk.monitoring.max_duration_hours` vs `max_duration` | `config.yaml:98-100`, `config_manager.py:395-404` | YAML-значения не применяются, используются defaults 24/48 |
| `storage.events_*` плоско vs вложенный `events` | `config.yaml:16-22`, `config_manager.py:406-414` | retention/buffer из YAML игнорируются |
| `exchange.reconnect_*` плоско vs ожидаемый `reconnect` | `config.yaml:38-40`, `config_manager.py:315-318` | используются defaults 0/1/300/2, а не YAML 0/1/60 |
| `notification.default_priority: "normal"` vs `int` | `config.yaml:92`, `types.py:331` | значение не соответствует типу; не влияет |
| `notification.rate_limit_window_seconds` | `config.yaml:87` | в dataclass нет поля; игнорируется |
| `cmc` section | `config.yaml:102-118` | не моделируется, не используется |
| `testnet`/`--testnet` | `src/main.py:53-56` | CLI-флаг не передаётся в приложение; всегда используется config/testnet=False |
| `run.py` | `run.py:14-17` | async main не awaited; entry point не работает |

### 9.3. Зависимости

- `pyproject.toml` — рабочий источник: Python `>=3.11`, `websockets>=17.3`, зависимости aiohttp/aiolimiter/dateutil/dotenv/PyYAML/tenacity/pydantic.
- `requirements.txt` — UTF-16 LE с BOM/CRLF; стандартный UTF-8-парсинг ломается; `websockets==17.0.1` конфликтует с `>=17.3`; список stale.
- `[project.scripts]` отсутствует; установленный wheel не даёт CLI-команды.
- `src/evreconse.egg-info` не tracked, но присутствует локально; не влияет на опубликованное дерево.

## 10. Хранилище и данные

### 10.1. Event storage

- `FileStorageRepository` хранит каждый `MarketEvent` отдельным JSON-файлом в `config.storage.data_path` (по умолчанию `./data`).
- Имя файла — UUID event id; есть защита от path traversal.
- Запись атомарная: temp file + rename.
- In-memory index по status/symbol/strategy.
- `StorageEngine.exists_by_symbol_timestamp()` пытается вызвать метод репозитория, но `FileStorageRepository` такого метода не имеет (`storage_engine.py:120-137`), поэтому дедупликация всегда `False`.
- Pipeline storage при наличии `context.strategy_id` вызывает `ME.qualified(...)` для **любого** события, включая rejected (`event_pipeline.py:455-469`), и ставит `confirm=True`. Это искажает persisted status.
- `FileStorageRepository.close()` выставляет `_loaded = False` вместо `_initialized`; эффект close фактически нулевой (`file_repository.py:523-526`).

### 10.2. Tracked data

В репозитории 85 JSON-файлов `data/*.json` — старые события (примеры датированы 2026-08-05, exchange `bybit`), а не тестовые фикстуры. Они занимают немного места, но создают ложное впечатление production-данных и смешиваются с runtime-каталогом. Их нужно либо удалить, либо перенести в явные fixtures с описанием происхождения.

### 10.3. Root SQLite

`realtime_lw001_monitor.py` создаёт `sent_signals` в `/home/evreconse/sent_signals.db`:

- таблица `sent_signals(symbol, candle_timestamp, sent_at)`, уникальный индекс;
- `claim_signal()` пытается вставить запись и при конфликте не отправляет дубль;
- инициализация выполняется **при импорте**, до `main()`, поэтому любой импорт модуля из другого окружения падает или создаёт неожиданный файл;
- путь не конфигурируется; на Windows используется другой жёсткий путь.

## 11. Тесты и CI

### 11.1. Локальные тесты

В чистом клоне на Python 3.11:

```text
115 passed in 0.23s
```

Разбивка:

| Модуль | Тестов |
|---|---:|
| `tests/test_async.py` | 14 |
| `tests/test_bootstrap.py` | 11 |
| `tests/test_di.py` | 15 |
| `tests/test_lifecycle.py` | 26 |
| `tests/test_scoring.py` | 26 |
| `tests/test_strategy.py` | 23 |
| **Итого** | **115** |

Тесты используют фейки (`tests/fixtures/`) и не делают реальных сетевых вызовов.

### 11.2. Покрытие

Сильные стороны:

- LW-001 canonical: пороги, red/green/doji, границы;
- scoring: параметры и агрегация;
- bootstrap/DI/lifecycle: сборка и переходы состояний;
- async helpers.

Пробелы:

- нет тестов на `src/exchange/*` (BingX REST, подпись, CMC, CoinGlass);
- нет тестов на `src/data_provider/*` (WS, reconnect, universe, cache);
- нет тестов на `src/notification/*` (очередь, retry, реальная доставка);
- нет тестов на `src/storage/*` (save/load, dedup, corrupted JSON);
- нет тестов на `src/event_engine/event_pipeline.py`;
- нет тестов на `src/outcome/*`;
- нет тестов на root-мониторы;
- нет integration/e2e/contract-тестов;
- Capitulation `run_unit_tests()` — фиктивный.

### 11.3. CI

`.github/workflows/ci.yml`:

- только Python 3.11;
- `ruff check src tests LW001_METRIC_SPEC.py`;
- `mypy src/ tests/ --explicit-package-bases`;
- `compileall`;
- `pip wheel`;
- `pytest tests/ -q`.

CI **не проверяет** root-скрипты, `realtime_*_monitor.py`, `run.py`, реальный импорт пакета как installed CLI, миграции/БД, secrets, coverage threshold. Поэтому зелёный CI не означает работоспособность production-entry point.

## 12. Мёртвый, дублированный и незавершённый код

| Объект | Статус | Комментарий |
|---|---|---|
| 185 root `.py` | Большей частью research/one-off | Не packaged, не тестируются; 667 Python вне `src`/`tests` |
| `.devin`, `.codeium`, `Microsoft Office`, `Default Project` | Tracked junk | 1 040 файлов, ~334 MB; `.gitignore` не помогает для уже tracked |
| `src/strategy/capitulation_detector.py` | Не интегрирован | Нет экспорта/тестов/pipeline |
| `realtime_capitulation_monitor.py` | Не работает | TypeError + insufficient history |
| `realtime_lw001_monitor_fixed.py` | Устаревшая копия | Volume ratio 1.5, конфликтует с LW-001 |
| `src/data_provider/rest_client.py` | Не используется | Только экспорт/README/фикстуры |
| `CoinMarketCapFetcher`, `CoinGlassFetcher` | Не используются | Нет wiring |
| `src/exchange/bingx_trader.py` | Отсутствует | Auto-trader import fallback |
| `EventFactory.create_qualified_event/scored_event/signaled_event` | `NotImplementedError` | Абстракция обещает больше, чем реализует |
| `PipelineStageOutcomeTracker` | No-op | `pass` |
| `EventFactory` alias | `EventFactory = EventFactory` | Бессмысленный алиас |
| `src/core` | Малый пакет логирования | Нормальный, но окружён мусором |
| `format_lw001_telegram_message` | Дублирует пороги | Нет red-condition строки |
| `LW001_METRIC_SPEC.check_all_conditions` | Неполная проверка | Нет red candle |

## 13. Подтверждённые проблемы по приоритетам

### P0 — блокируют реальный end-to-end запуск

1. **WS-протокол BingX неверен.** Неверный JSON подписки и topic; официальный формат `reqType/dataType`. Файлы: `websocket_client.py:288-303`, `:396-409`; документация BingX.
2. **WS не потребляется.** `BingXDataProvider.stream()` не вызывается; lifecycle только подписывает имена. Файлы: `lifecycle.py:176-195`, `bingx_provider.py:296-333`.
3. **Callback-контракт неверен.** Sync `process_event` оборачивается в `create_task`; в engine передаётся `MarketDataMessage` вместо `MarketEvent`. Файлы: `lifecycle.py:177-179`, `bingx_provider.py:589-599`, `event_engine.py:275-305`, `:352-354`.
4. **Закрытая свеча не проверяется.** Pipeline ставит `confirm=True`; `is_closed` игнорируется. Файлы: `event_pipeline.py:172-180`, `:252-260`, `:455-465`; `lw_001.py:184-186`.
5. **Timeframe mismatch.** `"15m"` vs `"M15"`; `Timeframe(context.timeframe)` может упасть. Файлы: `config.yaml:30`, `models/enums.py:39-48`, `event_pipeline.py:146`, `:237`, `:443`.
6. **Capitulation-монитор неработоспособен.** Гарантированный `TypeError` из-за неверной сигнатуры, `.get` на list/tuple и жёстко all-True результаты; окно истории при этом неявное. Файл: `realtime_capitulation_monitor.py:362-451`; `capitulation_detector.py:206`.
7. **Private BingX signature отсутствует.** `_generate_signature` вызывается, но результат не включается в URL. Файл: `bingx_fetcher.py:97-108`.
8. **Root-монитор запускается только в конкретном окружении.** Импорт-тайм SQLite по `/home/evreconse/...`; systemd-путь совпадает, но переносимость отсутствует. Файлы: `realtime_lw001_monitor.py:42-50`, `:108-123`; `evreconse.service:10-11`.

### P1 — искажают сигналы/доставку/данные

9. **Notification engine сообщает PENDING как успех.** Pipeline не проверяет `DeliveryResult`; worker может упасть. Файлы: `notification_engine.py:194-221`, `:241-290`; `event_pipeline.py:367-376`.
10. **Очередь не соблюдает приоритет.** `_insert_sorted` всегда вставляет в 0. Файл: `queue.py:151-158`.
11. **Конфиг очереди/rate limit игнорируется.** Созданные queue/limiter выбрасываются; engine использует 10000/10 rps. Файлы: `bootstrap.py:215-227`, `notification_engine.py:52-80`.
12. **Дедупликация storage не работает.** Нет `exists_by_symbol_timestamp` у репозитория. Файл: `storage_engine.py:120-137`.
13. **Rejected events сохраняются как qualified.** Pipeline storage вызывает `ME.qualified` для любого `strategy_id`. Файл: `event_pipeline.py:455-469`.
14. **Universe пуст первые 24 часа.** `initialize()` не вызывает `refresh()`, auto-refresh сначала спит. Файлы: `universe_provider.py:137-169`, `:252+`.
15. **Universe cache TTL не enforced.** `get_active_universe()` возвращает stale; `cache_db_path`/`fallback_file` конструктора игнорируются. Файлы: `universe_provider.py:120-129`, `cmc_universe_cache.py:48-56`, `:216-229`.
16. **Scoring не влияет на отправку.** `min_confidence_score=80` не проверяется notifier’ом; `LW001Strategy.final_score=0`. Файлы: `event_pipeline.py:267-288`, `:326-376`; `lw_001.py:239-243`.
17. **Config mapping теряет значения.** risk/storage/reconnect/scoring/CMC; см. таблицу 9.2. Файлы: `config_manager.py:315-404`.
18. **Outcome tracking не подключён.** `PipelineStageOutcomeTracker` — `pass`; TP/SL не мониторится. Файл: `event_pipeline.py:401-405`.
19. **`run.py` не работает.** `sys.exit(main())` на async main. Файл: `run.py:14-17`.
20. **`--testnet` игнорируется.** CLI-флаг не передаётся в bootstrap. Файл: `src/main.py:53-56`, `:79-83`.
21. **Ошибки main не логируются.** Широкий `except Exception: return 1`. Файл: `src/main.py:122-123`.
22. **Health endpoint без auth на `0.0.0.0:8080`.** Отдаёт статусы компонентов. Файлы: `application.py:305-367`, `src/main.py:108-109`. Это не критичная утечка, но unnecessary exposure.

### P2 — качество, сопровождение, документация

23. **Capitulation unit tests — no-op.** `run_unit_tests()` всегда True. Файл: `capitulation_detector.py:234-317`.
24. **`LW001_METRIC_SPEC.check_all_conditions` не проверяет red candle.** Файл: `LW001_METRIC_SPEC.py:249-320`.
25. **Три копии LW-001 и устаревший fixed-монитор.** См. 7.2.
26. **Formatter не выводит red condition.** `lw001_canonical.py:198-204`.
27. **Документация устарела.** SETUP описывает Bybit/Python 3.12/requirements.txt; README — Foundation Stage и отсутствующий `configs/`.
28. **Tracked junk и 85 data-артефактов.** См. 3.3/10.2.
29. **`requirements.txt` UTF-16 и stale.** См. 9.3.
30. **CI не покрывает root-скрипты и интеграции.** См. 11.3.
31. **`EventFactory` transition methods не реализованы.** `event_factory.py:75-104`.
32. **`FileStorageRepository.close()` не сбрасывает `_initialized`.** `file_repository.py:523-526`.
33. **`NotificationQueue.close/remove` может упасть.** `notify_all` без lock; см. `queue.py:240+`.
34. **`realtime_lw001_monitor.py` создаёт fetcher на символ.** Нет переиспользования сессии; риск rate limit. `:375-378`.
35. **`BingXFetcher.get_balance/order_status` double-unwrap.** `:286-296`, `:315`, `:340-345`.

## 14. Что реализовано, что частично, что запланировано

### Реализовано

- LW-001 canonical qualification (6 условий, red candle, фиксированные пороги).
- LW-001 unit-тесты и scoring-тесты.
- Модели `MarketEvent`/`Enums`/ID и базовая state machine.
- Конфиг-загрузчик YAML/.env/ENV с валидацией.
- DI-контейнер, bootstrap, lifecycle-переходы (в тестах).
- Файловое JSON-хранилище с atomic write.
- Telegram service/formatter/queue/retry как отдельные классы.
- CI-пайплайн и успешная публикация.
- Root-монитор LW-001 как отдельный исполняемый сценарий (не live-проверен).

### Частично

- BingX REST market data: код есть, но private auth, сессии и обработка ответов дефектны.
- WebSocket: клиент и reconnect-стратегия есть, но протокол/фильтр/callback/consumer не сходятся.
- Event pipeline: стадии есть, но реальный вход и closed-candle safety отсутствуют.
- Notification: отправка кода есть, но результат доставки не подтверждается.
- Storage: запись есть, дедупликация и корректный status отсутствуют.
- Scoring: расчёт есть, но не гейтит сигнал.
- Universe: фильтры есть, но первый refresh/TTL/пути не работают как заявлено.
- Outcome: класс есть, pipeline не вызывает.
- Capitulation: формулы есть, интеграции и рабочий запуск отсутствуют.
- Документация: частично актуальна, частично описывает Bybit/старую структуру.

### Запланировано/отсутствует

- `src.exchange.bingx_trader` и auto-trading.
- Полноценный CMC/CoinGlass pipeline.
- EventFactory transition methods.
- Production-grade delivery confirmation/outbox.
- Integration/e2e тесты и contract tests.
- Реальный deployment/runbook и проверка systemd.
- Нормальная упаковка/CLI (`[project.scripts]`).
- Очистка tracked junk и старых research-артефактов.

## 15. Приоритетный план исправлений

### Этап 0 — предохранители (до любых live-сигналов)

1. Остановить реальную отправку сигналов/торговлю; перевести root-монитор в dry-run/paper.
2. Зафиксировать в README, что текущий `src`-pipeline не является рабочим.
3. Не менять LW-001-пороги «для улучшения аудита»; все изменения — отдельными коммитами с тестами.

### Этап 1 — восстановить поток данных

1. Привести WS-подписку к формату BingX:
   - `{"id": "...", "reqType": "sub", "dataType": "SYMBOL@kline_15m"}`;
   - endpoint оставить/сверить с документацией;
   - обрабатывать `dataType`, `data`/`k`.
2. Сделать единый async consumer `stream()` и запустить его из lifecycle; не дублировать `connect`/`reconnect`-логику.
3. Исправить callback-контракт: либо callback async и принимает `MarketEvent`, либо `process_event` принимает `MarketDataMessage` и сам создаёт `MarketEvent`; нельзя `create_task` на sync-функции.
4. Добавить проверку `is_closed`/`confirm` внутри pipeline; не ставить `confirm=True` безусловно.
5. Нормализовать timeframe: `15m ↔ M15` в одном месте; тест на конфиг.
6. Исправить health-monitor: reconnect при `_last_ws_message is None`, не отменять собственную task.
7. Добавить integration-тест с записанным BingX WS payload (fixture) без live-сети.

### Этап 2 — private API и уведомления

1. Включить `signature` в query/URL private-запросов; проверить на testnet/paper.
2. Исправить двойную распаковку `get_balance`/`get_order_status`/`wait_for_order_fill`.
3. Переиспользовать `aiohttp.ClientSession`; добавить rate limiter на уровне fetcher.
4. Сделать `NotificationEngine.send()` возвращающим реальный результат или явно асинхронным с correlation id; pipeline не должен логировать success до доставки.
5. Починить очередь: priority sort, корректный `notify_all` под lock, учитывать config queue size/rate limit.
6. Добавить тесты: mock Telegram API, ошибка/retry/rate limit.

### Этап 3 — данные, конфиг, storage

1. Исправить mapping YAML: risk/storage/reconnect/scoring/notification/CMC.
2. Убрать `"normal"` из `default_priority` или привести тип.
3. Вызывать `refresh()` в `initialize()` (с fallback) и проверять TTL.
4. Прокинуть `cache_db_path`/`fallback_file` в `CMCUniverseCache`; создавать `data/`.
5. Реализовать `exists_by_symbol_timestamp` или явную dedup-таблицу; не сохранять rejected как qualified.
6. Подключить `OutcomeTracker` к фоновому мониторингу цен.
7. Добавить тесты storage/repository/universe.

### Этап 4 — Capitulation и root-мониторы

1. Исправить `get_last_completed_candle(candles, now_ms)`.
2. Сделать окно истории явным: не менее 31 завершённой M15-свечи (лучше 100+), не полагаться на неявные 500; валидировать `candle_index`.
3. Заменить `pass`-тесты на реальные assertions.
4. Привести формат/пороги к одному источнику; не дублировать в мониторе.
5. Определить, является ли Capitulation отдельной стратегией или частью LW-001; сейчас это отдельный неинтегрированный модуль.
6. Убрать/пометить `realtime_lw001_monitor_fixed.py`.

### Этап 5 — упаковка, CI и гигиена

1. Удалить tracked `.devin`, `.codeium`, `Microsoft Office`, `Default Project`, старые `data/*.json` (или перенести в fixtures).
2. Разделить `src` и `scripts/`; root research-скрипты убрать из production-пути.
3. Добавить `[project.scripts]` и рабочий `run.py`.
4. Расширить CI: Python 3.11/3.12, `ruff`/`mypy`/`compileall` для root entry points, integration fixtures, coverage threshold, secret scan.
5. Обновить README/SETUP: BingX, Python 3.11+, `pip install -e ".[dev]"`, реальные entry points, dry-run.
6. Убрать health bind `0.0.0.0` или добавить auth/сетевую политику.

### Критерии готовности к live

- WS fixture-тест и реальная проверка на testnet: сообщение доходит до canonical check.
- Закрытая свеча обязательна; частичная свеча не создаёт событие.
- Private API подпись проверена на testnet; баланс/ордер читаются.
- Telegram delivery подтверждён; ошибки не теряются; дубликаты не отправляются.
- Dedup storage/root SQLite работает при рестарте.
- Universe прогрет; пустой universe не приводит к «тихому» простою.
- Capitulation либо работает, либо явно отключён.
- CI покрывает entry points и интеграционные фикстуры.
- Live-проверки оформлены отдельным отчётом; этот аудит не считается live-подтверждением.

## 16. Итог

Публикация `origin/main` выполнена корректно с точки зрения Git: ветка указывает на проверенный commit, CI зелёный, известные секреты не обнаружены, отчёт добавлен отдельно. Но **код не готов к production**:

- основной `src`-конвейер не имеет рабочего входа рыночных данных;
- root LW-001-монитор является отдельной системой с жёсткой привязкой к окружению и не проверен live;
- Capitulation-монитор неработоспособен;
- private BingX API не аутентифицируется;
- notification/storage/scoring/outcome содержат подтверждённые дефекты, которые могут давать ложные «успехи» и искажать данные.

До исправлений P0 и P1 реальную отправку сигналов и автоторговлю включать нельзя. Этот документ фиксирует состояние опубликованного кода, а не обещание его production-готовности.

---

**Проверенный код:** `bfb11f0210eaf6309a5a5d1eeb3267d5b0c53868`  
**Отчёт опубликован отдельным коммитом после проверенного состояния.**  
**Live-интеграции BingX/Telegram/CMC/CoinGlass не проверялись.**

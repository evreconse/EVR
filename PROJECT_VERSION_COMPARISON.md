# EVRECONSE — сравнение production и GitHub по версиям

**Дата этапа 2:** 2026-10-23
**Репозиторий:** `https://github.com/evreconse/EVR`
**Ветка:** `main`
**GitHub HEAD на начало этапа:** `907354b2473e557c52e40372ba189df1a48170ae`
**Production entry point:** `/home/evreconse/realtime_capitulation_monitor_fixed.py`
**Режим доступа к production:** строго read-only
**Итоговый статус этапа 2:** **B. АЛГОРИТМИЧЕСКАЯ ЭКВИВАЛЕНТНОСТЬ ПОДТВЕРЖДЕНА, НО ОСТАЛИСЬ ФАЙЛОВЫЕ РАЗЛИЧИЯ**

Документ описывает результаты повторной сверки в новом clone GitHub. Прежние
локальные копии не использовались как источник истины: серверные файлы были
заново прочитаны по SFTP, хэши пересчитаны, import graph построен по AST.

---

## 1. Три состояния, которые нельзя смешивать

| Состояние | Что проверено | Что доказано |
|---|---|---|
| **Файлы на диске production** | SHA-256, размеры, mtime; SFTP-копии сверены с серверными хэшами | Содержимое файлов на диске сервера |
| **Код в памяти процесса** | `MainPID`, время старта, mtime файлов, `apply_fix.py` | Побайтовая память **не доказана**: процесс не перезапускался и не отлаживался |
| **GitHub `main`** | Новый clone, `git ls-remote`, commit после публикации | Опубликованное содержимое GitHub |

Процесс:

```text
Unit:               evreconse.service
ActiveState:        active
SubState:           running
MainPID:            880596
Started:            2026-10-17 08:02:29 UTC
NRestarts:          0
ExecStart:          /usr/bin/python3 /home/evreconse/realtime_capitulation_monitor_fixed.py
WorkingDirectory:   /home/evreconse
User:               evreconse
Interpreter:        /usr/bin/python3.11 (Python 3.11.13)
```

`realtime_capitulation_monitor_fixed.py` имеет mtime `2026-10-17 18:45:03 UTC`,
то есть позже старта. Рядом лежит `apply_fix.py` (mtime `18:45:02 UTC`), который
делает только две stats/diagnostic замены: текст причины отказа и распределение
счётчиков `FILTERED_*`. Пороги, формулы, red-candle, history, dedup и Telegram
flow не менялись. Поэтому работающий процесс **алгоритмически** соответствует
текущему файлу, но его память не является доказанно побайтовой копией.

---

## 2. Как определялся active path

Был построен статический import graph от
`realtime_capitulation_monitor_fixed.py` с учётом:

- imports внутри функций;
- package `__init__.py`;
- относительных imports;
- `src.*` и top-level `config`.

Graph содержит **36 локальных модулей**. Они делятся на две группы:

1. **Decision / import path (11 файлов)** — реально участвуют в решении или
   обязательны для его импорта: monitor, detector, thresholds, fetcher, rate
   limiter, universe provider, cache и package `__init__` модули.
2. **Import-time only (25 файлов)** — загружаются через `__init__.py`
   (`src.data_provider`, `src.strategy`, `src.core`, `src.models`), но их
   функции не вызываются в Capitulation decision path. Это, в частности,
   legacy LW-001, WebSocket/REST-клиенты и модели приложения.

Дополнительно проверен `src/exchange/bingx_endpoints.py`: он не импортируется
active monitor, но относится к exchange-модулю и указан в задании.

### 2.1. Разрешение `config` в active process

На production detector делает:

```python
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from config.capitulation_thresholds import CAPITULATION_THRESHOLDS
```

Поэтому в fresh процессе побеждает **top-level** `/home/evreconse/config`, а не
`src/config`. В GitHub теперь добавлен точный top-level `config/`; тест
`tests/test_production_source_sync.py` в отдельном интерпретаторе проверяет, что
active detector разрешает именно его. `src/config` остаётся полноценным
application-пакетом для `src/main.py`, bootstrap и тестов; в active monitor он
не участвует.

---

## 3. Файлы active path, синхронизированные побайтово

Полные SHA-256; `server = GitHub` для каждой строки.

| Файл | SHA-256 | Роль |
|---|---|---|
| `realtime_capitulation_monitor_fixed.py` | `f661e3796f9285dc3fc592714bc980d7734ec8dae61b6dcbd2863083d3de8204` | entry point, final gate, dedup, Telegram |
| `config/__init__.py` | `35e3ae3fd2851525ecf6741ab834a63fcc6b722ca40b95f62ffd955035561b23` | production config package init |
| `config/capitulation_thresholds.py` | `bc51b6972d243bb18eee1165579b18899597cd9b67d423dae0017bb0e62a0b5e` | thresholds |
| `src/config/capitulation_thresholds.py` | `bc51b6972d243bb18eee1165579b18899597cd9b67d423dae0017bb0e62a0b5e` | тот же thresholds для app/tests |
| `src/strategy/__init__.py` | `db6101ff709de19a0d3d2ccb3e671c926259eacb5f607004bf885ff7cb6e9d8d` | strategy package init |
| `src/strategy/capitulation_detector.py` | `3b239a003ee20873178ae2e0aad15784556658fb5b343bc98e4d1e843ace0539` | формулы и `result.qualified` |
| `src/exchange/__init__.py` | `eb8ea474128749befcd3d052499ae3b1504c226edf7c746217dd4b2931acffd5` | exchange package init |
| `src/exchange/bingx_fetcher.py` | `89369399e2521a8fa0e9b3aaf6faba05221e7d1090660bccc13e122050c6a14d` | klines/contracts |
| `src/exchange/bingx_rate_limiter.py` | `bd77f0516baf1bb4f058f5b88f857d5b015cf8fc32334d9ec30cf20cdfd5c3a6` | rate limiter |
| `src/exchange/bingx_endpoints.py` | `cdc63bc050cf58f23aeb692b8f1dc18962ded5f58e3cfdc622c534eeafc7405a` | endpoints (не импортируется monitor) |
| `src/data_provider/__init__.py` | `2039e99ffed561d8414b6eb16df914d7115c8de7a050b9b939fdc0c06949ba56` | data provider package init |
| `src/data_provider/universe_provider.py` | `9ca77e0b80b4f8859b57163324c8cf0ce7a831ed1e0112cf49c4d06ed2f0c0aa` | universe |
| `src/data_provider/cmc_universe_cache.py` | `da46289b9eb1880091e56fa1d88f43ebb56234c2fe02d6dac1067de34fad58d3` | SQLite cache |
| `evreconse.service` | `adc9201cca8a299c3da4aa7b70ddbf1efe5eb70f62eb5969844e23ed8c14e51c` | production unit, без секретов |
| `requirements-production-freeze.txt` | `6e638060c003708658e1e10ca9ed020df24ca9324277dc6e18412aa2a04ad41e` | точный server freeze |

`evreconse.service` опубликован точной копией production unit: в нём нет
секретов, только `PYTHONUNBUFFERED=1` и стандартные пути. `.env` не читался и
не публиковался.

`requirements-production-freeze.txt` — точная ASCII-копия серверного
`requirements.txt`; GitHub `requirements.txt` сохранён как development manifest,
потому что он в UTF-16/CRLF и содержит другие pin-ы (см. §7).

---

## 4. Оставшиеся различия внутри import graph (25 файлов)

Все эти файлы загружаются при старте, но **не участвуют в расчёте
Capitulation-сигнала**. Они не синхронизированы, потому что их точная замена
затронула бы application/legacy-поведение, тесты и структуру пакетов, а не
active signal path. Это осознанное ограничение, а не «совпадение».

| Модуль | SHA-256 server | SHA-256 GitHub | Почему загружается | Влияние |
|---|---|---|---|---|
| `src.core` | `cb0962b50566c1f7417ceb4c48571806ccadd27298a81e4481f3cfd2a2028b5b` | `944fd63ddbaa84b48a574281ef913ffcff9919d85759de6eb658da62154c92b3` | package init | app logging/core; не вызывается monitor |
| `src.core.logging` | `2b40bdcb5a021d9d4840d2c1dd60374ab9e522402ad248b386c9745f8b123fac` | `90a6fa512abc2c33d2a6e88cc8a0e658792b37fb50ba990aaf5bbbaaa4b1d91e` | import из core | logging side effects; не в signal path |
| `src.data_provider.bingx_provider` | `7c73bdd31d27eeb65639f8f91a64e20f119e75fdb52b4781330fdcf96ff9497b` | `557f457cde70277815d73e81e77d4aab2cd7d565dd2846edbadcb3b76c032d97` | package init | REST/WS provider; monitor не вызывает |
| `src.data_provider.exceptions` | `627ba6c20824f1312353c7c8914abe457c7c7e289ea31bb070e76aa3394f4946` | `0cfec68296fabed9ffeba81a6b4356edbf9d81019984ff114e946934d6b61aba` | package init | типы исключений; не в signal path |
| `src.data_provider.heartbeat` | `be042ca65645b5b3ca541ce730e031e6439fba52bb4b3f0ac50da2026fdfd6c2` | `f9f7a43839de0c3f295152dae34c9f5edd3033b50a1fa73e403dd556d602fe49` | package init | WebSocket heartbeat; не используется |
| `src.data_provider.internal_models` | `3d56778fc04a37079320a8317d6ad9dac6aa273fb6e8210ec93385fc91971d17` | `079e35902eac2a5ac76da9155be5543ac58aacacddb8b0a1f951ec7a3cd25f2b` | package init | модели данных; не нужны Capitulation |
| `src.data_provider.provider` | `1557553523e2ba5ee16ddb932bbe6158d37626e3fa70cea6dcda06bc1b9c36de` | `6090cdc0a42d4e4bfa0f3c13570e20df3e24352a47d2a1c940776c556a1826ff` | package init | ABC provider; не вызывается |
| `src.data_provider.rate_limiter` | `9e1dabe29fdad6924bff585b8ddc740b4bb6f6d37bb6c89fd5ed27da4063601c` | `8f8d67ae8b4f7e8c868702de8ed3b50b47056b4787f802430ee9e8965383afa0` | package init | отдельный provider limiter; monitor использует BingX limiter |
| `src.data_provider.reconnect_strategy` | `5298e7d95c1f3a377ed7162107e79f9d26a9e0b4e0dd183c4c0cb4e5953cf51f` | `93d412edb3da808ac0a008f79375abd91204aaba89188e1554cce10f050f6d15` | package init | reconnect; не используется |
| `src.data_provider.rest_client` | `a5358721af5f32d87a512bacac960bac7f1a6ed9942f7fc00facb47587bb249a` | `b633010211e7ce637dea20749889aa00d749093f2536ee6b04fc2bf94daf88d1` | package init | Bybit-style REST; не используется |
| `src.data_provider.websocket_client` | `a5c7de050bc04a1dbfb1f9fd4062a24b20efb30c5ff3751edebc0cae6eec8653` | `7998b52341a043ea65cc60a656a6cd4272a8196a7e14cfc7ea1110199491599b` | package init | WebSocket; не используется |
| `src.exchange.coinglass_fetcher` | `8f56d8ac6a54858e99b792c22e7c7e93fc841b860da7d377aa337f6235867c11` | `a1d4291e14e97cea716bc88030e489331a9d4940208f8c047cee5785d0a7c50f` | package init exchange | импортируется, но active monitor его не вызывает |
| `src.models` | `1ae4ff58d244f85e2c1dac77033fe50e8317cbf9188ff4e936d02afef335c330` | `ea04ebfc243f6d7be7d18896dc591a9ba02795afe8ec9466e13e3df5445be29a` | import из provider | модели приложения; не в signal path |
| `src.models.enums` | `e3595d4a131bdb9f7d88f3c321e9c3837e57a18fc92f1629a9bb460f643bfeed` | `45c63b9681654add7868ef517d3f9f56487d51da47762822934393c936c1bb3b` | package init models | enum-типы; не в signal path |
| `src.models.exceptions` | `b94070f407886c8f00f1d3a4719012679c416a69dcdf582dc9647d1ba7090d74` | `d241e06b72ba67995f1307551124abffd19e3e7f2213b3268a4a898402a7fcf3` | package init models | типы ошибок; не в signal path |
| `src.models.identifiers` | `4d3641c37e3cdc307d3b57766614e2228652cb07fb5b5b3f1eacb9d6295ec1cd` | `5e9dd0408626b9f01d583bd819a1c2a718791d3dae0a2749775cbd4fa4a54d8c` | package init models | идентификаторы; не в signal path |
| `src.models.market_event` | `9a9f05e4a439aff852ff46f7f3e360742f6e57509c9e3c11fa2527af640e901e` | `28e23ca6df690b681077af8e8b8b2230eb62c168a247bb04d3652b9ecf320abd` | package init models | event-модель; не в signal path |
| `src.models.transition_guard` | `c44e3d413b926dc082db6b0f20bcc395a2363c15ccff7a54bdbb195e519a443f` | `bbad462b15625550dddacf866364bc7b26e7248c1b0aae1f6b7b90e257c89f4b` | package init models | state machine; не в signal path |
| `src.strategy.context` | `01f431c58b35ce80b1cd23b0b1fb144690bb0cf2188a9cd4ee39946236ced92f` | `d8b1ad6772998fb221b4062f4c747139e9a879351d2bc2e537a62cea8ee5a42c` | package init strategy | context для LW-001; не в Capitulation |
| `src.strategy.exceptions` | `1714cfbf69dc2b36fd5ed13c9f60abc0576d4b13df4766da25862a458a789072` | `0d7c7302c5cc8f01cae1f3ef470ac257b7e1e4b1ea3614e6adb57cc76dbc9b51` | package init strategy | ошибки стратегий; не в signal path |
| `src.strategy.lw001_canonical` | `793496663f581ae528d06aecacf6b06a27ff229cb4fbc40ffa0a6698053999e2` | `8af637514c884e40e8da327fdf84bb02d75bbc5a38c81acb38dd7d018c49f8d6` | import из lw_001 | LW-001 formulas; inactive |
| `src.strategy.lw_001` | `fe9a1e6ec2205ce4f304898ad88b66a99877697d27d1e2d82653724d98fc4cfc` | `411c5f1b2ce4ad425a79aadfc0a40e664e0ab5ddfde809329bc8e7acd3d03899` | package init strategy | LW-001 class; inactive |
| `src.strategy.registry` | `49c236a322233dc56359a9471aed12f581780668986209f9f1ce158a4568bf0b` | `707cb7165d9a827497473d9efe7b115fc298fa91aea6ffe9a909373a9ca6683b` | package init strategy | registry; не вызывается monitor |
| `src.strategy.strategy` | `069fb763329cf0b4f1e6bc1dbd80ae9179a6c484afaaae3b908abc7e6eab3e16` | `0fb084ef771cbc81eea4a305d9d6c9204aa02582d81d4c41552e4e3ef1f809c3` | package init strategy | базовый Strategy; не в Capitulation |
| `src.strategy.strategy_engine` | `30d9ce05a3865b6e0db8299766a2590e348214f4ddb2a0a0633ed592d48c89b4` | `51dad1ca72c8be3f558e5f100d82ba4af34e53576510bbf21e03cdd592e819a1` | package init strategy | engine; не вызывается monitor |

Важно: часть этих файлов имеет не только formatting/typing, но и реальные
API-отличия (например, `provider.py`, `models/exceptions.py`, `lw_001.py`).
Именно поэтому они **не** заменялись «на глаз»: это изменило бы поведение
application/legacy-кода, хотя и не current Capitulation signal.

---

## 5. Различия вне active import graph

| Файл | SHA-256 server | SHA-256 GitHub | Статус / влияние |
|---|---|---|---|
| `src/config/__init__.py` | server `config/__init__.py`: `35e3ae3fd2851525ecf6741ab834a63fcc6b722ca40b95f62ffd955035561b23` | `ed5ac8f174151e954e0ecc32ef129e64543a9af9995a74ba9817434d29823b75` | application config package; active monitor использует top-level `config` |
| `requirements.txt` | `6e638060c003708658e1e10ca9ed020df24ca9324277dc6e18412aa2a04ad41e` (server freeze) | `3631ae899a523e0b7c07c46f8dbe4155e8483c399ccc284d92a31cbbd0738abf` | dev manifest; точный freeze добавлен отдельным файлом |
| `LW001_METRIC_SPEC.py` | `3926898d46477ed94fe9362c1b709ef2722a608c38a1adf25a89b78d5e3c3e18` | `bd5ecc63cad03d229b298152e0662021046911ff50a1eca1d64cd1d4958f309f` | LW-001 inactive |
| `realtime_lw001_monitor.py` | `df9331d7b64ada4cc47c510889b9af4c9e028677f22efcb52b8541ea2a6112fb` | `df9331d7b64ada4cc47c510889b9af4c9e028677f22efcb52b8541ea2a6112fb` | inactive, совпадает |
| `src/exchange/coinmarketcap_fetcher.py` | `d77213dc7bcd5a7ac3577e9539552b9f6148cf658ca3b9bbfc0088d7ef13fb32` | `298d2dd20632bcd95469651f7d04afc9c9d1c43eeb380ac3080c301aaebcbdc7` | не используется active monitor |
| `realtime_capitulation_monitor.py` | на сервере отсутствует | `f67aa1e44fdf684e344d60436eab2ea55a7df3078b2d7dc8bd3b3b88b24aaeb2` | GitHub legacy shim, не production entry point |
| `pyproject.toml` | server-файл пустой | project manifest | на сервере не используется |
| `.env`, `sent_signals.db`, `cmc_universe.db`, логи | не публикуются | отсутствуют | runtime-секреты/данные |

Runtime-базы и логи не копировались. Их содержимое не является исходным кодом и
не должно попадать в GitHub. Метаданные БД использовались только для
эксплуатационного вывода о stale universe.

---

## 6. Работающий процесс: доказанное и предположения

### 6.1. Доказано

- процесс `880596` запущен `2026-10-17 08:02:29 UTC`, `NRestarts=0`;
- active unit — `evreconse.service`, entry point — Capitulation monitor;
- monitor на диске имеет mtime `2026-10-17 18:45:03 UTC`;
- `apply_fix.py` содержит только stats/diagnostic замены, без порогов,
  формул, dedup, red-candle и Telegram;
- все остальные ключевые active-модули имеют mtime раньше старта процесса;
- текущий файл monitor на диске и в GitHub побайтово совпадают;
- detector/config/fetcher/limiter/universe/cache и package init на диске и в
  GitHub теперь побайтово совпадают.

### 6.2. Не доказано

- что в памяти процесса находится ровно текущий файл monitor;
- что в памяти загружены именно текущие версии всех import-time modules;
- что stats/diagnostic правка была единственной, если не считать mtime и
  содержимого `apply_fix.py` (других следов не найдено).

Для доказательства памяти потребовался бы дамп/отладка или restart. И то, и
другое запрещено условиями задачи. Поэтому статус — **B**, а не A.

---

## 7. Dependency и runtime environment

Сервер:

```text
Interpreter: /usr/bin/python3.11
Version:     Python 3.11.13
Freeze:      50 packages, ASCII, SHA-256 6e638060…
```

GitHub `requirements.txt`: те же 50 имён, но UTF-16/CRLF и три отличия:

| Пакет | Server | GitHub dev manifest |
|---|---:|---:|
| `aiohappyeyeballs` | 2.6.1 | 2.7.1 |
| `aiohttp` | 3.9.5 | 3.14.3 |
| `numpy` | 1.26.4 | 2.5.1 |

Точный server freeze опубликован как `requirements-production-freeze.txt`.
`requirements.txt` и `pyproject.toml` не переписаны, потому что:

- `pyproject.toml` требует `aiohttp>=3.14.0`, что конфликтует с server pin
  3.9.5;
- серверный freeze включает dev/test/OS-пакеты и не является декларацией
  зависимостей проекта;
- замена pin-ов без отдельного тестирования изменила бы dev-окружение, а не
  алгоритм.

Точное воспроизведение окружения зависит от Debian/system Python 3.11.13 и
системных пакетов; на другой ОС оно не гарантируется. Для pure-Python формул
Capitulation это не является алгоритмическим различием.

Systemd unit опубликован точной копией: `StartLimitIntervalSec=0`,
`StartLimitBurst=0`, `Restart=always`, `RestartSec=15`, `User=evreconse`,
`WorkingDirectory=/home/evreconse`, `Environment=PYTHONUNBUFFERED=1`. Секретов в
unit нет.

---

## 8. Повторная проверка сигнального пути

### 8.1. Фактический финальный gate

`verify_signal_comprehensive()`:

```text
timestamp <= 0?                 -> Invalid timestamp
close >= open?                  -> Candle is not red
len(prev_30_volumes) < 30?      -> Insufficient history for Volume30
detector metrics                -> check_thresholds(FIXED_THRESHOLDS)
```

`check_thresholds()`:

```python
drop_pct        = metrics.open_to_low_pct <= -5.0
wick_body_ratio = metrics.lw_body_ratio >= 1.0
reclaim_pct     = metrics.reclaim_pct >= 30.0
volume_30_ratio = metrics.volume_30_ratio >= 2.0
passed = all(...)
```

Плюс отдельная проверка `close < open` до detector. Все операторы
включительные. Score-гейта нет.

### 8.2. `result.qualified` vs `check_thresholds()`

Detector вычисляет `result.qualified` по тем же значениям из
`CAPITULATION_THRESHOLDS`. Active monitor **игнорирует** `result.qualified` и
использует `check_thresholds(metrics)`.

- В текущем коде значения совпадают, поэтому решения не расходятся.
- Архитектурно это dual source of truth: если изменить только
  `config/capitulation_thresholds.py`, detector изменится, а production
  monitor — нет. Это documented risk, не исправлялся.
- Реально production signal решают `FIXED_THRESHOLDS` monitor + red-candle
  check.

### 8.3. Synthetic evidence

- 5 007 одинаковых кейсов: server и GitHub detector загружены **полным**
  import path (top-level `config`, `src.strategy`), JSON с `qualified`,
  `failed_conditions` и всеми `metrics` совпал побайтово:
  `793afcd9c37bf9f38347e45bdc4a2d1bb00b46939c09f8e90c8f25762e2a4069`.
- 5 000 случайных свечей + границы + нулевые body/range/open + зелёная свеча:
  detector и monitor gate совпали (`tests/test_monitor_threshold_equivalence.py`).
- 152 теста проходят, включая 18 server-sync regression tests, 3 equivalence
  tests и 16 source-hash/resolution tests.

### 8.4. Что ещё проверено в пути

- `get_klines()`: `limit=500`, `endTime`; `startTime` не фильтрует выдачу,
  возвращается до 500 последних M15-свечей, не строго 4 часа.
- Явной сортировки нет; используется порядок API + `reversed()`.
- Закрытая свеча: `timestamp + 15min <= now_ms`, поиск с конца.
- `candle_index < 31` → `insufficient_history` (нужно ≥ 32 свечи).
- Предыдущие 30 объёмов: `candles[index-30:index]`.
- Universe: active snapshot без проверки expiry; fallback только при
  отсутствии active. На сервере snapshot stale (2026-10-08, 574 символа),
  SQLite `root:root 0644`, refresh падает с readonly database.
- Dedup: SQLite `(symbol, candle_timestamp)` primary key; claim `pending`;
  success `sent`; failure `failed` + rollback `DELETE`; pending не
  переотправляется автоматически.
- Telegram: personal + optional channel; success if at least one message;
  chat_id печатается в journald; live send не выполнялся.
- Ошибки: rate limit / offline / network / other; per-symbol isolation;
  `asyncio.Semaphore(10)`; monitor не останавливается из-за одного символа.
- `get_last_completed_candle` определён дважды с идентичным телом; второе
  определение перекрывает первое, поведение не меняется.

---

## 9. Проверки и ограничения

| Проверка | Результат |
|---|---|
| `pytest -q` | **152 passed** |
| `pytest -q tests/test_production_source_sync.py` | **16 passed** |
| `pytest -q tests/test_server_sync_algorithms.py` | **18 passed** |
| `pytest -q tests/test_monitor_threshold_equivalence.py` | **3 passed** |
| `ruff check src tests config` | **All checks passed** |
| `mypy src` | **Success: no issues found in 96 source files** |
| Compile/import active modules | **OK** |
| Server-vs-GitHub synthetic comparison | **5 007 / 5 007 identical** |

Ограничения:

1. Работающий процесс не перезапускался; memory bytes не доказаны.
2. 25 import-time modules не синхронизированы (см. §4).
3. `src/config` application package отличается от production top-level
   `config`; active monitor использует top-level exact.
4. `requirements.txt` dev manifest не совпадает с server freeze; exact freeze
   опубликован отдельно.
5. Live Telegram, private BingX, CMC и CoinGlass не вызывались.
6. Universe stale и root-owned SQLite — эксплуатационный риск, не изменялся.
7. В `.service` и документации нет секретов; `.env`, БД и логи не публиковались.

---

## 10. Итог

**B. АЛГОРИТМИЧЕСКАЯ ЭКВИВАЛЕНТНОСТЬ ПОДТВЕРЖДЕНА, НО ОСТАЛИСЬ ФАЙЛОВЫЕ
РАЗЛИЧИЯ.**

Все файлы, которые реально определяют Capitulation/Absorption signal, и
package init, необходимые для их импорта, теперь побайтово совпадают с
production. Формулы, пороги, операторы, closed-candle, median30, red-candle,
dedup, Telegram и error handling проверены. Оставшиеся различия относятся к
import-time-only application/legacy-модулям, `src/config` layout, dev
requirements и не влияют на current signal. Побайтовая память работающего
процесса не доказана, production не изменялся.

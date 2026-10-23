# EVRECONSE — проверка синхронизации GitHub с production-сервером

**Дата проверки:** 2026-10-22
**Репозиторий:** `https://github.com/evreconse/EVR`
**Ветка:** `main`

**GitHub HEAD до синхронизации:**
`21fc7fde3c605336bc5c4acf601de7660b2398c8` (`21fc7fd`)

**Коммит синхронизации:** `c6d00fa9623b83234c1674b8bf9bbbfe96500d96`

**Проверенный HEAD на начало финального аудита:**
`3581bb24bd6bcbf00958b674b865cfa0e978125f` (docs-only follow-up)

**Публикация audit report:**
`3b85cab990772aef1132c5c41d6d3697d48c4918` (docs-only audit commit)

**Финальный аудит:** 2026-10-22, отчёт `PROJECT_FINAL_AUDIT.md`.

**Сравнение версий:** `PROJECT_VERSION_COMPARISON.md`

**Активная стратегия:** `STRATEGY_CAPITULATION_ABSORPTION.md`

**Отчёт синхронизации:** `GITHUB_SERVER_SYNC_REPORT.md`

**Production source of truth:** `evreconse.service` →
`/home/evreconse/realtime_capitulation_monitor_fixed.py`

**Режим доступа к серверу:** read-only

> **Stage 2 addendum (2026-10-23).** Выполнена повторная синхронизация в новом
> clone GitHub (`907354b...`): 11 файлов signal decision path и top-level
> `config` теперь побайтово совпадают с production, опубликованы точный
> `evreconse.service` и `requirements-production-freeze.txt`. 25
> import-time-only модулей, `src/config` layout и dev requirements остаются
> файлово отличными. Полный прогон — **152 passed**; `ruff check src tests
> config` — passed; `mypy src/ tests/ --explicit-package-bases` — passed
> (118 files). Работающий процесс не перезапускался. Актуальные детали:
> `PROJECT_VERSION_COMPARISON.md`, `GITHUB_SERVER_SYNC_REPORT.md`,
> `STRATEGY_CAPITULATION_ABSORPTION.md`. Исторические даты и числа ниже
> относятся к предыдущему этапу.

**Локальный рабочий clone:** отдельный clone GitHub, не сервер

Секреты, токены, chat_id, содержимое `.env`, production БД и логи в документе
не воспроизводятся. Реальные торговые, Telegram, private BingX, CMC и
CoinGlass действия не выполнялись.

---

## 1. Метод и границы проверки

Проверка выполнена в следующем порядке:

1. Определён реальный процесс production-сервиса, cwd, пользователь,
   интерпретатор, systemd unit, env source и количество экземпляров.
2. Прочитаны только файлы, импортируемые работающим процессом, и связанные
   конфиги/модули.
3. Сняты read-only снимки выбранных файлов; секреты не копировались.
4. Выполнена сверка с чистым clone GitHub `21fc7fd`.
5. Подготовлен отдельный локальный sync clone.
6. Изменены только необходимые source/config/service/docs/test-файлы.
7. Выполнены локальные тесты, ruff, mypy, compile и secret/artifact checks.
8. Изменения опубликованы отдельным commit в `origin/main`.
9. Опубликованный код проверен в свежем clone после push.

Не выполнялись:

- запись/редактирование на production-сервере;
- restart/reload systemd;
- установка пакетов на сервере;
- изменение `.env`, БД, логов, cron, unit-файлов;
- реальные ордера, Telegram-отправки, private BingX, CMC/CoinGlass запросы.

---

## 2. Production baseline

| Параметр | Значение |
|---|---|
| Unit | `evreconse.service` |
| ExecStart | `/usr/bin/python3 /home/evreconse/realtime_capitulation_monitor_fixed.py` |
| WorkingDirectory | `/home/evreconse` |
| User | `evreconse` |
| Interpreter | `/usr/bin/python3.11` |
| MainPID | `880596` |
| Started | `2026-10-17 08:02:29 UTC` |
| NRestarts | `0` |
| Restart | `always`, `RestartSec=15` |
| Environment | `PYTHONUNBUFFERED=1` |
| Env source | `/home/evreconse/.env` via `load_dotenv()` |
| Active instances | 1 |
| `.git` in project | отсутствует |
| Installed `evreconse` package | отсутствует; используется локальный код |
| User cron | отсутствует |
| Relevant timers | отсутствуют |

### 2.1. Активная и неактивная стратегии

- **Активна:** Capitulation / Absorption, LONG shadow mode.
- **Не активна:** LW-001. Она присутствует в коде, но unit на неё не указывает.

### 2.2. Состояние данных

| Объект | Значение |
|---|---|
| `sent_signals.db` | 663 строки: 468 pending, 195 sent |
| Active universe | 574 символа (snapshot stale) |
| BingX active contracts | 1239 |
| Cache fetched_at | `2026-10-08T09:25:51Z` (~14 дней на момент аудита) |
| Cache id | 5 |

### 2.3. Оговорка о stats-only правке

Процесс запущен в 08:02 UTC, файл monitor имеет mtime 18:45 UTC. Работающий
процесс загрузил версию до `apply_fix.py`. Эта правка меняет только
failure-reason reporting и счётчики `FILTERED_*`/`DROP`; пороги, формулы,
red-candle, candle confirmation, dedup и Telegram-flow не меняются.

В GitHub опубликован текущий файл с этой stats-правкой; сервер не
перезапускался. Это ограничение зафиксировано явно.

---

## 3. GitHub до синхронизации

```text
HEAD:  21fc7fde3c605336bc5c4acf601de7660b2398c8
Tree:  10b0f17b33869f7b4123bd6dea979561a1fa832b
Parent: bfb11f0210eaf6309a5a5d1eeb3267d5b0c53868
Remote: https://github.com/evreconse/EVR.git
```

Существенные расхождения до обновления:

1. `evreconse.service` указывал на LW-001, а production работает на
   Capitulation.
2. Активный `realtime_capitulation_monitor_fixed.py` отсутствовал.
3. `src/strategy/capitulation_detector.py` был старой версией с `-2.5` и
   несовместимым API.
4. `config/capitulation_thresholds.py` отсутствовал.
5. `realtime_lw001_monitor.py`, `LW001_METRIC_SPEC.py`,
   `src/strategy/lw001_canonical.py`, `src/strategy/lw_001.py` содержали
   устаревший `-2.5`.
6. Серверные `bingx_rate_limiter.py` и `bingx_endpoints.py` отсутствовали.
7. `bingx_fetcher.py`, `universe_provider.py`, `cmc_universe_cache.py` были
   существенно старее серверных.
8. `realtime_capitulation_monitor.py` был старым и несовместимым с новым
   detector API.
9. Не было regression-тестов на серверные формулы/пороги.

---

## 4. Компонентная таблица

Хэши указаны как SHA-256 (сокращённо — в тексте, полностью — в §5).

| Компонент | Сервер | GitHub до | Действие | GitHub после |
|---|---|---|---|---|
| `realtime_capitulation_monitor_fixed.py` | `f661e379…` | отсутствовал | добавлен | `f661e379…` |
| `src/strategy/capitulation_detector.py` | `3b239a00…` | `c43e87d4…` | заменён | `8e2ff8f6…` |
| `src/config/capitulation_thresholds.py` | `bc51b697…`* | отсутствовал | добавлен | `4a7789ee…` |
| `src/exchange/bingx_fetcher.py` | `89369399…` | `8051d881…` | синхронизирован | `19caf773…` |
| `src/exchange/bingx_rate_limiter.py` | `bd77f051…` | отсутствовал | добавлен | `4f08b318…` |
| `src/exchange/bingx_endpoints.py` | `cdc63bc0…` | отсутствовал | добавлен | `78e28acc…` |
| `src/data_provider/universe_provider.py` | `9ca77e0b…` | `6c8e7d4c…` | синхронизирован | `2744e235…` |
| `src/data_provider/cmc_universe_cache.py` | `da46289b…` | `74aa8825…` | синхронизирован | `56c3eb03…` |
| `realtime_lw001_monitor.py` | `df9331d7…` | `4a665df1…` | `-5.0` | `df9331d7…` |
| `LW001_METRIC_SPEC.py` | `3926898d…` | `2a15609d…` | `-5.0` | `bd5ecc63…` |
| `src/strategy/lw001_canonical.py` | `79349666…` | `d3bf8948…` | `-5.0` | `8af63751…` |
| `src/strategy/lw_001.py` | `fe9a1e6e…` | `ca110131…` | `-5.0` | `411c5f1b…` |
| `evreconse.service` | `/etc/systemd/...` | LW-001 | обновлён | Capitulation |
| `realtime_capitulation_monitor.py` | legacy | старый код | shim | делегирует active |
| `backfill_capitulation_signals.py` | legacy | старый API | адаптирован | новый detector |
| `tests/test_server_sync_algorithms.py` | — | отсутствовал | добавлен | 18 tests |

\* Серверный путь: `/home/evreconse/config/capitulation_thresholds.py`. В GitHub
файл размещён в `src/config/capitulation_thresholds.py`, чтобы не конфликтовать
с существующим package layout. Значения идентичны; форматирование/типизация
нормализованы.

### 4.1. Почему хэши некоторых файлов не совпадают побайтно

Для активного monitor и LW-001 monitor хэши совпадают с сервером. Для detector,
config и I/O-модулей допущены только безопасные адаптации:

- import path под layout GitHub (`config` находится в `src/config`);
- удаление/нормализация trailing whitespace;
- современные type annotations;
- file-level lint/type directives для сохранённых production I/O-модулей;
- удалён недостижимый/сломанный второй `__main__` блок в `cmc_universe_cache`;
- добавлены комментарии о секретах/service.

Ни одна адаптация не меняет пороги, формулы, условия квалификации, dedup или
notifications.

---

## 5. Полные хэши после синхронизации

```text
f661e3796f9285dc3fc592714bc980d7734ec8dae61b6dcbd2863083d3de8204  realtime_capitulation_monitor_fixed.py
8e2ff8f6ef5775df6071617c96ff853fb3084cb73da9bc4ed65356e982a75c89  src/strategy/capitulation_detector.py
4a7789ee20abd8a6d7b3f9e6016f2e8f6ded14bfba3a6ce809d2109d656ff93d  src/config/capitulation_thresholds.py
19caf7730bf484ed337ba120f67e5b2fd70c71ba01c42c1058ed1aee7d2fa0ca  src/exchange/bingx_fetcher.py
4f08b3180bef2068dccfed6bc43f3d58b7dc74fe1ac0980f18985b0aab7867a3  src/exchange/bingx_rate_limiter.py
78e28acc39e1b5f7026a9d3599e57aba8a1e2dc866f59ff5f8425bb45425b047  src/exchange/bingx_endpoints.py
2744e235c7bef4386a492426b367bdff994f210f9e1ba5d3dd49e64f3d34d9a1  src/data_provider/universe_provider.py
56c3eb033ba1d43e1627a02c5414bcb87d94bdcfe55df84264e110860f5553ae  src/data_provider/cmc_universe_cache.py
df9331d7b64ada4cc47c510889b9af4c9e028677f22efcb52b8541ea2a6112fb  realtime_lw001_monitor.py
bd5ecc63cad03d229b298152e0662021046911ff50a1eca1d64cd1d4958f309f  LW001_METRIC_SPEC.py
8af637514c884e40e8da327fdf84bb02d75bbc5a38c81acb38dd7d018c49f8d6  src/strategy/lw001_canonical.py
411c5f1b2ce4ad425a79aadfc0a40e664e0ab5ddfde809329bc8e7acd3d03899  src/strategy/lw_001.py
```

---

## 6. Изменения

### 6.1. Добавлено

- `realtime_capitulation_monitor_fixed.py`;
- `src/config/capitulation_thresholds.py`;
- `src/exchange/bingx_rate_limiter.py`;
- `src/exchange/bingx_endpoints.py`;
- `tests/test_server_sync_algorithms.py`.

### 6.2. Обновлено

- `src/strategy/capitulation_detector.py`;
- `src/exchange/bingx_fetcher.py`;
- `src/data_provider/universe_provider.py`;
- `src/data_provider/cmc_universe_cache.py`;
- `realtime_lw001_monitor.py`;
- `realtime_lw001_monitor_fixed.py`;
- `LW001_METRIC_SPEC.py`;
- `src/strategy/lw001_canonical.py`;
- `src/strategy/lw_001.py`;
- `src/config/types.py`;
- `realtime_capitulation_monitor.py` (legacy shim);
- `backfill_capitulation_signals.py`;
- `evreconse.service`;
- `scripts/replay_4day.py`;
- `README.md`;
- `LW001_PRODUCTION_SPEC.md`;
- `PROJECT_FULL_DOCUMENTATION.md`;
- `PROJECT_VERSION_VERIFICATION.md`.

### 6.3. Не включено

- `.env`, секреты, токены, chat_id;
- production SQLite/БД;
- logs, forensic snapshots, dumps;
- runtime universe cache;
- серверные секретные unit/drop-in/env-файлы;
- сторонние бинарные артефакты.

---

## 7. Соответствие алгоритмов

| Параметр | Сервер | GitHub после | Статус |
|---|---:|---:|---|
| Capitulation red candle | `close < open` | `close < open` | ✅ |
| Capitulation Open→Low | -5.0 | -5.0 | ✅ |
| Capitulation Volume30Ratio | 2.0 | 2.0 | ✅ |
| Capitulation LW/Body | 1.0 | 1.0 | ✅ |
| Capitulation Reclaim | 30.0 | 30.0 | ✅ |
| LW-001 Range | 4.5 | 4.5 | ✅ |
| LW-001 Body | 0.8 | 0.8 | ✅ |
| LW-001 LW/Body | 1.3 | 1.3 | ✅ |
| LW-001 LW/Range | 55.0 | 55.0 | ✅ |
| LW-001 Open→Low | **-5.0** | **-5.0** | ✅ |
| LW-001 volume gate | отсутствует | отсутствует | ✅ |
| LW-001 score gate | отсутствует | отсутствует | ✅ |

Проверки:

- серверные файлы прочитаны read-only;
- значения вынесены в regression tests;
- active monitor hash совпадает с серверным;
- LW-001 monitor hash совпадает с серверным;
- подтверждено, что active monitor выполняет финальную квалификацию через
  собственный `check_thresholds()`/`FIXED_THRESHOLDS`, а не через
  `result.qualified` detector; значения сейчас идентичны;
- тесты не импортируют active monitor целиком; для LW-001 Body, LW/Body и
  LW/Range используются соседние pass/fail значения, а не float-equality на
  точной границе;
- `BingXFetcher.get_klines()` при `limit=500` использует `endTime` и не
  применяет `startTime` как фильтр; фактическая история — до 500 свечей.

---

## 8. Тесты и статические проверки

| Проверка | Команда | Результат |
|---|---|---|
| Все unit/regression tests | `pytest -q` | **136 passed** |
| Только серверная регрессия | `pytest -q tests/test_server_sync_algorithms.py` | **18 passed** |
| Эквивалентность порогов | `pytest -q tests/test_monitor_threshold_equivalence.py` | **3 passed** |
| Ruff | `ruff check src tests LW001_METRIC_SPEC.py` | **All checks passed** |
| Mypy | `mypy src/ tests/ --explicit-package-bases` | **Success: no issues found in 117 source files** |
| Compile | `py_compile` изменённых файлов | **OK** |
| Algorithm imports | `strategy.capitulation_detector`, `config...`, `LW001_METRIC_SPEC` | **OK** |
| Runtime package imports | `src.exchange`, `src.data_provider` | **OK** |

Mypy exclusion: `src/data_provider/universe_provider.py` и
`src/data_provider/cmc_universe_cache.py` исключены из strict module discovery,
так как сохраняют production I/O-реализацию с существующим typing debt. Это
явное ограничение, а не скрытая ошибка.

Не выполнялись production integrations и live-действия.

---

## 9. Проверки перед push

- [x] `git diff` просмотрен;
- [x] нет `.env`/токенов/private keys/chat_id;
- [x] нет production БД/логов/дампов;
- [x] нет случайных артефактов;
- [x] high-confidence secret scan текущего tree — 0 совпадений;
- [x] high-confidence secret scan всей доступной истории на момент проверки
  (22 коммита, 1490 уникальных blob) — 0 совпадений;
- [x] пороги Capitulation совпадают с сервером;
- [x] пороги LW-001 совпадают с сервером;
- [x] unit указывает на активный Capitulation monitor;
- [x] тесты/ruff/mypy/compile проходят;
- [x] production unit не содержит секретов;
- [x] история Git не переписывается.

Push выполняется отдельным commit. При невозможности безопасной
аутентификации публикация останавливается и оформляется как blocker.

---

## 10. Ответы на 10 вопросов

1. **Какой код реально использует сервер?**
   `evreconse.service` → `/usr/bin/python3.11
   /home/evreconse/realtime_capitulation_monitor_fixed.py`, cwd
   `/home/evreconse`, user `evreconse`, env из `.env` через `load_dotenv()`.
   Это Capitulation/Absorption monitor, не LW-001.

2. **Где находятся реальные формулы и пороги LW-001?**
   Формулы и канонические пороги — `/home/evreconse/LW001_METRIC_SPEC.py`;
   adapter — `/home/evreconse/src/strategy/lw001_canonical.py`; legacy strategy —
   `/home/evreconse/src/strategy/lw_001.py`; legacy monitor —
   `/home/evreconse/realtime_lw001_monitor.py`. LW-001 не запущен.

3. **Какие значения отличались от GitHub?**
   Главное: LW-001 `Open→Low` был **-2.5** в GitHub, на сервере **-5.0**.
   Также активный Capitulation detector/monitor/thresholds отсутствовали или
   были старыми; unit указывал на LW-001; серверные I/O-модули отличались.

4. **Какие ещё существенные расхождения?**
   Отсутствовал `realtime_capitulation_monitor_fixed.py`; detector был старой
   архитектуры; отсутствовал config thresholds; отсутствовали rate limiter и
   endpoints; universe/cache/fetcher были старее; старый
   `realtime_capitulation_monitor.py` был несовместим с новым API; unit был
   направлен не на активную стратегию.

5. **Какие файлы обновлены в GitHub?**
   См. §6: добавлены active monitor, config thresholds, rate limiter, endpoints,
   tests; обновлены detector, fetcher, universe/cache, LW-001 files, service,
   README, LW001 spec, backfill, legacy shim и оба обязательных документа.

6. **Какой SHA теперь опубликован?**
   На начало финального аудита remote HEAD —
   `3581bb24bd6bcbf00958b674b865cfa0e978125f`; sync commit —
   `c6d00fa9623b83234c1674b8bf9bbbfe96500d96`; docs-only audit commit —
   `3b85cab990772aef1132c5c41d6d3697d48c4918`. Текущий HEAD после
   metadata-follow-up указан в финальном ответе.

7. **Какие тесты прошли?**
   `pytest -q` — **136 passed**, включая **18** regression tests и **3** теста
   эквивалентности `FIXED_THRESHOLDS`/`check_thresholds`; `ruff` — passed;
   `mypy` — passed (117 source files); `py_compile` — OK; imports — OK.
   Production integrations не запускались.

8. **Подтверждено ли соответствие опубликованного алгоритма серверному?**
   Да для числовых порогов/формул Capitulation и canonical LW-001; значения
   сведены в §7 и проверены тестами. Активный monitor и LW-001 monitor совпадают
   с серверными по SHA-256. Для detector/config/I/O есть только безопасные
   адаптации package layout/форматирования, не меняющие алгоритм. Финальная
   квалификация active monitor использует собственный `FIXED_THRESHOLDS`;
   эквивалентность detector/config проверена отдельным тестом на 5 000
   случайных свечах, границах и вырожденных данных.

9. **Какие расхождения намеренно остались?**
   Секреты, `.env`, БД, логи, runtime cache, серверные абсолютные пути,
   dependency freeze и локальные service-настройки не публикуются. LW-001
   остаётся неактивным. Stats-only fix в активном monitor не был загружен
   процессом, так как сервер не перезапускался. Два server I/O-модуля исключены
   из strict mypy. Universe snapshot был stale (~14 дней); provider не
   проверяет expiry active snapshot перед выдачей, а initialize не делает
   немедленный refresh.

10. **Подтверди, что серверные файлы, конфигурация, службы и Git не
    изменялись.**
    Подтверждено: все действия были read-only. Не было записи файлов,
    изменения `.env`, БД, логов, cron, systemd unit, пакетов, Git; не было
    restart/reload; не выполнялись реальные торговые/Telegram/private
    BingX/CMC/CoinGlass действия. Сервер остался нетронутым.

---

## 11. Остаточные ограничения

1. Нет live-проверки Telegram/BingX private/CMC.
2. Нет production restart, поэтому stats-only fix не загружен процессом.
3. GitHub не содержит runtime БД, universe cache и секретов.
4. Server I/O modules сохраняют production typing debt; два файла исключены из
   strict mypy.
5. Абсолютные production paths в monitor сохранены; для переноса нужен
   deployment-конфиг.
6. LW-001 остаётся legacy и не должен включаться без отдельного решения.
7. Active monitor использует dual-source thresholds: detector/config и
   `FIXED_THRESHOLDS`; сейчас значения совпадают, но автоматической связи нет.
8. Universe provider не проверяет expiry active snapshot; snapshot на момент
   baseline был stale. Причина установлена read-only: `data/cmc_universe.db`
   принадлежит `root:root` (`0644`), процесс `evreconse` не может писать,
   refresh завершается ошибкой `attempt to write a readonly database`.
9. `BingXFetcher.get_klines()` при `limit=500` не применяет `startTime` как
   фильтр; фактическая история — до 500 свечей, а не строго 4 часа.
10. В active monitor дважды определён `get_last_completed_candle`; определения
    идентичны. Legacy LW-001 содержит несовместимый/volume-based код.

---

## 12. Итог

GitHub отражает актуальную серверную реализацию EVRECONSE по активной стратегии
Capitulation/Absorption и по canonical LW-001. Работающий сервер не изменялся.
Публикация выполнена отдельным commit; точный SHA и результат проверки свежего
clone указываются после push. Финальный аудит, найденные ограничения и
непроверенные production-интеграции — в `PROJECT_FINAL_AUDIT.md`.

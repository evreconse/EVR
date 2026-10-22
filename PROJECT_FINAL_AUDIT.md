# EVRECONSE — финальный аудит опубликованной версии

**Дата аудита:** 2026-10-22
**Репозиторий:** `https://github.com/evreconse/EVR`
**Ветка:** `main`
**Проверенный GitHub HEAD на начало аудита:**
`3581bb24bd6bcbf00958b674b865cfa0e978125f`
**Коммит синхронизации:**
`c6d00fa9623b83234c1674b8bf9bbbfe96500d96`
**Предыдущий HEAD:**
`21fc7fde3c605336bc5c4acf601de7660b2398c8`

Аудит выполнен в отдельном полном clone. Production-сервер использовался
только для чтения. Реальные торговые, Telegram, private BingX, CMC и
CoinGlass действия не выполнялись.

---

## 1. Фактическое состояние GitHub

Проверено в свежем clone:

```text
remote: https://github.com/evreconse/EVR.git   # без credentials в URL
HEAD:   3581bb24bd6bcbf00958b674b865cfa0e978125f
branch: main
status: clean
ls-remote origin refs/heads/main:
        3581bb24bd6bcbf00958b674b865cfa0e978125f
```

Оба ожидаемых коммита присутствуют в истории:

- `c6d00fa` — синхронизация кода и документации;
- `3581bb2` — docs-only follow-up с записью SHA синхронизации.

Неожиданных коммитов или изменений remote на момент проверки не обнаружено.
Рабочая директория чистная; проверялся именно опубликованный HEAD, а не старая
локальная копия.

---

## 2. Активный entry point и реальный путь исполнения

### 2.1. Entry point

Production unit `evreconse.service` запускает:

```text
/usr/bin/python3 /home/evreconse/realtime_capitulation_monitor_fixed.py
```

Рабочий каталог — `/home/evreconse`, пользователь — `evreconse`, переменные
окружения читаются через `load_dotenv()` из runtime `.env`. Это
Capitulation/Absorption monitor, **не LW-001**.

В GitHub `evreconse.service` является безопасным шаблоном: он не содержит
токенов, chat_id или иных секретов и не выдаётся за точную копию серверного
unit с локальными настройками.

### 2.2. Подтверждённый поток

```text
main()
  └── UniverseProvider.initialize()
        ├── CMCUniverseCache: active snapshot
        └── auto-refresh task (nominally every 24h)
  └── monitor_symbols()
        └── get_universe()
              └── for each symbol:
                    BingXFetcher.get_klines(interval="15m", limit=500, endTime=now)
                    get_last_completed_candle()
                    require candle_index >= 31 and prior 30 volumes
                    verify_signal_comprehensive()
                      ├── check_red_candle()
                      ├── check_capitulation_signal()   # detector + config metrics
                      └── check_thresholds()            # ACTUAL active pass/fail
                    claim_signal()                      # SQLite atomic dedup
                    send_signal_to_telegram()           # personal + optional channel
                    update status / delete claim on full failure
```

### 2.3. Важное уточнение о порогах активного пути

В active monitor есть **два слоя порогов**:

1. `src/strategy/capitulation_detector.py` читает
   `CAPITULATION_THRESHOLDS` из `src/config/capitulation_thresholds.py` и
   формирует `result.qualified`.
2. `realtime_capitulation_monitor_fixed.py` **не использует**
   `result.qualified` для окончательного решения. Он вызывает
   `check_thresholds(metrics)` с собственным `FIXED_THRESHOLDS`.

Сейчас значения совпадают, поэтому поведение сервера и опубликованного кода
одинаково. Однако это **dual source of truth**: изменение только config
detector не изменит фактическую квалификацию активного monitor. Это
зафиксировано как технический долг, а не исправлялось изменением алгоритма.

---

## 3. Capitulation / Absorption: формулы и пороги

### 3.1. Формулы

```python
range_pct       = (high - low) / open * 100
open_to_low_pct = (low - open) / open * 100
body_pct        = abs(close - open) / open * 100

lower_wick      = min(open, close) - low
lw_body_ratio   = lower_wick / body                    # 0.0 при body == 0
lw_range_pct    = lower_wick / (high - low) * 100      # 0.0 при range <= 0
reclaim_pct     = (close - low) / (high - low) * 100   # 0.0 при range <= 0

volume_30_median = median(previous 30 completed M15 volumes)  # N-30 ... N-1
volume_30_ratio  = volume / volume_30_median                   # 0.0 при median <= 0

is_red = close < open
```

В active detector при `open == 0` процентные метрики возвращают `0.0`, а не
бросают исключение. При нулевом body/range соответствующие ratios равны `0.0`.
Caller отдельно требует не менее 30 предыдущих объёмов и не менее 32 свечей.

### 3.2. Пороги

| Условие | Значение | Оператор |
|---|---:|---|
| Red candle | `close < open` | обязательное |
| Open → Low | **-5.0%** | `<=` |
| Volume30Ratio | **2.0x** | `>=` |
| LW / Body | **1.0x** | `>=` |
| Reclaim from Low | **30.0%** | `>=` |

Все условия объединяются через AND. Отдельного score-гейта нет.

### 3.3. Свеча и данные

- timeframe: **15m**;
- оценивается последняя **закрытая** свеча;
- закрытость: `candle_timestamp + 15 * 60 * 1000 <= now_ms`;
- незакрытая текущая свеча игнорируется;
- требуется `candle_index >= 31`, то есть минимум **32 свечи** в массиве;
- для median30 берутся ровно 30 свечей перед оцениваемой;
- monitor передаёт `start_time = now - 4h`, но `BingXFetcher.get_klines()`
  использует `limit=500` и `endTime`, а `startTime` не применяет как фильтр при
  таком limit. Фактически возвращается до **500** последних M15-свечей, чего
  достаточно для требования 32;
- пустой ответ или `< 2` свечей → `insufficient_candles`;
- нет закрытой свечи → `no_completed_candle`;
- некорректный timestamp (`<= 0`) → `invalid_timestamp`/пропуск;
- обнаружение сигнала и отправка уведомления — разные шаги: сигнал сначала
  проходит qualification, затем атомарно захватывается в SQLite, и только потом
  отправляется в Telegram.

### 3.4. Dedup и уведомления

- SQLite `sent_signals.db`, primary key `(symbol, candle_timestamp)`;
- `claim_signal()` делает `INSERT ... telegram_status='pending'`;
- `sqlite3.IntegrityError` означает, что сигнал уже обрабатывался;
- при успешной отправке статус `sent`, сохраняется `telegram_message_id`;
- при полном failure статус временно `failed`, затем строка **удаляется**
  (`DELETE`), memory-set очищается; сигнал может быть обработан повторно;
- pending-сигналы при старте только перечисляются с сообщением
  `manual intervention needed`; автоматического resend нет;
- получатели: personal chat + optional channel;
- успех, если доставлено хотя бы одно сообщение;
- отдельного Telegram retry-loop нет.

---

## 4. LW-001: canonical-формулы и inactive-статус

LW-001 **не запущен** под production unit. Его код сохранён для совместимости
и исследований.

### 4.1. Canonical qualification

```python
is_red          = close < open
range_pct       = (high - low) / open * 100
body_pct        = abs(close - open) / open * 100
lower_wick      = min(open, close) - low
lw_body_ratio   = lower_wick / body                 # 0.0 при body == 0
lw_range_pct    = lower_wick / (high - low) * 100   # 0.0 при range == 0
open_to_low_pct = (low - open) / open * 100
```

| Условие | Значение | Оператор |
|---|---:|---|
| Range | **4.5%** | `>=` |
| Body | **0.8%** | `>=` |
| LW / Body | **1.3x** | `>=` |
| LW / Range | **55.0%** | `>=` |
| Open → Low | **-5.0%** | `<=` |
| Red candle | `close < open` | обязательное |

Volume Ratio **не участвует** в canonical LW-001. Отдельного score-гейта нет;
`final_score` в legacy strategy носит информационный характер.

В `LW001_METRIC_SPEC.py` функции range/body/open-to-low бросают `ValueError`
при `open == 0`; `lw001_canonical.py` возвращает `0.0` для нулевого open и
ratio `0.0` при нулевых body/range. Это разные API, но LW-001 inactive и не
входит в production-путь.

### 4.2. Inactive/legacy-компоненты

- `realtime_lw001_monitor.py` — legacy monitor; unit на него не указывает;
- `realtime_lw001_monitor_fixed.py` — исторический volume-based entry point;
  содержит старую логику Volume Ratio и вызов несовместимого keyword
  `reference_average_volume`; **не использовать**;
- `src/strategy/lw_001.py` — legacy strategy с информационным score;
- `src/strategy/lw001_canonical.py` и `LW001_METRIC_SPEC.py` — canonical
  adapter/spec для LW-001.
- При старте LW-001 monitor использует 4-часовой `start_time`, но фактический
  fetcher ведёт себя так же, как в active monitor: `limit=500`, `endTime`;
  для LW-001 требуется минимум 2 свечи и `candle_index >= 1`.

---

## 5. Проверки, выполненные локально

Все проверки выполнены в отдельном clone, без production-БД, приватных API и
отправки сообщений.

| Проверка | Команда | Результат |
|---|---|---|
| Все тесты | `pytest -q` | **133 passed** |
| Серверная регрессия | `pytest -q tests/test_server_sync_algorithms.py` | **18 passed** |
| Ruff | `ruff check src tests LW001_METRIC_SPEC.py` | **All checks passed** |
| Mypy | `mypy src/ tests/ --explicit-package-bases` | **Success: no issues found in 116 source files** |
| Compile | `py_compile` ключевых модулей | **OK** |
| Imports | `config`, `strategy`, `LW001_METRIC_SPEC`, `src.exchange`, `src.data_provider` | **OK** |
| Внешний доступ из tests | поиск network/Telegram/DB/private refs | **не обнаружено** |

Mypy сохраняет два server I/O-модуля (`universe_provider.py`,
`cmc_universe_cache.py`) вне strict module discovery из-за существующего
production typing debt. Это ограничение, а не скрытая ошибка.

### 5.1. Ограничения тестов

- Тесты проверяют detector/config и canonical LW-001, но **не импортируют**
  active monitor целиком: его импорт инициализирует production-пути/БД.
- Для active Capitulation точные inclusive-проверки есть для Open→Low,
  Volume и LW/Body; Reclaim проверяется около границы.
- Для LW-001 Range и Open→Low проверяются на точной границе; Body, LW/Body и
  LW/Range — на соседних pass/fail значениях, а не на точном равенстве.
- Это не меняет формулы: включительность следует из операторов `<`/`>`, но
  тесты не доказывают точное равенство для всех float-границ.

---

## 6. Найденные дефекты и их статус

| № | Дефект | Влияние | Статус |
|---|---|---|---|
| 1 | Документация называла detector единственным источником active-порогов | Вводила в заблуждение: active monitor использует собственный `FIXED_THRESHOLDS` | исправлено в документации |
| 2 | Документация говорила о запросе «4 часа истории» | Фактически fetcher возвращает до 500 свечей; `startTime` не фильтрует при limit<1000 | исправлено в документации |
| 3 | Документация говорила о TTL 24h/fallback как о гарантии | Provider возвращает active snapshot без проверки возраста; refresh запускается только через 24h после старта; fallback — только при отсутствии active | исправлено; stale cache зафиксирован как риск |
| 4 | В active monitor дважды определён `get_last_completed_candle` | Оба определения идентичны; поведение не меняется | оставлено как production-совместимый technical debt |
| 5 | Тесты не покрывают active monitor's hardcoded `check_thresholds` | Риск незамеченного расхождения config/monitor | зафиксировано в audit |
| 6 | Legacy LW-001 monitor содержит несовместимый вызов `reference_average_volume` | Соответствующий старый путь неработоспособен | LW-001 inactive; зафиксировано |
| 7 | `realtime_lw001_monitor_fixed.py` сохраняет Volume Ratio | Не соответствует canonical LW-001 | явно помечен как historical/non-canonical |
| 8 | README слишком широко говорил о полной синхронизации | Не отражал stats-only caveat и ограничения | уточнено |

Код алгоритма не изменялся: для исправления перечисленных пунктов достаточно
документации и явных ограничений.

---

## 7. Runtime-риски, не являющиеся ошибками публикации

1. **Stale universe cache.** На момент baseline active snapshot имел
   `fetched_at=2026-10-08T09:25:51Z` (возраст ~14 дней), хотя номинальный
   refresh interval — 24h. Provider не проверяет `is_expired()` перед выдачей
   active snapshot. Причина отсутствия более свежего snapshot по логам не
   устанавливалась; это не проверялось live.
2. **Нет начального refresh.** `initialize()` не вызывает `refresh()`. При
   отсутствии cache universe будет пустым до первого срабатывания фонового
   refresh (через 24h). На production cache существует, но это deployment-risk.
3. **Chat IDs в journald.** Active monitor печатает `chat_id=...` в stdout;
   это не секрет репозитория, но приватные идентификаторы попадают в
   journald. В документации и Git они не публикуются.
4. **Hardcoded paths.** Monitor и cache используют `/home/evreconse/...`;
   перенос требует deployment-конфигурации.
5. **Legacy code.** LW-001 monitor содержит optional demo auto-trader path;
   он не запущен, но не должен включаться без отдельного решения владельца.

---

## 8. Безопасность публикации

Проверены Git-tracked файлы и **вся доступная история на момент сканирования**
(22 коммита, 1490 уникальных blob; включая 14 крупных blobs >4 MB):

| Проверка | Результат |
|---|---|
| API keys / GitHub PAT / AWS keys / private keys в текущем tree | **не найдено** |
| Telegram bot tokens, Slack tokens, URL credentials | **не найдено** |
| `.env`, production SQLite/БД, logs, dumps в текущем tree | **не найдено** |
| Те же high-confidence паттерны в истории | **0 совпадений** |
| Секреты в `*.service`/`*.timer` | **не найдено** |
| Remote URL с credentials | **не найдено** (публичный URL) |

Отдельно проверены исторические `test_telegram_token.py` и его копии: в них
находятся только placeholder-значения (`***REMOVED***`/`YOUR_..._HERE`), а не
действующие токены. `.codeium`/`.devin` — сторонние vendored-артефакты, не
production-код; секретов в них high-confidence сканер не нашёл. Они остаются
техническим мусором, но не являются утечкой. `diagnose_all_sent_signals.py`
совпал по имени с `sent_signals`, но это исторический диагностический скрипт,
а не БД/лог; он содержит старую LW-001-логику и public BingX-вызовы и не
исполнялся. `Default Project/EVRECONSE/historical_signals.json` — tracked
исторический набор сигналов (~19 MB), не `.env`/БД/лог; high-confidence
секретов в нём не найдено. Эти артефакты не удалялись без отдельного решения
владельца.

История не переписывалась, секреты не ротировались, найденные значения не
выводились в отчёт.

---

## 9. Непроверенные production-интеграции

Следующие пункты **не проверялись live** и не должны считаться
подтверждёнными:

- фактическая доставка Telegram и поведение обоих получателей;
- private BingX API, баланс, ордера, позиции;
- CMC/CoinGlass API;
- фактический refresh universe и причина stale cache;
- restart/reload systemd и загрузка текущего stats-only файла процессом;
- journald-поведение и точные runtime-сообщения;
- production-БД, forensic snapshots и накопленные сигналы.

Проверены только исходный код, конфигурация, импорты, unit-тесты, regression
tests, статические проверки и безопасность публикации.

---

## 10. Подтверждение read-only

В ходе аудита:

- не было записи или редактирования файлов на production-сервере;
- не изменялись `.env`, БД, логи, cron, systemd unit/drop-in, пакеты и Git;
- не выполнялись restart/reload/stop сервиса;
- не выполнялись реальные торговые, Telegram, private BingX, CMC или CoinGlass
  действия;
- не копировались production-БД, логи, dumps или runtime cache;
- не публиковались секреты, chat_id и содержимое `.env`.

Финальная read-only проверка confirmed: `ActiveState=active`, `NRestarts=0`,
MainPID и start time соответствуют baseline; ключевые хэши файлов не
изменились. Сервер остался нетронутым.

---

## 11. Документы, изменённые по итогам аудита

- `PROJECT_FINAL_AUDIT.md` — этот отчёт;
- `PROJECT_FULL_DOCUMENTATION.md` — уточнены фактический data flow, dual-source
  thresholds, fetch semantics, cache behavior и ограничения;
- `PROJECT_VERSION_VERIFICATION.md` — актуализированы SHA/audit baseline,
  исправлены утверждения о порогах, fetch и тестах;
- `LW001_PRODUCTION_SPEC.md` — исправлено описание 4-часового окна и legacy
  volume entry point;
- `README.md` — добавлена ссылка на финальный аудит и уточнён статус.

Алгоритмические файлы, тестовые ожидания и active monitor не изменялись.

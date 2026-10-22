# EVRECONSE — сравнение production и GitHub по версиям

**Дата проверки:** 2026-10-22 (завершено 2026-10-23)
**Репозиторий:** `https://github.com/evreconse/EVR`
**Ветка:** `main`
**Проверенный GitHub HEAD на начало проверки:**
`fc131d7018da1e07031090ab7894e93b1a0875c1`
**Коммит синхронизации кода:**
`c6d00fa9623b83234c1674b8bf9bbbfe96500d96`
**Production entry point:**
`/home/evreconse/realtime_capitulation_monitor_fixed.py`
**Режим доступа к серверу:** строго read-only

Документ различает три состояния, которые нельзя смешивать:

1. **Работающий процесс** — код, загруженный в память процесса `880596` при
   старте `2026-10-17 08:02:29 UTC`.
2. **Файлы на диске сервера** — текущее содержимое `/home/evreconse`.
3. **GitHub** — опубликованный commit `fc131d7` (на момент начала проверки).

Точное содержимое памяти работающего Python-процесса read-only средствами не
извлекалось: для этого потребовалась бы отладка/инъекция в процесс. Поэтому для
работающего процесса ниже указано, что доказано, а что является обоснованной
реконструкцией. Сервер не перезапускался.

---

## 1. Краткий вывод

Активный алгоритм **Capitulation / Absorption** совпадает по всем существенным
формулам, порогам, фильтрам, порядку проверок, dedup и отправке уведомлений.
Это подтверждено:

- чтением серверных файлов и сравнением с GitHub;
- совпадением SHA-256 активного monitor и LW-001 monitor;
- разбором `apply_fix.py`, которым была сделана поздняя stats-only правка;
- regression-тестами на пороги, границы и эквивалентность двух источников
  порогов;
- mock-тестами fetcher/universe/dedup в опубликованном коде.

При этом **побайтовая идентичность не заявляется**:

- работающий процесс загрузил версию monitor до stats-only правки;
- detector/config и часть I/O-модулей имеют безопасные отличия в форматировании,
  typing и package layout;
- runtime-секреты, БД, `.env`, логи и production unit намеренно не публикуются;
- зависимости GitHub и серверный freeze различаются.

Итоговый статус: **алгоритмическое соответствие подтверждено, побайтовое — нет**.

---

## 2. Главная таблица

Сокращённые SHA-256 приведены для читаемости; полные значения — в §8.

| Компонент | Работающий процесс | Файл на диске сервера | GitHub | Влияет на сигнал | Статус |
|---|---|---|---|---|---|
| `realtime_capitulation_monitor_fixed.py` | версия до 18:45 UTC; stats-only отличие | `f661e379…` | `f661e379…` | нет (только reason/счётчики) | диск и GitHub совпадают побайтово |
| `FIXED_THRESHOLDS` + `check_thresholds()` | те же 4 порога | те же 4 порога | те же 4 порога | **да, финальный gate** | значения совпадают; dual-source |
| `src/strategy/capitulation_detector.py` | та же логика | `3b239a00…` | `8e2ff8f6…` | нет | алгоритмически совпадает |
| `config/capitulation_thresholds.py` → `src/config/...` | те же значения | `bc51b697…` | `4a7789ee…` | нет | значения/операторы совпадают |
| `src/exchange/bingx_fetcher.py` | та же логика | `89369399…` | `19caf773…` | нет | typing/lint-адаптация |
| `src/exchange/bingx_rate_limiter.py` | та же логика | `bd77f051…` | `4f08b318…` | нет | lint-адаптация |
| `src/exchange/bingx_endpoints.py` | та же логика | `cdc63bc0…` | `78e28acc…` | нет | lint-адаптация |
| `src/data_provider/universe_provider.py` | та же логика | `9ca77e0b…` | `2744e235…` | нет | lint-адаптация |
| `src/data_provider/cmc_universe_cache.py` | та же логика | `da46289b…` | `56c3eb03…` | нет | lint + удалён недостижимый `__main__` |
| SQLite dedup (`claim_signal`) | та же логика | inline в monitor | inline в monitor | да (повторная отправка) | побайтово в составе monitor |
| Telegram send | та же логика | inline в monitor | inline в monitor | только доставка | побайтово в составе monitor |
| `evreconse.service` | production unit | `/etc/systemd/system/...` | безопасный шаблон | нет | намеренно не точная копия |
| `realtime_lw001_monitor.py` | не запущен | `df9331d7…` | `df9331d7…` | нет (inactive) | побайтово совпадает |
| `LW001_METRIC_SPEC.py` | не запущен | `3926898d…` | `bd5ecc63…` | нет (inactive) | typing/formatting |
| `src/strategy/lw001_canonical.py` | не запущен | `79349666…` | `8af63751…` | нет (inactive) | исправлен текст сообщения |
| `src/strategy/lw_001.py` | не запущен | `fe9a1e6e…` | `411c5f1b…` | нет (inactive) | legacy-адаптация |
| `src/exchange/coinmarketcap_fetcher.py` | не используется active path | `d77213dc…` | `298d2dd2…` | нет | функциональная адаптация |
| `requirements.txt` / `pyproject.toml` | серверный freeze | `6e638060…` | `3631ae89…` | нет для pure-Python формул | версии/кодировка различаются |

---

## 3. Работающий процесс против файла на диске

### 3.1. Установленные факты

```text
systemd unit:       evreconse.service
ExecStart:          /usr/bin/python3 /home/evreconse/realtime_capitulation_monitor_fixed.py
WorkingDirectory:   /home/evreconse
User:               evreconse
MainPID:            880596
Started:            2026-10-17 08:02:29 UTC
NRestarts:          0
ActiveState:        active
SubState:           running
```

- В `/home/evreconse` нет `.git`; это standalone deployment, не checkout.
- Активен один процесс; других экземпляров монитора не обнаружено.
- `realtime_capitulation_monitor_fixed.py` имеет mtime
  `2026-10-17 18:45:03 UTC`, то есть **позже** старта процесса.
- `src/strategy/capitulation_detector.py`, `config/capitulation_thresholds.py`,
  `src/exchange/bingx_fetcher.py`, `src/exchange/bingx_rate_limiter.py`,
  `src/exchange/bingx_endpoints.py`, `src/data_provider/universe_provider.py`,
  `src/data_provider/cmc_universe_cache.py` имеют mtime **раньше** старта
  процесса.

### 3.2. Что именно изменяла поздняя правка

Рядом с monitor лежит `apply_fix.py` (mtime `2026-10-17 18:45:02 UTC`). Он
читает `realtime_capitulation_monitor_fixed.py`, выполняет две точные замены и
записывает файл обратно:

1. В `verify_signal_comprehensive()` generic-строка
   `"Metrics do not pass thresholds"` заменяется на конкретные
   `DROP_FAIL` / `VOLUME_FAIL` / `WICK_BODY_FAIL` / `RECLAIM_FAIL`.
2. В `check_latest_candle_with_stats()` меняется только распределение
   счётчиков `stats._filtered_*` / `stats._not_red` / `stats._exception_errors`
   по этим строкам.

`apply_fix.py` не содержит замен порогов, формул, `check_thresholds`,
`check_red_candle`, `claim_signal`, `send_signal_to_telegram`, `SENT_SIGNALS` или
`FIXED_THRESHOLDS`. Следовательно:

- **сигнальное решение** работающего процесса и текущего файла одинаково;
- различаются только диагностический текст причины отказа и распределение
  статистических счётчиков;
- побайтово работающий процесс и текущий файл **не identical**;
- процесс не перезапускался, поэтому GitHub (совпадающий с текущим файлом)
  представляет диск, а не доказанную память процесса.

### 3.3. Чего доказать нельзя

Нельзя без вмешательства в процесс доказать, что в памяти находится ровно
реконструкция «текущий файл минус две замены `apply_fix.py`». Не сохранился
hash файла на момент `08:02:29 UTC`. Есть только:

- mtime файла и `apply_fix.py`;
- содержимое `apply_fix.py` с точными заменами;
- отсутствие других изменений monitor после старта (по mtime и журналу);
- идентичность всех алгоритмических ветвей, проверенная статически и тестами.

Этого достаточно для вывода об алгоритмической эквивалентности, но не для
утверждения о побайтовой идентичности памяти.

---

## 4. Активный путь: что именно применяется

### 4.1. Два источника порогов

В опубликованном и серверном коде есть два слоя:

1. `src/strategy/capitulation_detector.py` читает
   `CAPITULATION_THRESHOLDS` из `src/config/capitulation_thresholds.py`
   (на сервере — `config/capitulation_thresholds.py`) и формирует
   `result.qualified`.
2. `realtime_capitulation_monitor_fixed.py` **не использует**
   `result.qualified`. Он вызывает `check_thresholds(metrics)` с собственным
   `FIXED_THRESHOLDS`.

Фактический финальный gate:

```python
FIXED_THRESHOLDS = {
    "drop_pct": -5.0,        # open_to_low_pct <= -5.0
    "wick_body_ratio": 1.0,  # lw_body_ratio >= 1.0
    "reclaim_pct": 30.0,     # reclaim_pct >= 30.0
    "volume_30_ratio": 2.0,  # volume_30_ratio >= 2.0
}
```

Плюс отдельная проверка `close < open` в monitor. Все условия — AND.
Score-гейта нет.

### 4.2. Совпадают ли два источника

Да, на проверенной версии:

| Условие | Detector/config | Monitor `check_thresholds` |
|---|---:|---:|
| Red candle | `close < open` | отдельная `check_red_candle` |
| Open → Low | `<= -5.0` | `<= -5.0` |
| Volume30Ratio | `>= 2.0` | `>= 2.0` |
| LW / Body | `>= 1.0` | `>= 1.0` |
| Reclaim | `>= 30.0` | `>= 30.0` |

Для проверки добавлен `tests/test_monitor_threshold_equivalence.py`, который
извлекает **реальные** `FIXED_THRESHOLDS` и `check_thresholds` из опубликованного
monitor (без импорта с побочными эффектами) и сравнивает их с полной
квалификацией detector на:

- 5 000 случайных свечах;
- точных границах;
- свечах с нулевым body/range/open;
- зелёной свече.

Результат: расхождений нет.

Дополнительно серверный `capitulation_detector.py` (baseline, SHA-256
`3b239a00…`) и GitHub-версия были загружены раздельно и прогнаны на **5 007**
одинаковых кейсах. JSON-выходы с `qualified`, `failed_conditions` и всеми
`metrics` совпали побайтово. Это подтверждает алгоритмическую идентичность
detector, а не только совпадение порогов.

### 4.3. Остающийся риск

Это **dual source of truth**. Если изменить только
`src/config/capitulation_thresholds.py`, detector начнёт считать иначе, но
финальное решение active monitor не изменится, потому что он использует
`FIXED_THRESHOLDS`. Это архитектурный долг, а не расхождение текущих значений.
Он не исправлялся, чтобы не менять production-поведение.

---

## 5. Формулы, данные и порядок решения

### 5.1. Данные

- Источник: публичные BingX USDT perpetual klines через `BingXFetcher`.
- Timeframe: `15m`.
- Запрос: `limit=500`, `endTime=now`; `startTime` вычисляется как `now - 4h`,
  но при `limit=500` не применяется как фильтр. `get_klines()` использует
  только `endTime`, разворачивает ответ и возвращает до 500 последних свечей.
- Сортировка: явная сортировка по timestamp отсутствует; код полагается на
  порядок ответа BingX и `reversed()`. Это ограничение, а не гарантия.
- Закрытая свеча: `timestamp + 15 * 60 * 1000 <= now_ms`; поиск идёт с конца
  массива.
- Минимум: `len(candles) >= 2`; для median30 требуется `candle_index >= 31`,
  то есть **32 свечи** включая оцениваемую.
- Предыдущие 30 объёмов: индексы `candle_index - 30 … candle_index - 1`.

### 5.2. Формулы

```python
range        = high - low
range_pct    = range / open * 100
open_to_low  = (low - open) / open * 100
body         = abs(close - open)
body_pct     = body / open * 100
lower_wick   = min(open, close) - low
lw_body      = lower_wick / body                    # 0.0 при body == 0
lw_range_pct = lower_wick / range * 100             # 0.0 при range <= 0
reclaim_pct  = (close - low) / range * 100          # 0.0 при range <= 0
median30     = median(previous 30 completed M15 volumes)
volume_ratio = volume / median30                    # 0.0 при median30 <= 0
is_red       = close < open
```

При `open == 0` процентные метрики detector возвращают `0.0`, исключение не
бросается. При нулевом body/range соответствующие ratios равны `0.0`. Это
означает, что такие свечи не проходят пороги, а не вызывают падение цикла.

### 5.3. Порядок проверок active monitor

```text
fetch candles
  → len(candles) < 2?                 → insufficient_candles
  → get_last_completed_candle()
  → timestamp <= 0?                   → invalid_timestamp
  → (symbol, timestamp) in memory?    → already_processed
  → candle_index < 31?                → insufficient_history
  → prev_30_volumes
  → verify_signal_comprehensive()
       → timestamp <= 0?              → Invalid timestamp
       → close < open?                → not red
       → len(prev_30) < 30?           → insufficient history
       → detector metrics
       → check_thresholds(metrics)    → 4 conditions
  → signal
  → claim_signal() SQLite
  → send_signal_to_telegram()
  → status sent / failed + rollback
```

`result.qualified` и `result.failed_conditions` в этом пути не используются для
финального решения. Они вычисляются detector, но monitor принимает решение по
`check_thresholds`.

---

## 6. Dedup, SQLite и Telegram

### 6.1. Dedup

- БД: `/home/evreconse/sent_signals.db`.
- Таблица `sent_signals`, PK `(symbol, candle_timestamp)`.
- `claim_signal()` делает `INSERT ... telegram_status='pending'` и commit.
- `sqlite3.IntegrityError` → сигнал уже обрабатывался, отправка пропускается.
- Успех → `telegram_status='sent'`, сохраняется `telegram_message_id`.
- Полный failure → статус `failed`, затем строка **удаляется** (`DELETE`),
  memory-set очищается; сигнал может быть обработан повторно.
- При старте pending-сигналы только перечисляются с сообщением
  `manual intervention needed`; автоматического resend нет.
- `SENT_SIGNALS` — in-memory snapshot на старте; источник истины для
  конкурентного claim — SQLite PK.

Снимок на момент проверки: **663 строки**, 468 `pending`, 195 `sent`.
Значения меняются во время работы.

### 6.2. Telegram

- Получатели: personal chat и optional channel, если заданы в `.env`.
- Успех, если доставлено хотя бы одно сообщение; сохраняется первый `message_id`.
- Отдельного retry-loop нет; есть обработка HTTP/JSON-ошибок и rollback claim.
- При неудаче одного получателя второй всё равно пытается отправиться.
- `chat_id` печатается в journald в диагностических сообщениях — это
  эксплуатационный/privacy-риск, не влияющий на сигнал.
- Реальная отправка в рамках проверки **не выполнялась**.

---

## 7. Universe: важное расхождение в runtime-состоянии

Код GitHub и серверный код `universe_provider.py` / `cmc_universe_cache.py`
совпадают алгоритмически, но фактическое состояние сервера имеет отдельную
проблему:

- active snapshot: `id=5`, `final_count=574`,
  `fetched_at=2026-10-08T09:25:51Z`;
- `data/cmc_universe.db` принадлежит `root:root`, режим `0644`;
- процесс работает под `evreconse`, поэтому не может писать в этот файл;
- в journal зафиксированы ошибки автоматического refresh:
  `Universe refresh failed: attempt to write a readonly database`
  (21 и 22 октября 2026);
- `UniverseProvider.get_universe()` возвращает active snapshot без проверки
  возраста/expiry; fallback используется только при отсутствии active cache;
- `initialize()` не делает немедленный refresh; фоновый loop сначала спит 24h.

Следствие: active universe остаётся **замороженным на 574 символах** с 8 октября
2026. Монитор продолжает работать, а 28 символов в типичном цикле
классифицируются как offline. Это не меняет формулы сигнала, но влияет на
полноту universe и является эксплуатационным риском.

GitHub не содержит runtime-БД и не может исправить права на сервере. В рамках
задачи сервер **не изменялся**.

---

## 8. Полные SHA-256

### 8.1. Сервер (read-only снимок)

```text
f661e3796f9285dc3fc592714bc980d7734ec8dae61b6dcbd2863083d3de8204  realtime_capitulation_monitor_fixed.py
df9331d7b64ada4cc47c510889b9af4c9e028677f22efcb52b8541ea2a6112fb  realtime_lw001_monitor.py
3926898d46477ed94fe9362c1b709ef2722a608c38a1adf25a89b78d5e3c3e18  LW001_METRIC_SPEC.py
3b239a003ee20873178ae2e0aad15784556658fb5b343bc98e4d1e843ace0539  src/strategy/capitulation_detector.py
bc51b6972d243bb18eee1165579b18899597cd9b67d423dae0017bb0e62a0b5e  config/capitulation_thresholds.py
793496663f581ae528d06aecacf6b06a27ff229cb4fbc40ffa0a6698053999e2  src/strategy/lw001_canonical.py
fe9a1e6ec2205ce4f304898ad88b66a99877697d27d1e2d82653724d98fc4cfc  src/strategy/lw_001.py
89369399e2521a8fa0e9b3aaf6faba05221e7d1090660bccc13e122050c6a14d  src/exchange/bingx_fetcher.py
bd77f0516baf1bb4f058f5b88f857d5b015cf8fc32334d9ec30cf20cdfd5c3a6  src/exchange/bingx_rate_limiter.py
cdc63bc050cf58f23aeb692b8f1dc18962ded5f58e3cfdc622c534eeafc7405a  src/exchange/bingx_endpoints.py
9ca77e0b80b4f8859b57163324c8cf0ce7a831ed1e0112cf49c4d06ed2f0c0aa  src/data_provider/universe_provider.py
da46289b9eb1880091e56fa1d88f43ebb56234c2fe02d6dac1067de34fad58d3  src/data_provider/cmc_universe_cache.py
d77213dc7bcd5a7ac3577e9539552b9f6148cf658ca3b9bbfc0088d7ef13fb32  src/exchange/coinmarketcap_fetcher.py
```

### 8.2. GitHub `fc131d7`

```text
f661e3796f9285dc3fc592714bc980d7734ec8dae61b6dcbd2863083d3de8204  realtime_capitulation_monitor_fixed.py
df9331d7b64ada4cc47c510889b9af4c9e028677f22efcb52b8541ea2a6112fb  realtime_lw001_monitor.py
bd5ecc63cad03d229b298152e0662021046911ff50a1eca1d64cd1d4958f309f  LW001_METRIC_SPEC.py
8e2ff8f6ef5775df6071617c96ff853fb3084cb73da9bc4ed65356e982a75c89  src/strategy/capitulation_detector.py
4a7789ee20abd8a6d7b3f9e6016f2e8f6ded14bfba3a6ce809d2109d656ff93d  src/config/capitulation_thresholds.py
8af637514c884e40e8da327fdf84bb02d75bbc5a38c81acb38dd7d018c49f8d6  src/strategy/lw001_canonical.py
411c5f1b2ce4ad425a79aadfc0a40e664e0ab5ddfde809329bc8e7acd3d03899  src/strategy/lw_001.py
19caf7730bf484ed337ba120f67e5b2fd70c71ba01c42c1058ed1aee7d2fa0ca  src/exchange/bingx_fetcher.py
4f08b3180bef2068dccfed6bc43f3d58b7dc74fe1ac0980f18985b0aab7867a3  src/exchange/bingx_rate_limiter.py
78e28acc39e1b5f7026a9d3599e57aba8a1e2dc866f59ff5f8425bb45425b047  src/exchange/bingx_endpoints.py
2744e235c7bef4386a492426b367bdff994f210f9e1ba5d3dd49e64f3d34d9a1  src/data_provider/universe_provider.py
56c3eb033ba1d43e1627a02c5414bcb87d94bdcfe55df84264e110860f5553ae  src/data_provider/cmc_universe_cache.py
298d2dd20632bcd95469651f7d04afc9c9d1c43eeb380ac3080c301aaebcbdc7  src/exchange/coinmarketcap_fetcher.py
```

---

## 9. Безопасные адаптации, которые не меняют сигнал

| Отличие | Сервер | GitHub | Почему не влияет |
|---|---|---|---|
| Package layout | `config/capitulation_thresholds.py` | `src/config/capitulation_thresholds.py` | active monitor добавляет `src` в `sys.path`; значения те же |
| Formatting/typing | `List`, `Dict`, лишние пробелы | `list`, `dict`, `from __future__` | исполняемая логика та же |
| Lint headers | нет | `# ruff: noqa`, `# mypy: ignore-errors` | комментарии/директивы |
| `cmc_universe_cache` main | недостижимый `asyncio.run(main())` | блок удалён | active path не вызывает `__main__` |
| LW-001 messages | местами `-2.5%` | `-5.0%` | порог берётся из spec; LW-001 inactive |
| LW-001 strategy | без `Strategy` base | наследует `Strategy` | inactive; active path не импортирует |
| CMC fetcher | без проверки типа `data` | добавлена проверка list | CMC не используется active monitor |
| Service unit | production unit | безопасный шаблон | не влияет на расчёт; секреты не публикуются |
| Dependencies | freeze от 2026-10-01 | более новые версии | формулы pure Python; тесты проходят |

---

## 10. Что не проверялось

- Реальная отправка Telegram.
- Приватные BingX-эндпоинты, CMC и CoinGlass.
- Перезапуск/остановка production-сервиса.
- Побайтовое извлечение кода из памяти процесса.
- Изменение runtime-БД, `.env`, логов или прав на сервере.
- Полная проверка всех исторических коммитов на секреты (выполнена отдельная
  high-confidence проверка; см. `GITHUB_SERVER_SYNC_REPORT.md`).

---

## 11. Итоговая оценка

| Вопрос | Ответ |
|---|---|
| Активная стратегия | Capitulation / Absorption |
| Формулы совпадают | да |
| Пороги совпадают | да |
| Операторы/границы совпадают | да |
| Дополнительные фильтры совпадают | да |
| Порядок решения совпадает | да |
| Dedup/Telegram flow совпадают | да |
| Побайтово active monitor | диск = GitHub; память процесса — нет |
| Detector/config побайтово | нет (formatting/typing/layout) |
| Алгоритмически | да, подтверждено |
| Production изменялся | нет |

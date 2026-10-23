# EVRECONSE — отчёт о синхронизации GitHub с production

**Дата:** 2026-10-23 (этап 2)
**Репозиторий:** `https://github.com/evreconse/EVR`
**Ветка:** `main`
**HEAD на начало этапа:** `907354b2473e557c52e40372ba189df1a48170ae`
**Коммит синхронизации:** `6b2f2b8570d3afb0e3f182465a400c4c6f8022e7`
**Production entry point:** `/home/evreconse/realtime_capitulation_monitor_fixed.py`
**Доступ к production:** строго read-only
**Итоговый статус:** **B. АЛГОРИТМИЧЕСКАЯ ЭКВИВАЛЕНТНОСТЬ ПОДТВЕРЖДЕНА, НО ОСТАЛИСЬ ФАЙЛОВЫЕ РАЗЛИЧИЯ**

---

## 1. Ограничения и гарантии

На production не выполнялось:

- запись, создание или удаление файлов;
- изменение `.env`, конфигурации, БД, кэша, логов, прав, владельцев, пакетов
  или systemd;
- restart / stop / reload / запуск второго экземпляра;
- реальные торговые операции;
- отправка Telegram;
- приватные BingX, CMC или CoinGlass запросы, способные иметь side effects.

Разрешённые операции: чтение файлов, SHA-256, mtime, systemd properties,
journal, метаданные SQLite, SFTP-копирование исходников. Секреты не читались и
не публиковались.

---

## 2. Исходное состояние

Новый clone, не прежняя рабочая копия:

```text
remote: https://github.com/evreconse/EVR.git
HEAD:   907354b2473e557c52e40372ba189df1a48170ae
branch: main
status: clean
```

`git ls-remote` до начала работ:

```text
907354b2473e557c52e40372ba189df1a48170ae  refs/heads/main
```

Production read-only снимок:

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

---

## 3. Что синхронизировано

Точные копии production-файлов (SHA-256 server = GitHub):

| Файл | SHA-256 |
|---|---|
| `realtime_capitulation_monitor_fixed.py` | `f661e3796f9285dc3fc592714bc980d7734ec8dae61b6dcbd2863083d3de8204` |
| `config/__init__.py` | `35e3ae3fd2851525ecf6741ab834a63fcc6b722ca40b95f62ffd955035561b23` |
| `config/capitulation_thresholds.py` | `bc51b6972d243bb18eee1165579b18899597cd9b67d423dae0017bb0e62a0b5e` |
| `src/config/capitulation_thresholds.py` | `bc51b6972d243bb18eee1165579b18899597cd9b67d423dae0017bb0e62a0b5e` |
| `src/strategy/__init__.py` | `db6101ff709de19a0d3d2ccb3e671c926259eacb5f607004bf885ff7cb6e9d8d` |
| `src/strategy/capitulation_detector.py` | `3b239a003ee20873178ae2e0aad15784556658fb5b343bc98e4d1e843ace0539` |
| `src/exchange/__init__.py` | `eb8ea474128749befcd3d052499ae3b1504c226edf7c746217dd4b2931acffd5` |
| `src/exchange/bingx_fetcher.py` | `89369399e2521a8fa0e9b3aaf6faba05221e7d1090660bccc13e122050c6a14d` |
| `src/exchange/bingx_rate_limiter.py` | `bd77f0516baf1bb4f058f5b88f857d5b015cf8fc32334d9ec30cf20cdfd5c3a6` |
| `src/exchange/bingx_endpoints.py` | `cdc63bc050cf58f23aeb692b8f1dc18962ded5f58e3cfdc622c534eeafc7405a` |
| `src/data_provider/__init__.py` | `2039e99ffed561d8414b6eb16df914d7115c8de7a050b9b939fdc0c06949ba56` |
| `src/data_provider/universe_provider.py` | `9ca77e0b80b4f8859b57163324c8cf0ce7a831ed1e0112cf49c4d06ed2f0c0aa` |
| `src/data_provider/cmc_universe_cache.py` | `da46289b9eb1880091e56fa1d88f43ebb56234c2fe02d6dac1067de34fad58d3` |
| `evreconse.service` | `adc9201cca8a299c3da4aa7b70ddbf1efe5eb70f62eb5969844e23ed8c14e51c` |
| `requirements-production-freeze.txt` | `6e638060c003708658e1e10ca9ed020df24ca9324277dc6e18412aa2a04ad41e` |

Дополнительно:

- добавлен top-level `config/`, чтобы active detector разрешал production
  config package, а не `src/config`;
- `evreconse.service` опубликован точной копией production unit; секретов в нём
  нет;
- серверный freeze опубликован отдельным ASCII-файлом;
- добавлен `tests/test_production_source_sync.py`: 15 hash-проверок + 1
  subprocess-проверка разрешения top-level `config`;
- в `pyproject.toml` exact production-файлы исключены из lint/type-политики,
  потому что они сохраняются verbatim, включая старый typing и отсутствие
  trailing newline. Это не меняет runtime; формулы покрыты тестами.

### 3.1. Почему exact production-файлы исключены из ruff/mypy

Production-файлы написаны до современной repo-политики. Если их
переформатировать, SHA-256 перестанет быть доказательством. Поэтому:

- `ruff` per-file ignores для точных файлов;
- `mypy` overrides с `ignore_errors` для detector/fetcher/limiter и
  downstream `bingx_provider`, который получает тип `List[List]` из
  production fetcher;
- остальные 96 source-файлов проверяются mypy;
- runtime, import, hash и equivalence tests остаются обязательными.

Это осознанный компромисс: **точность исходника важнее косметического lint**.

---

## 4. Что не синхронизировано

| Объект | Причина |
|---|---|
| 25 import-time-only modules | Загружаются через `__init__.py`, но не участвуют в Capitulation signal; часть имеет реальные API-отличия. См. `PROJECT_VERSION_COMPARISON.md` §4 |
| `src/config/__init__.py` | Application config package; active monitor использует top-level exact `config` |
| `requirements.txt` | Dev manifest в UTF-16/CRLF; exact server freeze добавлен отдельно |
| `.env`, БД, кэши, логи | Секреты/runtime-данные |
| LW-001 legacy | Не запущен; отличается и не должен включаться без решения владельца |
| CoinMarketCap fetcher | Не используется active monitor |
| Точная память процесса | Процесс не перезапускался; дамп/отладка запрещены |

Полная таблица с SHA-256 и влиянием — в `PROJECT_VERSION_COMPARISON.md`.

---

## 5. Проверки

| Проверка | Результат |
|---|---|
| `pytest -q` | **152 passed** |
| `pytest -q tests/test_production_source_sync.py` | **16 passed** |
| `pytest -q tests/test_server_sync_algorithms.py` | **18 passed** |
| `pytest -q tests/test_monitor_threshold_equivalence.py` | **3 passed** |
| `ruff check src tests config` | **All checks passed** |
| `mypy src` | **Success: no issues found in 96 source files** |
| Compile/import active modules | **OK** |
| `git diff --check` | **OK** |
| Server-vs-GitHub detector, полный import path | **5 007 / 5 007 identical**, JSON SHA-256 `793afcd9…` |
| Monitor gate vs detector/config | **5 000 random + boundaries + degenerate**, расхождений нет |

Synthetic comparison не выполнял сетевые запросы, Telegram, private BingX, CMC
или CoinGlass. Использовались только локальные копии серверных исходников и
сгенерированные свечи.

### 5.1. Что именно проверено в active path

- 15m, последняя закрытая свеча;
- red candle `close < open`;
- Open→Low `<= -5.0%`;
- Volume30Ratio `>= 2.0x`;
- LW/Body `>= 1.0x`;
- Reclaim `>= 30.0%`;
- median предыдущих 30 завершённых свечей;
- минимум 32 свечи для history;
- `result.qualified` вычисляется, но monitor использует `check_thresholds()`;
- dedup SQLite `(symbol, candle_timestamp)`, `pending → sent/failed`,
  rollback при ошибке;
- Telegram personal + channel, success хотя бы одного;
- rate limit / offline / network / other errors, per-symbol isolation;
- universe stale и readonly SQLite — documented operational risk.

---

## 6. Секреты

Проверено:

- diff и новые файлы;
- текущее дерево;
- история Git (blobs);
- отсутствие `.env`, БД, логов, private keys и реальных chat_id в публикации.

Результат: high-confidence секретов не обнаружено. В коде остаются только имена
переменных окружения (`EVRECONSE_...`) и безопасный `.env.example`. Реальные
Telegram chat_id, токены, API-ключи и production DB в GitHub не попадали.

---

## 7. Публикация

Публикация выполняется обычными commits в `main`, без force-push, без rewrite
history, без удаления чужих изменений.

Порядок:

1. commit с exact-файлами, service, freeze, тестом и документацией;
2. push в `origin/main`;
3. новый clone с GitHub;
4. проверка HEAD через `git ls-remote`, clean worktree, hash-тестов и полного
   `pytest -q`;
5. при необходимости — metadata-follow-up commit с точным SHA публикации.

Фактически выполнено:

```text
code commit:   6b2f2b8570d3afb0e3f182465a400c4c6f8022e7
push:          907354b..6b2f2b8  main -> main
fresh clone:   6b2f2b8570d3afb0e3f182465a400c4c6f8022e7
worktree:      clean
pytest:        152 passed
ruff:          All checks passed
mypy:          Success: no issues found in 118 source files
```

Metadata-follow-up commit (если создан) содержит только документацию и
обновляет точный финальный HEAD; code commit остаётся `6b2f2b8`. Финальный
remote HEAD указан в ответе и подтверждается `git ls-remote`.

---

## 8. Production остался неизменным

Повторная read-only проверка после работ:

```text
ActiveState=active
SubState=running
MainPID=880596
NRestarts=0
Started=2026-10-17 08:02:29 UTC
```

Ключевые серверные SHA-256 не изменились:

```text
f661e379…  realtime_capitulation_monitor_fixed.py
3b239a00…  src/strategy/capitulation_detector.py
bc51b697…  config/capitulation_thresholds.py
89369399…  src/exchange/bingx_fetcher.py
9ca77e0b…  src/data_provider/universe_provider.py
```

Не выполнялось restart/stop/reload, запись файлов, изменение прав, БД, логов,
`.env`, пакетов или systemd. Работающий процесс не перезапускался.

---

## 9. Остающиеся риски

1. **Память процесса.** Загружена версия monitor до stats-only правки;
   побайтовая memory identity не доказана.
2. **25 import-time-only modules.** Не синхронизированы; не влияют на current
   Capitulation signal, но отличаются.
3. **Dual thresholds.** `FIXED_THRESHOLDS` и detector/config не связаны
   автоматически. Текущие значения совпадают; изменение только config не
   изменит production signal.
4. **Universe stale.** Snapshot от 2026-10-08, 574 символа; SQLite принадлежит
   `root:root 0644`; refresh падает с `attempt to write a readonly database`.
5. **Pending claims.** Автоматического resend нет; pending требует ручного
   вмешательства.
6. **Telegram chat_id в journald.** Privacy/ops risk; live send не проверялся.
7. **API order.** Нет явной сортировки свечей; используется порядок ответа
   BingX + `reversed()`.
8. **Fetch window.** `startTime` не ограничивает выдачу при `limit=500`;
   фактически до 500 M15-свечей, не строго 4 часа.
9. **Dependency pin.** Server freeze и dev manifest различаются; exact freeze
   опубликован отдельно, но ОС/Python-окружение не воспроизводится полностью.
10. **Inactive LW-001.** Не включать без отдельного решения; его код отличается.

---

## 10. Итог

**B. АЛГОРИТМИЧЕСКАЯ ЭКВИВАЛЕНТНОСТЬ ПОДТВЕРЖДЕНА, НО ОСТАЛИСЬ ФАЙЛОВЫЕ
РАЗЛИЧИЯ.**

Signal path Capitulation/Absorption синхронизирован побайтово; production
config, monitor, detector, fetcher, limiter, universe/cache, package init,
systemd unit и server freeze зафиксированы хэшами. Оставшиеся различия
относятся к import-time-only application/legacy-модулям, `src/config` layout и
dev requirements. Production не изменялся и не перезапускался.

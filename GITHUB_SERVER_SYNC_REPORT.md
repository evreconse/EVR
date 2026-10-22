# EVRECONSE — отчёт о синхронизации GitHub и production-сервера

**Дата отчёта:** 2026-10-23
**Репозиторий:** `https://github.com/evreconse/EVR`
**Ветка:** `main`
**Проверенный GitHub HEAD на начало работ:**
`fc131d7018da1e07031090ab7894e93b1a0875c1`
**Коммит синхронизации кода:**
`c6d00fa9623b83234c1674b8bf9bbbfe96500d96`
**Production entry point:**
`/home/evreconse/realtime_capitulation_monitor_fixed.py`
**Режим доступа к production:** строго read-only

**Итоговый статус:**
**АЛГОРИТМИЧЕСКОЕ СООТВЕТСТВИЕ ПОДТВЕРЖДЕНО, ПОБАЙТОВОЕ НЕ ДОКАЗАНО.**

---

## 1. Что проверялось

Проверка выполнялась в отдельном свежем clone GitHub, а не в прежней локальной
копии. Production-сервер использовался только для чтения: файлы, хэши, mtime,
systemd-состояние, journal и SQLite-метаданные. Не выполнялось:

- запись файлов, `.env`, конфигурации, БД, кэша или логов на сервере;
- изменение прав, пакетов, systemd unit или процессов;
- restart/stop/reload сервиса;
- реальные торговые операции;
- отправка Telegram;
- private BingX, CMC или CoinGlass запросы.

---

## 2. Исходное состояние GitHub

Свежий clone:

```text
remote: https://github.com/evreconse/EVR.git
HEAD:   fc131d7018da1e07031090ab7894e93b1a0875c1
branch: main
status: clean
```

Проверено через `git ls-remote`:

```text
fc131d7018da1e07031090ab7894e93b1a0875c1  refs/heads/main
```

Ожидаемые коммиты присутствуют:

- `c6d00fa9623b83234c1674b8bf9bbbfe96500d96` — синхронизация production-кода
  Capitulation и LW-001;
- `3581bb24bd6bcbf00958b674b865cfa0e978125f` — docs-only follow-up;
- `3b85cab990772aef1132c5c41d6d3697d48c4918` — audit report;
- `fc131d7018da1e07031090ab7894e93b1a0875c1` — metadata follow-up.

Неожиданных коммитов или изменений remote не обнаружено.

---

## 3. Исходное состояние production

Read-only снимок:

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
```

- В `/home/evreconse` нет `.git`; это standalone deployment.
- Активен один экземпляр монитора.
- `realtime_capitulation_monitor_fixed.py` имеет mtime
  `2026-10-17 18:45:03 UTC`, то есть позже старта процесса.
- Остальные импортируемые модули имеют mtime раньше старта процесса.
- Рядом находится `apply_fix.py`, который в 18:45 UTC сделал только две
  stats/diagnostic замены; пороги, формулы, dedup и Telegram-flow не менялись.
- Побайтовое содержимое памяти процесса не извлекалось: это потребовало бы
  отладки/инъекции. Поэтому работающий процесс описан как алгоритмически
  эквивалентный, но не доказанно побайтово идентичный текущему файлу.

Подробный разбор: `PROJECT_VERSION_COMPARISON.md`.

---

## 4. Что синхронизировано в GitHub

Коммит `c6d00fa` содержит production-код активной стратегии и сопутствующие
модули:

- `realtime_capitulation_monitor_fixed.py` — active entry point;
- `src/strategy/capitulation_detector.py` — config-driven detector;
- `src/config/capitulation_thresholds.py` — active thresholds;
- `src/exchange/bingx_fetcher.py`, `bingx_rate_limiter.py`,
  `bingx_endpoints.py`;
- `src/data_provider/universe_provider.py`, `cmc_universe_cache.py`;
- `realtime_lw001_monitor.py`, `LW001_METRIC_SPEC.py`,
  `src/strategy/lw001_canonical.py`, `src/strategy/lw_001.py` — inactive
  legacy LW-001;
- `evreconse.service` — безопасный шаблон, не точная копия production unit;
- `tests/test_server_sync_algorithms.py` — 18 regression tests.

Текущая проверка дополнительно добавляет:

- `PROJECT_VERSION_COMPARISON.md` — три состояния и таблица расхождений;
- `STRATEGY_CAPITULATION_ABSORPTION.md` — полное описание active strategy;
- `tests/test_monitor_threshold_equivalence.py` — 3 теста эквивалентности
  `FIXED_THRESHOLDS`/`check_thresholds` и detector/config;
- ссылки и уточнения в `README.md`, `PROJECT_FULL_DOCUMENTATION.md`,
  `PROJECT_VERSION_VERIFICATION.md`.

Активный monitor в GitHub побайтово совпадает с текущим файлом на диске
сервера:

```text
SHA-256 f661e3796f9285dc3fc592714bc980d7734ec8dae61b6dcbd2863083d3de8204
```

LW-001 monitor также совпадает побайтово:

```text
SHA-256 df9331d7b64ada4cc47c510889b9af4c9e028677f22efcb52b8541ea2a6112fb
```

Detector/config и I/O-модули имеют только безопасные отличия (package layout,
formatting, typing, lint-заголовки, удалённый недостижимый `__main__`).
Ни одно из них не меняет active signal decision. Доказательства и полные хэши —
в `PROJECT_VERSION_COMPARISON.md`.

---

## 5. Что намеренно не синхронизировано

| Объект | Причина |
|---|---|
| `.env` и любые секреты | Не публикуются |
| `sent_signals.db`, `cmc_universe.db` | Runtime-данные production |
| Логи, `__pycache__`, кэши | Runtime-артефакты |
| Точный `/etc/systemd/system/evreconse.service` | Внутренние эксплуатационные настройки; в GitHub безопасный шаблон |
| Абсолютные `/home/evreconse/...` пути | Сохранены как production-поведение; для переноса нужен deployment-конфиг |
| Серверный dependency freeze | GitHub сохраняет declared dependency ranges, а не копию `pip freeze` |
| Stats-only правка в памяти процесса | Процесс не перезапускался; на диске и в GitHub файл новее |
| Отличия inactive LW-001 | Legacy-код не является production; сообщения/адаптеры не влияют на active path |
| CMC fetcher | Не используется active monitor; GitHub-версия содержит дополнительную валидацию |

---

## 6. Проверки

Выполнено локально, без внешних интеграций:

| Проверка | Результат |
|---|---|
| `pytest -q` | **136 passed** |
| `pytest -q tests/test_server_sync_algorithms.py` | **18 passed** |
| `pytest -q tests/test_monitor_threshold_equivalence.py` | **3 passed** |
| `ruff check src tests LW001_METRIC_SPEC.py` | **All checks passed** |
| `mypy src/ tests/ --explicit-package-bases` | **Success: no issues found in 117 source files** |
| `py_compile` изменённых Python-файлов | **OK** |
| Runtime imports algorithm modules | **OK** |
| `git diff --check` | **OK** |

Дополнительно выполнено сравнение на одинаковых синтетических свечах:

- 5 000 случайных свечей;
- точные границы `-5.0%`, `2.0x`, `1.0x`, `30.0%`;
- нулевые body/range/open;
- зелёная свеча.

Серверный `capitulation_detector.py` (baseline, SHA-256 `3b239a00…`) и
GitHub-версия загружены раздельно и прогнаны на **5 007** одинаковых кейсах.
JSON-выходы с `qualified`, `failed_conditions` и всеми `metrics` совпали
побайтово.

`result.qualified` detector и финальное решение monitor по `check_thresholds`
совпали во всех случаях. Это не отменяет архитектурный риск dual-source: при
изменении только config active monitor продолжит использовать
`FIXED_THRESHOLDS`. Текущие значения совпадают.

---

## 7. Проверка секретов

Просканировано:

- текущее дерево;
- **1 859** Git blobs;
- **24** коммита;
- tracked-артефакты и remote URL.

Результат:

- high-confidence секретов не найдено;
- единственное совпадение — учебный placeholder
  `your_bingx_api_key_here` в `test_bingx_migration.py`; это не секрет;
- tracked `.env`/БД/логов/private keys нет; есть только безопасный
  `.env.example`;
- remote URL не содержит credentials;
- крупные tracked-артефакты (`Default Project/EVRECONSE/historical_signals.json`,
  vendored `.devin`/`.codeium`) не являются production-кодом и не удалялись без
  решения владельца.

---

## 8. Production остался неизменным

Повторная read-only проверка после работ:

```text
ActiveState=active
MainPID=880596
NRestarts=0
Started=2026-10-17 08:02:29 UTC
```

Ключевые SHA-256 на сервере не изменились:

```text
f661e379...  realtime_capitulation_monitor_fixed.py
3b239a00...  src/strategy/capitulation_detector.py
bc51b697...  config/capitulation_thresholds.py
89369399...  src/exchange/bingx_fetcher.py
9ca77e0b...  src/data_provider/universe_provider.py
```

Не выполнялось restart/stop/reload, запись файлов, изменение прав, БД, логов,
`.env`, пакетов или systemd. Реальные Telegram/BingX-private/CMC/CoinGlass
действия не выполнялись.

---

## 9. Публикация и финальная проверка

**Первичный коммит с этим отчётом, документами и тестом:**
`2a27a62d95167aa6582cf4118fd8382df524551b`

**Коммит с evidence server-vs-GitHub synthetic comparison:**
`837144e716e839a9cbfac8ac752f4d9890b299bc`

**Metadata-follow-up:** отдельный commit, которым в этот раздел внесён точный
SHA публикации. Финальный HEAD после push проверяется в новом clone; его точный
SHA указан в финальном ответе.

Порядок публикации:

1. normal commit (без force-push, без rewrite history);
2. push в `origin/main`;
3. новый clone с GitHub;
4. проверка HEAD, clean worktree, наличия документов и теста;
5. повторный `pytest -q` в новом clone.

---

## 10. Остающиеся риски и рекомендации

1. **Universe stale / readonly DB.** Active snapshot: 574 символа,
   `fetched_at=2026-10-08T09:25:51Z`. `data/cmc_universe.db` принадлежит
   `root:root`, режим `0644`; процесс `evreconse` не может писать. Journal
   фиксирует `attempt to write a readonly database` при refresh 21 и 22
   октября. Это эксплуатационная проблема, не ошибка GitHub-кода. Исправление
   требует решения владельца и изменения прав/владельца БД; в рамках задачи не
   выполнялось.
2. **Dual-source thresholds.** `FIXED_THRESHOLDS` monitor и config detector
   сейчас совпадают, но не связаны автоматически. Изменение только config не
   изменит active signal.
3. **Stats-only версия в памяти.** Процесс загружен до поздней диагностической
   правки; побайтовая идентичность памяти не доказана. Для её загрузки нужен
   restart, который в рамках задачи запрещён.
4. **Live Telegram/private API.** Не проверялись.
5. **Telegram chat_id в journald.** Диагностические сообщения содержат
   идентификаторы получателей; это privacy/ops risk.
6. **Pending claims.** Автоматического resend нет; pending-сигналы требуют
   ручного вмешательства.
7. **API order.** Нет явной сортировки свечей; используется порядок ответа
   BingX и `reversed()`.
8. **Fetch window.** `startTime` не ограничивает выдачу при `limit=500`;
   фактически до 500 M15-свечей, а не строго 4 часа.
9. **Requirements.** GitHub dependency ranges и серверный freeze различаются;
   `requirements.txt` в GitHub имеет нестандартную UTF-16/CRLF-кодировку.
   На active pure-Python формулы это не влияет, но для воспроизведения
   окружения лучше нормализовать отдельным решением владельца.
10. **Hardcoded paths.** `/home/evreconse/...` сохранены как production
    behavior; локальный запуск требует адаптации.
11. **Inactive LW-001.** Содержит legacy/volume-пути и отличается текстами
    сообщений; не включать без отдельного решения.
12. **Duplicate `get_last_completed_candle`.** Определён дважды, определения
    идентичны; поведение не меняется.

---

## 11. Итоговый checklist

- [x] Свежий clone GitHub проверен.
- [x] Remote HEAD и ожидаемые коммиты проверены.
- [x] Production process/unit/entry point проверены read-only.
- [x] SHA-256 и mtime ключевых файлов сверены.
- [x] Разобрана поздняя stats-only правка.
- [x] Active Capitulation path прослежен полностью.
- [x] Формулы, пороги, операторы и границы проверены.
- [x] `result.qualified` vs `check_thresholds` проверены на синтетике.
- [x] Dedup, SQLite, Telegram-flow и retry/concurrency описаны.
- [x] Universe stale/readonly DB зафиксирован как ops risk.
- [x] Тесты/ruff/mypy/compile/imports выполнены.
- [x] Секреты и опасные артефакты просканированы.
- [x] Production не изменялся.
- [x] Документы созданы.
- [ ] Normal commit и push.
- [ ] Fresh-clone verification после push.

---

**Связанные документы:**

- `PROJECT_VERSION_COMPARISON.md` — три состояния и таблица расхождений;
- `STRATEGY_CAPITULATION_ABSORPTION.md` — полное описание active strategy;
- `PROJECT_FULL_DOCUMENTATION.md` — общая документация;
- `PROJECT_VERSION_VERIFICATION.md` — история сверки;
- `PROJECT_FINAL_AUDIT.md` — предыдущий финальный аудит;
- `LW001_PRODUCTION_SPEC.md` — inactive LW-001.

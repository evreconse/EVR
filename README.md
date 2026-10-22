# EVRECONSE

Автоматизированная система идентификации и оценки разворотных паттернов на
криптовалютном рынке.

## Status

**Production synchronization / shadow mode.** Активная стратегия на production —
**Capitulation / Absorption** (LONG-кандидаты, без реальной торговли). GitHub
синхронизирован с работающим серверным кодом; LW-001 сохранён как неактивная
legacy-стратегия. Полная побайтовая идентичность не заявляется: runtime-секреты,
БД, пути и окружение намеренно различаются, а stats-only правка активного файла
не была загружена процессом без restart.

- Активный entry point: `realtime_capitulation_monitor_fixed.py`
- Активный systemd unit на сервере: `evreconse.service` (в GitHub — безопасный
  шаблон, не точная копия серверного unit)
- LW-001: `realtime_lw001_monitor.py` — **не запущен**
- Секреты и runtime-данные в репозиторий не входят

Полное описание: `PROJECT_FULL_DOCUMENTATION.md`.
История сверки: `PROJECT_VERSION_VERIFICATION.md`.
Финальный аудит и ограничения: `PROJECT_FINAL_AUDIT.md`.
Спецификация LW-001: `LW001_PRODUCTION_SPEC.md`.

## Требования

- **Python 3.11+** (используется `datetime.UTC` и современная типизация)
- pip / venv

## Быстрый старт (Linux/macOS)

```bash
git clone https://github.com/evreconse/EVR.git
cd EVR

python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"

cp .env.example .env
# Заполните .env своими ключами. Не коммитьте .env.

pytest tests/ -v
```

## Быстрый старт (Windows PowerShell)

```powershell
git clone https://github.com/evreconse/EVR.git
cd EVR

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e ".[dev]"

Copy-Item .env.example .env
# Заполните .env своими ключами. Не коммитьте .env.

pytest tests/ -v
```

## Project Structure

```text
EVRECONSE/
├── src/                          # основной код и стратегии
│   ├── config/                   # конфигурация приложения и пороги
│   ├── data_provider/            # universe и рыночные данные
│   ├── exchange/                 # BingX fetcher, rate limiter, endpoints
│   └── strategy/                 # Capitulation и LW-001
├── tests/                        # unit/regression tests
├── realtime_capitulation_monitor_fixed.py  # активный production monitor
├── realtime_capitulation_monitor.py        # legacy shim
├── realtime_lw001_monitor.py               # неактивный LW-001 monitor
├── backfill_capitulation_signals.py        # исторический backfill
├── evreconse.service                       # безопасный service-шаблон
├── LW001_METRIC_SPEC.py                    # canonical LW-001 formulas
├── LW001_PRODUCTION_SPEC.md
├── PROJECT_FULL_DOCUMENTATION.md
├── PROJECT_VERSION_VERIFICATION.md
└── PROJECT_FINAL_AUDIT.md
```

## Основные команды

| Команда | Описание |
|---------|----------|
| `python realtime_capitulation_monitor_fixed.py` | Активный Capitulation monitor |
| `python realtime_capitulation_monitor.py` | Legacy-совместимый entry point (делегирует в активный) |
| `python realtime_lw001_monitor.py` | LW-001 legacy monitor; не включать без отдельного решения |
| `pytest tests/` | Все тесты |
| `pytest tests/test_server_sync_algorithms.py -v` | Регрессия серверных порогов и формул |
| `ruff check src tests LW001_METRIC_SPEC.py` | Линтинг |
| `mypy src/ tests/ --explicit-package-bases` | Проверка типов |

## Активная стратегия

Capitulation/Absorption, 15m, только закрытые свечи:

```text
red candle:        close < open
open_to_low_pct:   <= -5.0%
volume_30_ratio:   >= 2.0x
lw_body_ratio:     >= 1.0x
reclaim_pct:       >= 30.0%
all conditions:    AND
score gate:        none
```

Активный монитор работает в shadow mode: реальные ордера не отправляются.
Уведомления идут в Telegram; dedup хранится в SQLite `sent_signals.db`.

## LW-001 (inactive)

```text
range_pct:          >= 4.5%
body_pct:           >= 0.8%
lower_wick/body:    >= 1.3x
lower_wick/range:   >= 55.0%
open_to_low_pct:    <= -5.0%   # server value; older GitHub used -2.5%
red candle:         close < open
volume ratio:       NOT used
score gate:         none
```

LW-001 не является работающим сервисом. Не переключайте `evreconse.service` на
него без отдельного решения владельца.

## Конфигурация

- Секреты: `.env` (не коммитится), загружается через `python-dotenv`.
- Пороги Capitulation: `src/config/capitulation_thresholds.py`.
- Пороги LW-001: `LW001_METRIC_SPEC.py`.
- Service-шаблон: `evreconse.service`; секреты в unit-файл не записываются.

Переменные окружения имеют приоритет над статическими настройками.

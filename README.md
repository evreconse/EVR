# EVRECONSE

Автоматизированная система идентификации и оценки разворотных паттернов на криптовалютном рынке.

## Status

**Foundation Stage**

## Требования

- **Python 3.11+** (обязательно — используется `datetime.UTC`, добавлен в Python 3.11)
- pip / venv

## Быстрый старт (Linux/macOS)

```bash
# 1. Клонирование и вход в директорию
git clone https://github.com/evreconse/EVR.git
cd EVR

# 2. Создание виртуального окружения Python 3.11+
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Установка зависимостей
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Настройка конфигурации
cp .env.example .env
# Отредактируйте .env — добавьте свои API ключи (BingX, Telegram, CoinGlass, CMC)

# 5. Запуск тестов (проверка окружения)
pytest tests/ -v
```

## Быстрый старт (Windows PowerShell)

```powershell
# 1. Клонирование и вход в директорию
git clone https://github.com/evreconse/EVR.git
cd EVR

# 2. Создание виртуального окружения Python 3.11+
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Установка зависимостей
python -m pip install --upgrade pip
pip install -e ".[dev]"

# 4. Настройка конфигурации
Copy-Item .env.example .env
# Отредактируйте .env — добавьте свои API ключи

# 5. Запуск тестов
pytest tests/ -v
```

## Project Structure

```
EVRECONSE/
├── docs/              # Документация и спецификации
├── strategies/        # Описание торговых стратегий
├── research/          # Исследования
├── src/              # Исходный код
├── tests/            # Тесты
├── configs/          # Конфигурационные файлы
├── scripts/          # Скрипты
├── logs/             # Логи
├── data/             # Данные
│   ├── raw/          # Сырые данные
│   ├── processed/    # Обработанные данные
│   └── exports/      # Экспортированные данные
├── .github/          # GitHub конфигурация
├── README.md
├── .gitignore
├── .env.example
├── pyproject.toml
├── requirements.txt
├── config.yaml
└── LICENSE
```

## Documentation First Development

Проект следует принципу **Documentation First Development**: все решения сначала документируются, затем реализуются.

## Основные команды

| Команда | Описание |
|---------|----------|
| `python -m src.main` | Запуск основного приложения |
| `python -m src.main --dry-run` | Проверка инициализации без запуска |
| `pytest tests/` | Запуск тестов |
| `pytest tests/ --cov=src` | Тесты с покрытием |
| `ruff check src/` | Линтинг кода |
| `mypy src/` | Проверка типов |

## Запуск стратегий

### Capitulation/Absorption Monitor (SHADOW MODE)
```bash
python realtime_capitulation_monitor.py
```

### Исторический бэкфилл
```bash
# Dry run (без отправки в Telegram)
python backfill_capitulation_signals.py --dry-run

# С отправкой в Telegram
python backfill_capitulation_signals.py --send-telegram
```

## Конфигурация

Основные настройки в `config.yaml`:
- `exchange` — настройки BingX API
- `strategies` — параметры LW-001 и Capitulation
- `notifications` — Telegram bot token, chat ID
- `storage` — пути к данным и логам

Переменные окружения (`.env`) имеют приоритет над `config.yaml`.

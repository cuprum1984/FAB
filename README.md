# MyAggryBot

Telegram-бот для агрегации контента из Telegram-каналов и YouTube в форумные группы.

A Telegram bot that aggregates content from Telegram channels and YouTube into forum groups.

[Русский](#русский) | [English](#english)

---

## Русский

### Что делает бот

- Работает **только в супергруппах** с включённым форумом (regular groups не поддерживаются)
- Подписывает форумные группы на Telegram-каналы и YouTube-каналы
- Автоматически переслает новые посты в указанные топики
- Поддерживает несколько групп, топиков и источников
- Контроль лимитов, rate limiting, защита от спама после простоя
- 4 языка интерфейса: русский, украинский, белорусский, английский

### Быстрый старт (разработка)

**Требования:** Python 3.12+

```bash
# 1. Клонируй репозиторий
git clone <url>
cd FAB

# 2. Создай виртуальное окружение
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Скопируй .env.example в .env и заполни
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac

# 5. Запусти бота
python bot/main.py
```

В режиме разработки (`ENV=development` или не задано) бот использует:
- **SQLite** в памяти (без внешней БД)
- **MemoryStorage** для FSM
- **FileFakeRedis** — файл `redis_data.json` вместо Redis

База данных создаётся автоматически при первом запуске.

### Запуск в продакшене

#### 1. Инфраструктура (Docker)

```bash
docker-compose up -d
```

Поднимет PostgreSQL (порт 5432), Redis (порт 6379) и Redis Commander UI (порт 8081).

#### 2. Миграции

```bash
alembic upgrade head
```

#### 3. Запуск бота

```bash
BOT_TOKEN=xxx DATABASE_URL=postgresql+asyncpg://... ENV=production python bot/main.py
```

Или задай переменные в `.env`.

### Переменные окружения

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `BOT_TOKEN` | да | — | Токен бота от @BotFather |
| `DATABASE_URL` | да (prod) | — | Строка подключения PostgreSQL |
| `ENV` | нет | `development` | `development` / `production` |
| `SCHEDULE_INTERVAL` | нет | `3600` | Интервал проверки фидов (сек) |
| `FREE_PLAN_SOURCES_LIMIT` | нет | `25` | Макс. источников на админа |
| `FREE_PLAN_GROUPS_LIMIT` | нет | `5` | Макс. групп на админа |

Полный список переменных — в `.env.example`.

### Тесты

```bash
pytest -v                      # все тесты
pytest -k gdpr -v              # по ключевому слову
pytest tests/test_rate_limiter.py  # один файл
pytest --cov=core --cov=bot    # покрытие
```

Тесты работают в изоляции (SQLite in-memory, моки Telegram/Redis), внешние сервисы не нужны.

### Структура проекта

```
FAB/
├── bot/                # Telegram-слой (aiogram 3.x)
│   ├── handlers/       #   роутеры и хендлеры
│   ├── keyboards/      #   инлайн-клавиатуры
│   ├── middlewares/    #   DB, i18n, групповой фильтр
│   └── utils/          #   меню-навигация
├── core/               # Бизнес-логика
│   ├── models/         #   SQLAlchemy 2.0 модели
│   ├── services/       #   мониторинг, rate limiting, GDPR
│   └── parser/         #   парсинг Telegram и YouTube
├── locales/            # Локализация (en, ru, uk, be)
├── migrations/         # Alembic миграции
├── tests/              # pytest (~200+ тестов)
└── docs/               # Документация
```

### Стек

| Компонент | Технология |
|---|---|
| Бот | aiogram 3.x, Python 3.12+ |
| БД | PostgreSQL (asyncpg), SQLAlchemy 2.0 |
| Кэш/FSM | Redis (prod) / FileFakeRedis (dev) |
| Миграции | Alembic |
| Парсинг | BeautifulSoup4, aiohttp |
| Планировщик | APScheduler |

---

## English

### What it does

- Works **only in supergroups** with forums enabled (regular groups are not supported)
- Subscribes forum groups to Telegram channels and YouTube channels
- Automatically forwards new posts into specified topics
- Supports multiple groups, topics, and sources
- Rate limiting, spam protection after downtime, plan limits
- 4 interface languages: English, Russian, Ukrainian, Belarusian

### Quick start (development)

**Requirements:** Python 3.12+

```bash
# 1. Clone the repo
git clone <url>
cd FAB

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy .env.example to .env and fill in values
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac

# 5. Run the bot
python bot/main.py
```

In development mode (`ENV=development` or unset), the bot uses:
- **SQLite** in-memory (no external DB)
- **MemoryStorage** for FSM
- **FileFakeRedis** — `redis_data.json` file instead of Redis

The database is created automatically on first run.

### Production

#### 1. Infrastructure (Docker)

```bash
docker-compose up -d
```

Starts PostgreSQL (port 5432), Redis (port 6379), and Redis Commander UI (port 8081).

#### 2. Migrations

```bash
alembic upgrade head
```

#### 3. Run the bot

```bash
BOT_TOKEN=xxx DATABASE_URL=postgresql+asyncpg://... ENV=production python bot/main.py
```

Or set the variables in `.env`.

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | yes | — | Bot token from @BotFather |
| `DATABASE_URL` | yes (prod) | — | PostgreSQL connection string |
| `ENV` | no | `development` | `development` / `production` |
| `SCHEDULE_INTERVAL` | no | `3600` | Feed check interval (seconds) |
| `FREE_PLAN_SOURCES_LIMIT` | no | `25` | Max sources per admin |
| `FREE_PLAN_GROUPS_LIMIT` | no | `5` | Max groups per admin |

Full list — see `.env.example`.

### Tests

```bash
pytest -v                      # all tests
pytest -k gdpr -v              # by keyword
pytest tests/test_rate_limiter.py  # single file
pytest --cov=core --cov=bot    # coverage
```

Tests run in isolation (SQLite in-memory, mocked Telegram/Redis), no external services needed.

### Project structure

```
FAB/
├── bot/                # Telegram layer (aiogram 3.x)
│   ├── handlers/       #   routers and handlers
│   ├── keyboards/      #   inline keyboards
│   ├── middlewares/    #   DB, i18n, group filter
│   └── utils/          #   menu navigation
├── core/               # Business logic
│   ├── models/         #   SQLAlchemy 2.0 models
│   ├── services/       #   monitoring, rate limiting, GDPR
│   └── parser/         #   Telegram and YouTube parsing
├── locales/            # Localization (en, ru, uk, be)
├── migrations/         # Alembic migrations
├── tests/              # pytest (~200+ tests)
└── docs/               # Documentation
```

### Tech stack

| Component | Technology |
|---|---|
| Bot | aiogram 3.x, Python 3.12+ |
| Database | PostgreSQL (asyncpg), SQLAlchemy 2.0 |
| Cache/FSM | Redis (prod) / FileFakeRedis (dev) |
| Migrations | Alembic |
| Parsing | BeautifulSoup4, aiohttp |
| Scheduler | APScheduler |

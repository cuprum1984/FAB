# 🚀 Развёртывание MyAggryBot

**Версия:** 6.2  
**Последнее обновление:** 30 марта 2026

---

## 📋 Требования

### Обязательные

| Компонент | Версия | Назначение |
|-----------|--------|------------|
| Python | 3.12+ | Язык выполнения |
| PostgreSQL | 14+ | База данных |
| Telegram Bot Token | — | Токен из @BotFather |

### Опциональные

| Компонент | Версия | Назначение |
|-----------|--------|------------|
| Redis | 6+ | Кэш и очереди (для продакшена) |

---

## 🔧 Установка (Windows)

### 1. Клонирование репозитория

```bash
cd d:\PROJ\FAB
```

### 2. Создание виртуального окружения

```bash
py -m venv venv
venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка окружения

Скопируйте `.env.example` в `.env`:

```bash
copy .env.example .env
```

Заполните `.env`:

```bash
# Telegram Bot Token (из @BotFather)
BOT_TOKEN=your_bot_token

# PostgreSQL (Neon или локальный)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Redis (опционально, для продакшена)
REDIS_URL=redis://localhost:6379

# Rate Limiting (защита от бана)
RATE_LIMIT_TELEGRAM_TOKENS=20
RATE_LIMIT_TELEGRAM_REFILL=10.0
RATE_LIMIT_YOUTUBE_TOKENS=5
RATE_LIMIT_YOUTUBE_REFILL=1.0
RATE_LIMIT_GLOBAL_PER_MINUTE=60
```

### 5. Применение миграций БД

```bash
alembic upgrade head
```

### 6. Запуск бота

```bash
# Разработка (SQLite, MemoryStorage)
python bot/main.py

# Продакшен (PostgreSQL, RedisStorage)
# Убедитесь, что DATABASE_URL и REDIS_URL настроены
python bot/main.py
```

---

## 🔧 Установка (Linux/Docker)

### Docker Compose (рекомендуется)

```yaml
version: '3.8'

services:
  bot:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/myaggrybot
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=myaggrybot
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Запуск:

```bash
docker-compose up -d
```

---

## ⚙️ Конфигурация

### Переменные окружения

#### Обязательные

| Переменная | Пример | Описание |
|------------|--------|----------|
| `BOT_TOKEN` | `123456:ABC-DEF1234` | Токен бота из @BotFather |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Connection string PostgreSQL |

#### Опциональные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `REDIS_URL` | — | Redis connection string |
| `SCHEDULE_INTERVAL` | `3600` | Интервал мониторинга (сек) |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

#### Rate Limiting

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `RATE_LIMIT_TELEGRAM_TOKENS` | `20` | Ёмкость ведра Telegram |
| `RATE_LIMIT_TELEGRAM_REFILL` | `10.0` | Токенов/сек (Telegram) |
| `RATE_LIMIT_YOUTUBE_TOKENS` | `5` | Ёмкость ведра YouTube |
| `RATE_LIMIT_YOUTUBE_REFILL` | `1.0` | Токенов/сек (YouTube) |
| `RATE_LIMIT_GLOBAL_PER_MINUTE` | `60` | Глобальный лимит запросов/мин |

---

## 🗄️ База данных

### Применение миграций

```bash
# Применить все миграции
alembic upgrade head

# Откатить на одну миграцию
alembic downgrade -1

# Создать новую миграцию
alembic revision --autogenerate -m "Description"
```

### Таблицы

После применения миграций создаётся 10 таблиц:

1. `telegram_accounts` — пользователи
2. `user_preferences` — настройки пользователей
3. `managed_groups` — управляемые группы
4. `group_topics` — темы в группах
5. `content_sources` — источники
6. `source_subscriptions` — подписки групп
7. `topic_source_assignments` — назначения
8. `user_channel_subscriptions` — личные подписки
9. `cached_media` — кэш медиа
10. `user_cached_media` — пользовательский кэш

---

## 🧪 Тестирование

### Запуск всех тестов

```bash
pytest -v
```

### Запуск отдельных категорий

```bash
# Тесты очистки (GDPR)
pytest tests/test_cleanup.py -v

# Тесты назначений
pytest tests/test_topic_assignments.py -v

# Тесты Rate Limiting
pytest tests/test_rate_limiter.py -v

# Тесты с фильтром по имени
pytest -k gdpr -v
pytest -k cascade -v
```

### Покрытие тестов

| Категория | Тестов | Пройдено |
|-----------|--------|----------|
| Очистка (GDPR) | 14 | 14 ✅ |
| Destination Service | 23 | 23 ✅ |
| Monitoring Service | 9 | 9 ✅ |
| Назначения | 8 | 8 ✅ |
| Rate Limiting | 23 | 23 ✅ |
| YouTube | 11 | 11 ✅ |
| **ИТОГО** | **99** | **99 ✅** |

---

## 📊 Мониторинг

### Логи

Логи сохраняются в папку `logs/`:

```
logs/
├── bot_YYYY-MM-DD.log
├── monitor_YYYY-MM-DD.log
└── sender_YYYY-MM-DD.log
```

### Метрики

- Количество пользователей
- Количество групп и тем
- Количество источников
- Статистика парсинга
- Ошибки и таймауты

---

## 🔐 Безопасность

### Рекомендации

1. **Не коммитьте `.env`** — добавьте в `.gitignore`
2. **Используйте Redis** — для продакшена обязательно
3. **Настройте Rate Limiting** — защита от бана API
4. **Регулярно обновляйте зависимости** — `pip install --upgrade -r requirements.txt`

### GDPR

Бот автоматически удаляет неактивных пользователей:
- Без активности > 90 дней
- Каскадное удаление всех связанных данных

---

## 🔗 Связанные документы

- [`../overview.md`](../overview.md) — Полный отчёт по проекту
- [`architecture.md`](architecture.md) — Архитектура
- [`../../04-services/rate-limiting.md`](../../04-services/rate-limiting.md) — Rate Limiting

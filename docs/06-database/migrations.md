# 🔄 Alembic миграции

**Папка:** `migrations/`  
**Инструмент:** Alembic

---

## 📋 Обзор

Система миграций базы данных на основе Alembic.

---

## 📁 Структура

```
migrations/
├── env.py                     # Конфигурация окружения
├── script.py.mako             # Шаблон для новых миграций
├── README                     # Документация Alembic
└── versions/                  # Файлы миграций
    ├── 001_initial.py         # Начальная схема
    ├── 002_add_preferences.py # Предпочтения пользователей
    ├── 003_add_assignments.py # Назначения источников
    └── ...
```

---

## 🚀 Быстрый старт

### Применить все миграции

```bash
alembic upgrade head
```

### Откатить на одну миграцию

```bash
alembic downgrade -1
```

### Откатить к конкретной

```bash
alembic downgrade 002
```

### Создать новую миграцию

```bash
alembic revision --autogenerate -m "Description"
```

---

## 🔧 Команды Alembic

| Команда | Описание |
|---------|----------|
| `alembic upgrade head` | Применить все миграции |
| `alembic downgrade -1` | Откатить на одну назад |
| `alembic revision --autogenerate -m "..."` | Создать миграцию (auto) |
| `alembic revision -m "..."` | Создать миграцию (пустую) |
| `alembic current` | Текущая версия БД |
| `alembic history` | История миграций |
| `alembic heads` | Доступные миграции для применения |

---

## 📊 История миграций

| Версия | Файл | Описание |
|--------|------|----------|
| 001 | `001_initial.py` | Начальная схема (5 таблиц) |
| 002 | `002_add_preferences.py` | `user_preferences` |
| 003 | `003_add_assignments.py` | `topic_source_assignments` |
| 004 | `004_add_cache.py` | `cached_media`, `user_cached_media` |
| 005 | `005_add_indexes.py` | Индексы для производительности |

---

## 📝 Пример миграции

**Файл:** `migrations/versions/003_add_assignments.py`

```python
"""add topic source assignments

Revision ID: 003
Revises: 002
Create Date: 2026-02-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создать таблицу назначений
    op.create_table(
        'topic_source_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('topic_identifier', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], ['source_subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['topic_identifier'], ['group_topics.topic_identifier'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subscription_id', 'topic_identifier', name='uq_subscription_topic')
    )
    
    # Добавить индекс
    op.create_index(
        'ix_topic_source_assignments_topic',
        'topic_source_assignments',
        ['topic_identifier']
    )


def downgrade() -> None:
    # Удалить индекс
    op.drop_index(
        'ix_topic_source_assignments_topic',
        table_name='topic_source_assignments'
    )
    
    # Удалить таблицу
    op.drop_table('topic_source_assignments')
```

---

## ⚙️ Конфигурация (alembic.ini)

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://user:pass@localhost:5432/dbname

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -q

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic
```

---

## 🗄️ env.py

**Файл:** `migrations/env.py`

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import asyncio

from core.models import Base
from core.settings import settings

config = context.config

# Переопределить URL из настроек
config.set_main_option("sqlalchemy.url", settings.database_url_async)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск в оффлайн режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Запуск миграций в онлайне."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Асинхронный запуск миграций."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    
    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск в онлайн режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## ⚠️ Особенности

1. **Асинхронность:** Используется `asyncpg` для PostgreSQL
2. **Автогенерация:** `--autogenerate` создаёт миграцию на основе изменений моделей
3. **Транзакции:** Все миграции в транзакции (атомарность)
4. **Downgrade:** Каждая миграция имеет `downgrade()` для отката

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор БД
- [`schema.md`](schema.md) — Схема БД
- [`models.md`](models.md) — ORM модели

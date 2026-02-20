# migrations/env.py

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Добавляем корень проекта в sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Импортируем настройки и модели ПОСЛЕ добавления пути
from core.settings import settings
from core.models import Base

config = context.config

# Берём URL из настроек, если не задан в alembic.ini
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    """Эта функция получает уже синхронный Connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # render_as_batch=True,  # только если SQLite и нужно
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Онлайн-режим с async engine"""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        # echo=True,  # для отладки
        future=True,
        pool_pre_ping=True,
    )

    # Ключевой момент: открываем соединение → получаем AsyncConnection → используем run_sync на нём
    async def run_migrations_async():
        async with connectable.connect() as async_connection:
            # run_sync вызывается на AsyncConnection
            await async_connection.run_sync(do_run_migrations)

    # Запускаем асинхронную функцию синхронно (Alembic ожидает синхронный вызов)
    import asyncio
    asyncio.run(run_migrations_async())

    # Опционально: закрываем engine явно
    # await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
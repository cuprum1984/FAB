# core/database.py
"""
Модуль для работы с базой данных.
Версия: 1.1 (14 февраля 2026)
Изменения:
- Добавлена функция check_db_connection
- Улучшено логирование
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import logging

from core.settings import settings
from core.models import Base

logger = logging.getLogger(__name__)

# Параметры для create_async_engine
engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,  # проверяет соединение перед использованием
}

# Параметры пула только для PostgreSQL (SQLite не поддерживает)
if not settings.database_url_async.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 20,        # размер пула соединений
        "max_overflow": 10,     # дополнительные соединения при пике
        "pool_recycle": 3600,   # пересоздавать соединения каждый час
        "connect_args": {
            "command_timeout": 60,  # таймаут на выполнение команд
            "timeout": 60,          # таймаут на подключение
        }
    })

engine = create_async_engine(
    settings.database_url_async,
    **engine_kwargs
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Создать таблицы, если их нет"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise


# ========== НОВАЯ ФУНКЦИЯ ==========

async def check_db_connection() -> bool:
    """Проверить подключение к БД"""
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        logger.debug("✅ Подключение к БД работает")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        return False
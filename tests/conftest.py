"""
Конфигурация и фикстуры для тестов.
Использует SQLite в памяти для изоляции тестов.
"""
import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from core.models import Base


# Тестовая БД — SQLite в памяти (НЕ Neon!)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Примечание: event_loop fixture больше не нужен в pytest-asyncio >= 0.23
# Используем встроенный event_loop


@pytest.fixture(scope="function")
async def db_session():
    """
    Создаёт чистую БД для каждого теста.
    
    Как работает:
    1. Создаётся новый движок SQLite в памяти
    2. Создаются все таблицы (Base.metadata.create_all)
    3. Тест получает сессию
    4. После теста всё удаляется (память очищается)
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Создаём все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создаём фабрику сессий
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # После теста движок закрывается (память очищается)
    await engine.dispose()


@pytest.fixture
def sample_telegram_html():
    """Загружает HTML-фикстуру с постами"""
    with open("tests/fixtures/telegram_with_posts.html", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def empty_telegram_html():
    """Загружает пустую HTML-фикстуру"""
    with open("tests/fixtures/telegram_empty.html", "r", encoding="utf-8") as f:
        return f.read()

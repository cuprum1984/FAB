# 🧪 Фикстуры pytest

**Файл:** `tests/conftest.py`  
**Папка:** `tests/fixtures/`

---

## 📋 Обзор

Фикстуры для тестирования: БД, бот, данные.

---

## 📁 Структура

```
tests/
├── conftest.py                # Главные фикстуры
└── fixtures/
    ├── db.py                  # БД фикстуры
    ├── bot.py                 # Бот фикстуры
    └── data.py                # Тестовые данные
```

---

## 🔧 Главные фикстуры (conftest.py)

### `db_session`

Асинхронная сессия БД для тестов.

```python
@pytest.fixture
async def db_session():
    """Создать тестовую сессию БД."""
    async with async_session() as session:
        yield session
        await session.rollback()
```

**Использование:**
```python
async def test_user_create(db_session):
    user = await create_user(db_session, user_id=123)
    assert user is not None
```

---

### `clean_db`

Очистка БД после каждого теста.

```python
@pytest.fixture
async def clean_db(db_session):
    """Очистить БД после теста."""
    yield db_session
    # Очистка всех таблиц
    await db_session.execute(text("DELETE FROM user_cached_media"))
    await db_session.execute(text("DELETE FROM cached_media"))
    # ... и т.д.
```

---

### `test_user`

Создание тестового пользователя.

```python
@pytest.fixture
async def test_user(db_session):
    """Создать тестового пользователя."""
    user = TelegramAccount(
        telegram_account_id=123456,
        telegram_username="test_user",
        language_code="ru"
    )
    db_session.add(user)
    await db_session.commit()
    return user
```

**Использование:**
```python
async def test_user_exists(test_user):
    assert test_user.telegram_username == "test_user"
```

---

### `test_group`

Создание тестовой группы.

```python
@pytest.fixture
async def test_group(db_session, test_user):
    """Создать тестовую группу."""
    group = ManagedGroup(
        telegram_chat_id=-1001234567890,
        title="Test Group",
        added_by_telegram_account_id=test_user.telegram_account_id
    )
    db_session.add(group)
    await db_session.commit()
    return group
```

---

### `test_source`

Создание тестового источника.

```python
@pytest.fixture
async def test_source(db_session):
    """Создать тестовый источник (Telegram)."""
    source = ContentSource(
        source_type="telegram",
        username="durov",
        title="Durov's Channel"
    )
    db_session.add(source)
    await db_session.commit()
    return source
```

---

## 🗂️ Фикстуры данных (fixtures/data.py)

### Тестовые данные

```python
TEST_USERS = [
    {"id": 1, "username": "user1"},
    {"id": 2, "username": "user2"},
]

TEST_GROUPS = [
    {"chat_id": -1001, "title": "Group 1"},
    {"chat_id": -1002, "title": "Group 2"},
]

TEST_SOURCES = [
    {"type": "telegram", "username": "durov"},
    {"type": "youtube", "url": "https://youtube.com/@mrbeast"},
]
```

---

## 🤖 Фикстуры бота (fixtures/bot.py)

### `mock_bot`

Моковый бот для тестов.

```python
@pytest.fixture
def mock_bot():
    """Моковый бот."""
    return MockBot()
```

---

## 📊 Использование в тестах

### Пример теста с фикстурами

```python
import pytest
from sqlalchemy import select
from core.models import TelegramAccount, ManagedGroup

@pytest.mark.asyncio
async def test_create_group(test_user, db_session):
    """Тест создания группы."""
    # Arrange
    group = ManagedGroup(
        telegram_chat_id=-1001234567890,
        title="Test Group",
        added_by_telegram_account_id=test_user.telegram_account_id
    )
    
    # Act
    db_session.add(group)
    await db_session.commit()
    
    # Assert
    stmt = select(ManagedGroup).where(
        ManagedGroup.telegram_chat_id == -1001234567890
    )
    result = await db_session.execute(stmt)
    saved_group = result.scalar_one()
    
    assert saved_group is not None
    assert saved_group.title == "Test Group"
```

---

## ⚙️ Настройки pytest (pytest.ini)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    database: marks tests as database tests
```

---

## ⚠️ Особенности

1. **Асинхронность:** Все фикстуры async/await
2. **Изоляция:** Каждый тест в отдельной транзакции
3. **Rollback:** Изменения откатываются после теста
4. **Параметризация:** Можно передавать параметры в фикстуры

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор тестирования
- [`running.md`](running.md) — Запуск тестов
- [`categories.md`](categories.md) — Категории тестов

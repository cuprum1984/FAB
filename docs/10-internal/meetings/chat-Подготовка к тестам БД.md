# 📋 ПРОМПТ ДЛЯ QWEN CODE: Настройка тестирования MyAggryBot

**Версия:** 1.0  
**Дата:** 22 февраля 2026  
**Проект:** MyAggryBot (Telegram агрегатор контента)

---

## 🎯 ЗАДАЧА

Настроить инфраструктуру для тестирования БД и сервисов **без изменения основной архитектуры проекта**. Тесты должны работать с SQLite (локально), а не с Neon.tech (продакшен).

---

## ⚠️ КРИТИЧЕСКИЕ ОГРАНИЧЕНИЯ (НЕ ЛОМАТЬ!)

| Что | Запрет | Почему |
|-----|--------|--------|
| `core/settings.py` | ❌ Не менять логику загрузки | Используется в продакшене |
| `core/database.py` | ❌ Не удалять глобальный engine | Бот зависит от него |
| `bot/main.py` | ❌ Не менять точку входа | Продакшен код |
| `core/models.py` | ❌ Не менять структуру таблиц | 10 таблиц, миграции готовы |
| Neon.tech | ❌ **НИКОГДА не подключаться в тестах** | Боевая база с реальными данными |

---

## ✅ ЧТО НУЖНО СОЗДАТЬ

### 1. Тестовые настройки (`tests/test_settings.py`)

**Задача:** Переопределить `DATABASE_URL` для тестов **до импорта core модулей**.

**Требования:**
```python
# tests/test_settings.py
import os

# 🔥 ЭТО ДОЛЖНО БЫТЬ ПЕРВЫМ, ДО ЛЮБЫХ ИМПОРТОВ ИЗ core/
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENV"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"  # Тихие тесты

# Теперь можно импортировать core
from core.settings import settings
```

**Почему:** `pydantic_settings` читает переменные окружения при создании класса `Settings`. Если переопределить после импорта — будет поздно.

---

### 2. Обновить `tests/conftest.py` (Безопасность)

**Текущая проблема:** В `conftest.py` нет переопределения `DATABASE_URL` до импортов.

**Что добавить в начало файла:**
```python
# tests/conftest.py
import os

# 🔥 КРИТИЧНО: Переопределить ДО импортов из core/
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENV"] = "test"

# Теперь импорты безопасны
import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.models import Base
```

**Фикстура `db_session`:** Уже есть, оставить как есть (SQLite в памяти, чистая БД для каждого теста).

---

### 3. Локальная SQLite БД для ручного тестирования

**Задача:** Создать возможность запускать бота с локальной SQLite БД для отладки **без Neon**.

**Что создать:**

#### A. Файл `.env.local` (в корне проекта)
```bash
# .env.local - для локальной разработки с SQLite
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
DATABASE_URL=sqlite+aiosqlite://./local_dev.db
ENV=development
LOG_LEVEL=DEBUG
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### B. Файл `.gitignore` (добавить)
```
# Локальные БД
*.db
local_dev.db
test_*.db

# Логи
logs/
*.log

# Python
__pycache__/
*.pyc
.pytest_cache/
```

#### C. Инструкция для запуска с локальной БД
```bash
# 1. Скопировать .env.local в .env (временная замена)
cp .env.local .env

# 2. Запустить бота
python bot/main.py

# 3. После тестов — вернуть .env с Neon
# (или использовать переменную окружения)
```

**Альтернатива (лучше):** Запуск с переопределением в командной строке:
```bash
DATABASE_URL=sqlite+aiosqlite://./local_dev.db python bot/main.py
```

---

### 4. Файл `pytest.ini` (в корне проекта)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

**Зачем:** `pytest-asyncio` требует явного указания режима. `auto` позволяет не писать `@pytest.mark.asyncio` в каждом тесте.

---

### 5. Структура папки `tests/`

```
tests/
├── __init__.py
├── conftest.py              # ✅ Уже есть (обновить переопределение ENV)
├── test_settings.py         # 🔥 Создать (переопределение настроек)
├── test_cleanup.py          # 🔥 Создать (GDPR тесты)
├── test_database_logic.py   # 🔥 Создать (назначения, подписки)
├── fixtures/
│   ├── telegram_with_posts.html
│   └── telegram_empty.html
└── __pycache__/             # В .gitignore
```

---

## 📝 ИНСТРУКЦИЯ ДЛЯ РАЗРАБОТЧИКА (ВАС)

### Шаг 1: Безопасность тестов (10 минут)

```bash
# 1. Откройте tests/conftest.py
# 2. Добавьте в самые первые строки (ДО импортов core/):
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENV"] = "test"

# 3. Проверьте, что нет импортов из core до этой строки
```

### Шаг 2: Локальная БД для отладки (5 минут)

```bash
# 1. Создайте файл .env.local в корне проекта
# 2. Скопируйте содержимое из раздела выше
# 3. Добавьте *.db в .gitignore

# Для запуска с локальной БД:
DATABASE_URL=sqlite+aiosqlite://./local_dev.db python bot/main.py

# Для запуска с Neon (продакшен):
python bot/main.py  # (использует .env с DATABASE_URL=postgresql://...)
```

### Шаг 3: Запуск тестов (2 минуты)

```bash
# Запустить все тесты
pytest

# Запустить только тесты очистки (GDPR)
pytest -k cleanup

# Запустить с подробным выводом
pytest -v

# Запустить один файл
pytest tests/test_cleanup.py
```

### Шаг 4: Проверка безопасности (Критично!)

```bash
# 1. Запустите тесты
pytest -v

# 2. Проверьте вывод — НЕ должно быть:
#    - "postgresql://"
#    - "neon.tech"
#    - Ваших паролей от БД

# 3. Если видите — СТОП! Исправьте conftest.py
```

---

## 🧪 ПРИМЕР ТЕСТА (GDPR)

**Файл:** `tests/test_cleanup.py`

```python
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from core.models import TelegramAccount
from core.services.cleanup_service import CleanupService

@pytest.mark.asyncio
async def test_gdpr_removes_blocked_user_old(db_session):
    """GDPR удаляет заблокированных пользователей >30 дней"""
    
    # 1️⃣ ПОДГОТОВКА — пользователь заблокирован 31 день назад
    old_date = datetime.utcnow() - timedelta(days=31)
    user = TelegramAccount(
        telegram_account_id=99999,
        telegram_username="test_user",
        telegram_first_name="Test",
        is_bot_blocked=True,
        last_activity=old_date
    )
    db_session.add(user)
    await db_session.commit()
    
    # 2️⃣ ДЕЙСТВИЕ — запускаем очистку
    cleanup = CleanupService()
    await cleanup._cleanup_gdpr(db_session)  # ✅ Передаём сессию явно
    await db_session.commit()
    
    # 3️⃣ ПРОВЕРКА — пользователь удалён
    result = await db_session.execute(
        select(TelegramAccount).where(TelegramAccount.telegram_account_id == 99999)
    )
    deleted_user = result.scalar()
    
    assert deleted_user is None, "Заблокированный пользователь должен быть удалён"

@pytest.mark.asyncio
async def test_gdpr_keeps_active_user(db_session):
    """GDPR НЕ удаляет активных пользователей (<30 дней)"""
    
    # 1️⃣ ПОДГОТОВКА — пользователь активен (вчера)
    recent_date = datetime.utcnow() - timedelta(days=1)
    user = TelegramAccount(
        telegram_account_id=88888,
        telegram_username="active_user",
        telegram_first_name="Active",
        is_bot_blocked=True,  # Заблокирован, но недавно
        last_activity=recent_date
    )
    db_session.add(user)
    await db_session.commit()
    
    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_gdpr(db_session)
    await db_session.commit()
    
    # 3️⃣ ПРОВЕРКА — пользователь остался
    result = await db_session.execute(
        select(TelegramAccount).where(TelegramAccount.telegram_account_id == 88888)
    )
    active_user = result.scalar()
    
    assert active_user is not None, "Активный пользователь НЕ должен быть удалён"
```

---

## ⚠️ ПРОВЕРКА ПЕРЕД КОМИТОМ

```bash
# 1. Все тесты зелёные
pytest

# 2. Нет WARNING о coroutine not awaited
pytest -v 2>&1 | grep -i "warning"

# 3. conftest.py не содержит продакшен-паролей
cat tests/conftest.py | grep -i "neon\|password"

# 4. .env не закоммичен (только .env.example)
git status | grep ".env"

# 5. *.db в .gitignore
cat .gitignore | grep ".db"
```

---

## 🎯 ПРИОРИТЕТЫ ДЛЯ QWEN CODE

| Приоритет | Задача | Файл | Время |
|-----------|--------|------|-------|
| 🔴 1 | Переопределение ENV в `conftest.py` | `tests/conftest.py` | 5 мин |
| 🔴 2 | Создать `pytest.ini` | `pytest.ini` | 2 мин |
| 🔴 3 | Создать `.env.local` | `.env.local` | 2 мин |
| 🟡 4 | Добавить `.db` в `.gitignore` | `.gitignore` | 1 мин |
| 🟡 5 | Создать шаблон теста GDPR | `tests/test_cleanup.py` | 15 мин |
| 🟢 6 | Создать фикстуры HTML | `tests/fixtures/*.html` | 10 мин |

---

## 📊 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После выполнения этой задачи:

| Что | Было | Стало |
|-----|------|-------|
| Тесты БД | ❌ Подключались к Neon | ✅ SQLite в памяти |
| Безопасность | ⚠️ Риск утечки данных | ✅ Изолированы |
| Локальная отладка | ❌ Только Neon | ✅ SQLite локально |
| Запуск тестов | ❌ Не настроен | ✅ `pytest` работает |
| Архитектура | ✅ Не изменена | ✅ Не изменена |

---

## 🔗 ССЫЛКИ НА ФАЙЛЫ ПРОЕКТА

- `core/settings.py` — Настройки (не менять)
- `core/database.py` — Подключение к БД (не менять)
- `core/models.py` — 10 таблиц ORM (не менять)
- `core/services/cleanup_service.py` — Сервис очистки (тестировать)
- `tests/conftest.py` — Фикстуры тестов (обновить)
- `tech_prompt_v7.1.md` — Документация проекта

---

## 💡 ВАЖНЫЕ ЗАМЕТКИ ДЛЯ QWEN CODE

1. **Не создавайте новые глобальные переменные** в `core/` — это усложнит тестирование.
2. **Не меняйте сигнатуры функций** в продакшене — используйте optional параметры для тестов.
3. **Все тесты должны быть асинхронными** (`async def test_*`) — проект на asyncio.
4. **Не используйте `print()` в тестах** — используйте `logger` или фикстуры pytest.
5. **Каждый тест должен быть независимым** — фикстура `db_session` создаёт чистую БД.

---

## ✅ ЧЕК-ЛИСТ ЗАВЕРШЕНИЯ

- [ ] `tests/conftest.py` переопределяет `DATABASE_URL` до импортов
- [ ] `pytest.ini` создан в корне проекта
- [ ] `.env.local` создан для локальной отладки
- [ ] `*.db` добавлен в `.gitignore`
- [ ] `tests/test_cleanup.py` содержит 2+ теста на GDPR
- [ ] `tests/fixtures/` содержит HTML фикстуры
- [ ] `pytest` запускается без ошибок
- [ ] Тесты не подключаются к Neon (проверить вывод)

---

**Готово к выполнению!** 🚀

Если Qwen Code задаст вопросы — напомните: **архитектура продакшена неприкосновенна, тесты изолированы в папке `tests/`**.
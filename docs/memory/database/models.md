# ORM Models — Контекст

**Последнее обновление:** 2026-03-28  
**Версия:** 6.3

---

## 📋 Что это

SQLAlchemy ORM модели для работы с БД.

**Последние изменения:**
- **v6.3:** Удалена модель `UserCachedMedia`

---

## 🎯 Ключевые файлы

- `core/models/__init__.py` — экспорт
- `core/models/base.py` — базовый класс
- `core/models/users.py` — пользователи
- `core/models/groups.py` — группы и темы
- `core/models/sources.py` — источники
- `core/models/assignments.py` — назначения
- `core/models/cache.py` — кэш

---

## 📊 Модели

```python
TelegramAccount       # Пользователь
UserPreferences       # Настройки
ManagedGroup          # Группа
GroupTopic            # Тема
ContentSource         # Источник
SourceSubscription    # Подписка группы
TopicSourceAssignment # Назначение в тему
UserChannelSubscription  # Личная подписка
CachedMedia           # Кэш медиа (источник)
```

**Удалено:**
- ~~`UserCachedMedia`~~ — v6.3 (избыточность)

---

## ⚠️ Важные решения

- **v5.4:** Разделение на 7 модулей
- **v5.4:** Базовый класс `Base`
- **v6.0:** Индексы для ForeignKey

---

## 🔧 Использование

```python
from core.models import TelegramAccount, UserPreferences

# Получить пользователя
user = await session.get(TelegramAccount, user_id)

# Создать предпочтения
prefs = UserPreferences(user_id=user_id, language='ru')
```

---

## 🔗 Связанные документы

- `docs/06-database/models.md` — полная документация
- `docs/06-database/schema.md` — схема БД

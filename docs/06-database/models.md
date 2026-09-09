# 📊 ORM модели

**Папка:** `core/models/`

---

## 📋 Обзор

SQLAlchemy ORM модели для работы с базой данных.

---

## 📁 Структура

```
core/models/
├── base.py                    # Базовый класс
├── users.py                   # Пользователи
├── groups.py                  # Группы и темы
├── sources.py                 # Источники и подписки
├── assignments.py             # Назначения
├── subscriptions.py           # Личные подписки
└── cache.py                   # Кэш медиа
```

---

## 🎯 Модели

### `Base` (base.py)

Базовый класс для всех моделей.

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

---

### `TelegramAccount` (users.py)

Пользователь бота.

```python
class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"
    
    telegram_account_id: Mapped[int] = mapped_column(primary_key=True)
    telegram_username: Mapped[str | None]
    telegram_first_name: Mapped[str | None]
    telegram_last_name: Mapped[str | None]
    language_code: Mapped[str] = mapped_column(String(10), default='en')
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

**Поля:**
- `telegram_account_id` — ID пользователя Telegram (PK)
- `telegram_username` — Username
- `telegram_first_name` — Имя
- `telegram_last_name` — Фамилия
- `language_code` — Код языка

---

### `UserPreferences` (users.py)

Настройки пользователя.

```python
class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('telegram_accounts.telegram_account_id'), unique=True)
    language: Mapped[str] = mapped_column(String(10), default='ru')
    icon_style: Mapped[str] = mapped_column(String(50), default='classic')
    notifications_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

**Связи:**
- `user_id` → `TelegramAccount.telegram_account_id` (FK, unique)

---

### `ManagedGroup` (groups.py)

Управляемая группа.

```python
class ManagedGroup(Base):
    __tablename__ = "managed_groups"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(String(255))
    added_by_telegram_account_id: Mapped[int | None] = mapped_column(ForeignKey('telegram_accounts.telegram_account_id'))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

**Связи:**
- `telegram_chat_id` — Уникальный ID чата
- `added_by_telegram_account_id` → `TelegramAccount` (FK)

---

### `GroupTopic` (groups.py)

Тема в группе.

```python
class GroupTopic(Base):
    __tablename__ = "group_topics"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(ForeignKey('managed_groups.telegram_chat_id', ondelete='CASCADE'))
    topic_identifier: Mapped[int]
    name: Mapped[str] = mapped_column(String(255))
    created_by_telegram_account_id: Mapped[int | None] = mapped_column(ForeignKey('telegram_accounts.telegram_account_id'))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    
    __table_args__ = (
        UniqueConstraint('telegram_chat_id', 'topic_identifier', name='uq_chat_topic'),
    )
```

**Связи:**
- `telegram_chat_id` → `ManagedGroup` (CASCADE)
- `topic_identifier` — ID темы в Telegram
- Уникальность: `(telegram_chat_id, topic_identifier)`

---

### `ContentSource` (sources.py)

Источник контента.

```python
class ContentSource(Base):
    __tablename__ = "content_sources"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50))  # 'telegram', 'youtube'
    username: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(512))
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    last_check: Mapped[datetime | None]
    last_video_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

**Поля:**
- `source_type` — Тип источника
- `username` — Для Telegram (@durov)
- `url` — Для YouTube
- `last_check` — Дата последней проверки
- `last_video_id` — ID последнего видео (YouTube)

---

### `SourceSubscription` (sources.py)

Подписка группы на источник.

```python
class SourceSubscription(Base):
    __tablename__ = "source_subscriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_global_id: Mapped[int | None] = mapped_column(ForeignKey('content_sources.id', ondelete='SET NULL'))
    telegram_chat_id: Mapped[int] = mapped_column(ForeignKey('managed_groups.telegram_chat_id', ondelete='CASCADE'))
    added_by_telegram_account_id: Mapped[int | None] = mapped_column(ForeignKey('telegram_accounts.telegram_account_id'))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    
    __table_args__ = (
        UniqueConstraint('source_global_id', 'telegram_chat_id', name='uq_source_chat'),
    )
```

**Связи:**
- `source_global_id` → `ContentSource` (SET NULL)
- `telegram_chat_id` → `ManagedGroup` (CASCADE)
- Уникальность: `(source_global_id, telegram_chat_id)`

---

### `TopicSourceAssignment` (assignments.py)

Назначение источника в тему.

```python
class TopicSourceAssignment(Base):
    __tablename__ = "topic_source_assignments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey('source_subscriptions.id', ondelete='CASCADE'))
    topic_identifier: Mapped[int] = mapped_column(ForeignKey('group_topics.topic_identifier', ondelete='CASCADE'))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    
    __table_args__ = (
        UniqueConstraint('subscription_id', 'topic_identifier', name='uq_subscription_topic'),
    )
```

**Связи:**
- `subscription_id` → `SourceSubscription` (CASCADE)
- `topic_identifier` → `GroupTopic` (CASCADE)
- Уникальность: `(subscription_id, topic_identifier)`

---

### `UserChannelSubscription` (subscriptions.py)

Личная подписка пользователя.

```python
class UserChannelSubscription(Base):
    __tablename__ = "user_channel_subscriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('telegram_accounts.telegram_account_id', ondelete='CASCADE'))
    source_global_id: Mapped[int] = mapped_column(ForeignKey('content_sources.id', ondelete='CASCADE'))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'source_global_id', name='uq_user_source'),
    )
```

**Связи:**
- `user_id` → `TelegramAccount` (CASCADE)
- `source_global_id` → `ContentSource` (CASCADE)

---

### `CachedMedia` (cache.py)

Кэш медиафайлов (привязан к источнику).

```python
class CachedMedia(Base):
    __tablename__ = "cached_media"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_global_id: Mapped[str] = mapped_column(ForeignKey('content_sources.source_global_id', ondelete='CASCADE'))
    post_id: Mapped[str] = mapped_column(String(100))
    file_id: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(50))  # 'photo', 'video', 'document'
    file_size: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime]
    last_used: Mapped[datetime | None]
    
    __table_args__ = (
        UniqueConstraint('source_global_id', 'post_id', name='uq_source_post'),
    )
```

---

## 🗑️ Удалённые модели

### `UserCachedMedia` (удалена в v6.3)

**Причина удаления:**
- Дублировала информацию из `CachedMedia`
- Избыточность: один файл кэшировался для всех пользователей
- Упрощение: кэш на уровне источника, не пользователя

**Файл:** Удалён из `core/models/cache.py`  
**Дата удаления:** 28 марта 2026 (v6.3)

---

## 🔗 Связи между моделями

```
TelegramAccount
    ├─< UserPreferences (1:1)
    ├─< ManagedGroup (1:M)
    ├─< GroupTopic (1:M)
    └─< UserChannelSubscription (1:M)

ManagedGroup
    ├─< GroupTopic (1:M, CASCADE)
    └─< SourceSubscription (1:M, CASCADE)

GroupTopic
    └─< TopicSourceAssignment (1:M, CASCADE)

ContentSource
    ├─< SourceSubscription (1:M, SET NULL)
    └─< UserChannelSubscription (1:M, CASCADE)

SourceSubscription
    └─< TopicSourceAssignment (1:M, CASCADE)
```

---

## 🧪 Использование

```python
from sqlalchemy import select
from core.models import TelegramAccount, UserPreferences

# Получить пользователя
stmt = select(TelegramAccount).where(
    TelegramAccount.telegram_account_id == user_id
)
result = await session.execute(stmt)
user = result.scalar_one_or_none()

# Создать предпочтения
prefs = UserPreferences(user_id=user_id, language='ru')
session.add(prefs)
await session.commit()
```

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор БД
- [`schema.md`](schema.md) — Схема БД
- [`migrations.md`](migrations.md) — Миграции

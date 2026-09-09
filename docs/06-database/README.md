# 🗄️ База данных

**Папка:** `core/models/`

---

## 📋 Обзор

ORM модели SQLAlchemy для работы с PostgreSQL.

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

## 📊 Таблицы (10 штук)

| Таблица | Модель | Файл | Описание |
|---------|--------|------|----------|
| `telegram_accounts` | `TelegramAccount` | [`users.py`](users.md) | Пользователи бота |
| `user_preferences` | `UserPreferences` | [`users.md`](users.md) | Настройки пользователей |
| `managed_groups` | `ManagedGroup` | [`groups.py`](groups.md) | Управляемые группы |
| `group_topics` | `GroupTopic` | [`groups.md`](groups.md) | Темы в группах |
| `content_sources` | `ContentSource` | [`sources.py`](sources.md) | Источники (TG, YouTube) |
| `source_subscriptions` | `SourceSubscription` | [`sources.md`](sources.md) | Подписки групп на источники |
| `topic_source_assignments` | `TopicSourceAssignment` | [`assignments.md`](assignments.md) | Назначения источников в темы |
| `user_channel_subscriptions` | `UserChannelSubscription` | [`subscriptions.md`](subscriptions.md) | Личные подписки пользователей |
| `cached_media` | `CachedMedia` | [`cache.md`](cache.md) | Кэш медиафайлов |
| `user_cached_media` | `UserCachedMedia` | [`cache.md`](cache.md) | Пользовательский кэш |

---

## 🔗 Foreign Key связи

```
TelegramAccount
    ← GroupTopic.created_by_telegram_account_id
    ← SourceSubscription.added_by_telegram_account_id
    ← UserChannelSubscription.user_id

ManagedGroup
    ← GroupTopic.telegram_chat_id (CASCADE)
    ← SourceSubscription.telegram_chat_id (CASCADE)

GroupTopic
    ← TopicSourceAssignment.topic_identifier (CASCADE)

ContentSource
    ← SourceSubscription.source_global_id (SET NULL)
    ← UserChannelSubscription.source_global_id (CASCADE)

SourceSubscription
    ← TopicSourceAssignment.subscription_id (CASCADE)
```

---

## 📝 Документы

| Файл | Описание | Статус |
|------|----------|--------|
| [`schema.md`](schema.md) | Схема БД, связи | 🔴 Не начато |
| [`models.md`](models.md) | ORM модели | 🔴 Не начато |
| [`migrations.md`](migrations.md) | Alembic миграции | 🔴 Не начато |

---

## 🔗 Связанные документы

- [`../04-services/README.md`](../04-services/README.md) — Сервисы
- [`../04-services/destinations.md`](../04-services/destinations.md) — Destination Service
- [`../../migrations/`](../../migrations/) — Миграции

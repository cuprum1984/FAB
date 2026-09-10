# Database Schema — Контекст

**Последнее обновление:** 2026-03-28  
**Версия:** 6.3

---

## 📋 Что это

Схема PostgreSQL базы данных (9 таблиц).

**Последние изменения:**
- **v6.3:** Удалена `user_cached_media` (оптимизация кэширования)

---

## 🎯 Ключевые файлы

- `core/models/` — ORM модели (7 модулей)
- `migrations/versions/` — миграции Alembic

---

## 🗄️ Таблицы

| Таблица | Назначение |
|---------|------------|
| `telegram_accounts` | Пользователи |
| `user_preferences` | Настройки пользователей |
| `managed_groups` | Управляемые группы |
| `group_topics` | Темы в группах |
| `content_sources` | Источники (TG, YouTube) |
| `source_subscriptions` | Подписки групп |
| `topic_source_assignments` | Назначения в темы |
| `user_channel_subscriptions` | Личные подписки |
| `cached_media` | Кэш медиа (источник) |

**Удалено:**
- ~~`user_cached_media`~~ — удалена в v6.3 (избыточность)

---

## 🔗 FK связи

```
TelegramAccount → UserPreferences (1:1)
TelegramAccount → ManagedGroup (1:M)
ManagedGroup → GroupTopic (1:M, CASCADE)
GroupTopic → TopicSourceAssignment (1:M, CASCADE)
ContentSource → SourceSubscription (1:M, SET NULL)
SourceSubscription → TopicSourceAssignment (1:M, CASCADE)
```

---

## ⚠️ Важные решения

- **v4.0:** `topic_source_assignments` (Назначения)
- **v5.4:** Разделение моделей на модули
- **v6.2:** Индексы для производительности

---

## 🔗 Связанные документы

- `docs/06-database/schema.md` — полная документация
- `docs/06-database/models.md` — ORM модели
- `docs/06-database/migrations.md` — миграции

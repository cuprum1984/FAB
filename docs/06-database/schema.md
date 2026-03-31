# 📊 Схема базы данных

**Версия:** 6.3
**Последнее обновление:** 28 марта 2026

---

## 📋 Обзор

Схема PostgreSQL базы данных MyAggryBot.

**Последние изменения:**
- **v6.3:** Удалена таблица `user_cached_media` (оптимизация кэширования)

---

## 🗄️ Таблицы (9 штук)

### 1. telegram_accounts

Пользователи бота.

```sql
CREATE TABLE telegram_accounts (
    telegram_account_id BIGINT PRIMARY KEY,
    telegram_username VARCHAR(255),
    telegram_first_name VARCHAR(255),
    telegram_last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Поля:**
- `telegram_account_id` — ID пользователя Telegram
- `telegram_username` — Username
- `telegram_first_name` — Имя
- `telegram_last_name` — Фамилия
- `language_code` — Код языка

---

### 2. user_preferences

Настройки пользователей.

```sql
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES telegram_accounts(telegram_account_id),
    language VARCHAR(10) DEFAULT 'ru',
    icon_style VARCHAR(50) DEFAULT 'classic',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 3. managed_groups

Управляемые группы.

```sql
CREATE TABLE managed_groups (
    id SERIAL PRIMARY KEY,
    telegram_chat_id BIGINT UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    added_by_telegram_account_id BIGINT REFERENCES telegram_accounts(telegram_account_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 4. group_topics

Темы в группах.

```sql
CREATE TABLE group_topics (
    id SERIAL PRIMARY KEY,
    telegram_chat_id BIGINT REFERENCES managed_groups(telegram_chat_id) ON DELETE CASCADE,
    topic_identifier BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_by_telegram_account_id BIGINT REFERENCES telegram_accounts(telegram_account_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(telegram_chat_id, topic_identifier)
);
```

---

### 5. content_sources

Источники контента.

```sql
CREATE TABLE content_sources (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,  -- 'telegram', 'youtube'
    username VARCHAR(255),             -- Для Telegram
    url VARCHAR(512),                  -- Для YouTube
    title VARCHAR(255),
    description TEXT,
    last_check TIMESTAMP,
    last_video_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 6. source_subscriptions

Подписки групп на источники.

```sql
CREATE TABLE source_subscriptions (
    id SERIAL PRIMARY KEY,
    source_global_id INTEGER REFERENCES content_sources(id) ON DELETE SET NULL,
    telegram_chat_id BIGINT REFERENCES managed_groups(telegram_chat_id) ON DELETE CASCADE,
    added_by_telegram_account_id BIGINT REFERENCES telegram_accounts(telegram_account_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_global_id, telegram_chat_id)
);
```

---

### 7. topic_source_assignments

Назначения источников в темы.

```sql
CREATE TABLE topic_source_assignments (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES source_subscriptions(id) ON DELETE CASCADE,
    topic_identifier BIGINT REFERENCES group_topics(topic_identifier) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subscription_id, topic_identifier)
);
```

---

### 8. user_channel_subscriptions

Личные подписки пользователей.

```sql
CREATE TABLE user_channel_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES telegram_accounts(telegram_account_id) ON DELETE CASCADE,
    source_global_id INTEGER REFERENCES content_sources(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, source_global_id)
);
```

---

### 9. cached_media

Кэш медиафайлов (привязан к источнику).

```sql
CREATE TABLE cached_media (
    id SERIAL PRIMARY KEY,
    source_global_id VARCHAR(256) REFERENCES content_sources(source_global_id) ON DELETE CASCADE,
    post_id VARCHAR(100) NOT NULL,
    file_id VARCHAR(512) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_used TIMESTAMP,
    UNIQUE(source_global_id, post_id)
);
```

**Индексы:**
- `idx_cached_media_source` — по источнику
- `idx_cached_media_file_id` — по file_id
- `idx_cached_media_expires` — по сроку действия

---

## 🗑️ Удалённые таблицы

### `user_cached_media` (удалена в v6.3)

**Причина удаления:**
- Дублировала информацию из `cached_media`
- Избыточность: один файл кэшировался для всех пользователей
- Упрощение: кэш на уровне источника, не пользователя

**Дата удаления:** 28 марта 2026 (v6.3)

---

## 🔗 Индексы

```sql
-- Для ускорения поиска
CREATE INDEX idx_telegram_accounts_username ON telegram_accounts(telegram_username);
CREATE INDEX idx_managed_groups_chat_id ON managed_groups(telegram_chat_id);
CREATE INDEX idx_group_topics_chat_id ON group_topics(telegram_chat_id);
CREATE INDEX idx_content_sources_type ON content_sources(source_type);
CREATE INDEX idx_source_subscriptions_chat_id ON source_subscriptions(telegram_chat_id);
CREATE INDEX idx_topic_source_assignments_topic ON topic_source_assignments(topic_identifier);
```

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор БД
- [`models.md`](models.md) — ORM модели
- [`migrations.md`](migrations.md) — Миграции

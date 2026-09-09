# 🧹 GDPR Очистка (Cleanup Service)

**Папка:** `core/services/cleanup/`
**Версия:** 6.6 (2 апреля 2026)

---

## 📋 Обзор

Автоматическая очистка неактивных пользователей и связанных данных (GDPR compliance).

**v6.6:** Добавлено полное удаление данных пользователя по запросу (кнопка "Удалить мои данные").

---

## 📁 Структура

| Файл | Описание |
|------|----------|
| `base.py` | Базовый класс для очисток |
| `user_cleanup.py` | Очистка пользователей |
| `subscription_cleanup.py` | Очистка подписок |
| `topic_cleanup.py` | Очистка тем |
| `media_cleanup.py` | Очистка медиа |

---

## 🎯 Основные функции

### `CleanupService.check_inactive_users(days=90)`

Проверка неактивных пользователей.

**Параметры:**
- `days` — количество дней без активности (по умолчанию 90)

**Возвращает:**
```python
List[int] = [user_id1, user_id2, ...]
```

---

### `CleanupService.delete_user(user_id)`

Удаление пользователя и всех связанных данных.

**Каскадное удаление:**
1. `UserPreferences`
2. `UserChannelSubscription`
3. `UserCachedMedia`
4. `SourceSubscription` (если добавлены пользователем)
5. `TopicSourceAssignment` (через CASCADE)

---

### `CleanupService.cleanup_old_media(days=30)`

Очистка старого кэша медиа.

**Параметры:**
- `days` — количество дней (по умолчанию 30)

---

## 🔄 Процесс очистки

```
[Планировщик: раз в сутки]
  ↓
[Проверка неактивных пользователей]
  ↓
[Для каждого пользователя:]
  ├─→ Удаление предпочтений
  ├─→ Удаление подписок
  ├─→ Удаление кэша
  └─→ Удаление пользователя
  ↓
[Логирование операции]
```

---

## 🗄️ База данных

### Удаляемые данные

| Таблица | Условие |
|---------|---------|
| `user_preferences` | `user_id IN (inactive_users)` |
| `user_channel_subscriptions` | `user_id IN (inactive_users)` |
| `user_cached_media` | `user_id IN (inactive_users)` |
| `source_subscriptions` | `added_by_telegram_account_id IN (inactive_users)` |
| `telegram_accounts` | `telegram_account_id IN (inactive_users)` |

---

## 🔒 Удаление данных пользователем (v6.6)

**Хендлер:** `bot/handlers/settings_handler.py::confirm_delete_data()`

**Триггер:** Кнопка "🗑️ Удалить мои данные" → "✅ ДА, удалить всё"

**Что удаляется:**
```sql
-- 1. Личные подписки
DELETE FROM user_channel_subscriptions WHERE user_id = ?;

-- 2. Добавленные подписки
DELETE FROM source_subscriptions WHERE added_by_telegram_account_id = ?;

-- 3. Созданные темы
DELETE FROM group_topics WHERE created_by_telegram_account_id = ?;

-- 4. Группы владельца ← НОВОЕ (v6.6)!
DELETE FROM managed_groups WHERE creator_id = ?;

-- 5. Настройки
DELETE FROM user_preferences WHERE user_id = ?;

-- 6. Аккаунт ← НОВОЕ (v6.6)!
DELETE FROM telegram_accounts WHERE telegram_account_id = ?;

-- 7. Redis кеш
FLUSHALL;
```

**Важно:**
- Аккаунт **полностью удаляется**, а не помечается
- Группы владельца удаляются (пользователь — админ!)
- Главное меню **не отправляется** после удаления
- Последнее сообщение — об успешном удалении

---

## 🧪 Тесты

**Файл:** `tests/test_cleanup.py`

| Тест | Описание | Статус |
|------|----------|--------|
| `test_check_inactive_users` | Проверка неактивных | ✅ |
| `test_delete_user` | Удаление пользователя | ✅ |
| `test_cascade_cleanup` | Каскадная очистка | ✅ |
| `test_cleanup_old_media` | Очистка медиа | ✅ |

**Всего:** 14 тестов, 14 ✅

---

## ⚠️ Особенности

1. **GDPR:** Соответствие требованиям GDPR
2. **Каскад:** Полное удаление всех связанных данных
3. **Логирование:** Все операции логируются
4. **Безопасность:** Проверка перед удалением

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор сервисов
- [`../02-handlers/settings.md`](../02-handlers/settings.md) — Удаление данных (хендлер)
- [`../06-database/schema.md`](../06-database/schema.md) — Схема БД

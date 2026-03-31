# 🧹 GDPR Очистка (Cleanup Service)

**Папка:** `core/services/cleanup/`  
**Версия:** 5.6 (1 марта 2026)

---

## 📋 Обзор

Автоматическая очистка неактивных пользователей и связанных данных (GDPR compliance).

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

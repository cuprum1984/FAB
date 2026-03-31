# Cleanup GDPR — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 5.6+

---

## 📋 Что это

Автоматическая очистка неактивных пользователей (GDPR compliance).

---

## 🎯 Ключевые файлы

- `core/services/cleanup/` — модуль (5 файлов)
- `core/services/cleanup/user_cleanup.py` — пользователи
- `core/services/cleanup/subscription_cleanup.py` — подписки

---

## ⚙️ Процесс

```
Планировщик (раз в сутки)
  ↓
Проверка неактивных (>90 дней)
  ↓
Для каждого пользователя:
  ├─→ Удаление предпочтений
  ├─→ Удаление подписок
  ├─→ Удаление кэша
  └─→ Удаление пользователя
```

---

## ⚠️ Важные решения

- **v5.6:** GDPR-очистка неактивных пользователей
- **v5.6:** Каскадное удаление всех связанных данных
- **v5.6:** Логирование всех операций

---

## 🗄️ БД

```python
# Удаляемые таблицы
user_preferences, user_channel_subscriptions, user_cached_media
source_subscriptions (если added_by = user)
telegram_accounts
```

---

## 🔗 Связанные документы

- `docs/04-services/cleanup-gdpr.md` — полная документация
- `docs/09-versions/v5.6.md` — версия
- `docs/02-handlers/settings.md` — удаление данных (хендлер)

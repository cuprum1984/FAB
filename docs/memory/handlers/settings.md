# Settings Handlers — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 5.7+

---

## 📋 Что это

Настройки пользователя: смена языка, стиль иконок, уведомления.

---

## 🎯 Ключевые файлы

- `bot/handlers/settings_handler.py` — обработчики
- `bot/keyboards/settings.py` — клавиатуры
- `core/models/user_preferences.py` — модель настроек

---

## 🎯 Команды

| Команда | Описание |
|---------|----------|
| `/settings` | Меню настроек |

---

## 🌍 Языки

| Код | Язык |
|-----|------|
| `ru` | Русский |
| `en` | English |
| `uk` | Українська |
| `be` | Беларуская |

---

## ⚠️ Важные решения

- **v5.7:** Inline-only клавиатуры
- **v5.7:** Мгновенная смена языка
- **v5.6:** GDPR — удаление данных пользователя

---

## 🗄️ БД

```python
# Таблицы
user_preferences: language, icon_style, notifications_enabled
telegram_accounts: language_code
```

---

## 🔗 Связанные документы

- `docs/02-handlers/settings.md` — полная документация
- `docs/04-services/cleanup-gdpr.md` — GDPR очистка
- `docs/08-i18n/languages.md` — языки

# 🌐 Локализация (i18n)

**Папка:** `locales/`

---

## 📋 Обзор

Локализация бота на 4 языка: русский, английский, украинский, белорусский.

---

## 📁 Структура

```
locales/
├── ru/
│   └── messages.json
├── en/
│   └── messages.json
├── uk/
│   └── messages.json
└── be/
    └── messages.json
```

---

## 🌍 Поддерживаемые языки

| Код | Язык | Флаг |
|-----|------|------|
| `ru` | Русский | 🇷🇺 |
| `en` | English | 🇬🇧 |
| `uk` | Українська | 🇺🇦 |
| `be` | Беларуская | 🇧🇾 |

---

## 📝 Формат файлов

**Файл:** `locales/ru/messages.json`

```json
{
  "common": {
    "start_new": "👋 Привет, {first_name}! Добро пожаловать в MyAggryBot!",
    "start_return": "👋 С возвращением, {first_name}!",
    "help": "ℹ️ Справка по боту...",
    "cancelled": "❌ Отменено"
  },
  "admin": {
    "activ_not_admin": "❌ Только администраторы могут активировать группу",
    "activ_bot_not_admin": "❌ Бот должен быть администратором",
    "activ_success": "✅ Группа активирована!"
  },
  "settings": {
    "language_changed": "✅ Язык изменён на {language}",
    "data_deleted": "✅ Данные удалены"
  },
  "sources": {
    "enter_telegram_username": "📺 Введите username Telegram канала:",
    "enter_youtube_url": "📹 Введите URL YouTube канала:",
    "source_deleted": "✅ Источник удалён"
  }
}
```

---

## 🔧 Использование

### В хендлерах

```python
from core.utils.i18n import get_text

# Получение текста
text = get_text(['common', 'start_new'], first_name=user_name)

# В middleware
async def i18n_middleware(handler, data):
    user_id = data['event_from_user'].id
    data['get_text'] = partial(get_text, user_id=user_id)
```

### Смена языка

```python
# Обновление языка пользователя
await session.execute(
    update(UserPreferences)
    .where(UserPreferences.user_id == user_id)
    .values(language='en')
)
```

---

## 📊 Документы

| Файл | Описание | Статус |
|------|----------|--------|
| [`languages.md`](languages.md) | Список языков, как добавить | 🔴 Не начато |

---

## ⚠️ Особенности

1. **Fallback:** При отсутствии перевода используется английский
2. **Кэширование:** Переводы кэшируются в памяти
3. **Форматирование:** Поддержка {placeholder} в текстах

---

## 🔗 Связанные документы

- [`../02-handlers/settings.md`](../02-handlers/settings.md) — Смена языка
- [`../01-general/deployment.md`](../01-general/deployment.md) — Развёртывание

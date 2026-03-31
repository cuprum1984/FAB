# 🌍 Языки локализации

**Папка:** `locales/`  
**Версия:** 5.7 (9 марта 2026)

---

## 📋 Обзор

Локализация бота на 4 языка.

---

## 🌍 Поддерживаемые языки

| Код | Язык | Флаг | Файл |
|-----|------|------|------|
| `ru` | Русский | 🇷🇺 | `locales/ru/messages.json` |
| `en` | English | 🇬🇧 | `locales/en/messages.json` |
| `uk` | Українська | 🇺🇦 | `locales/uk/messages.json` |
| `be` | Беларуская | 🇧🇾 | `locales/be/messages.json` |

---

## 📁 Структура файлов

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
    "main": "⚙️ Настройки",
    "language": "🌐 Язык",
    "language_changed": "✅ Язык изменён на {language}",
    "data_deleted": "✅ Данные удалены"
  },
  "sources": {
    "enter_telegram_username": "📺 Введите username Telegram канала:",
    "enter_youtube_url": "📹 Введите URL YouTube канала:",
    "source_deleted": "✅ Источник удалён"
  },
  "menu": {
    "add_channel": "➕ Добавить канал",
    "my_sources": "📚 Мои источники",
    "feed": "📰 Лента",
    "settings": "⚙️ Настройки",
    "help": "❓ Помощь"
  }
}
```

---

## 🔧 Использование

### В хендлерах

```python
from core.utils.i18n import get_text

@router.message(Command("start"))
async def cmd_start(message: Message, get_text: callable):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    text = get_text(['common', 'start_new'], first_name=first_name)
    await message.answer(text, reply_markup=get_main_menu_inline(get_text))
```

### В middleware

```python
from core.utils.i18n import I18nMiddleware

i18n = I18nMiddleware(locales_dir="locales", default_locale="ru")

@router.middleware()
async def i18n_middleware(handler, data):
    user_id = data['event_from_user'].id
    data['get_text'] = partial(i18n.get_text, user_id=user_id)
    return await handler(data)
```

---

## 🔄 Смена языка

### 1. Пользователь выбирает язык

```python
@router.callback_query(F.data.startswith("lang:"))
async def on_language_select(callback: CallbackQuery, session: AsyncSession):
    language_code = callback.data.split(":")[1]  # 'en', 'ru', etc.
    user_id = callback.from_user.id
    
    # Обновить язык в БД
    await session.execute(
        update(UserPreferences)
        .where(UserPreferences.user_id == user_id)
        .values(language=language_code)
    )
    await session.commit()
    
    # Показать подтверждение
    get_text = partial(i18n.get_text, user_id=user_id, language=language_code)
    text = get_text(['settings', 'language_changed'], language=language_code)
    await callback.answer(text)
```

---

## ➕ Как добавить новый язык

### 1. Создать папку и файл

```bash
mkdir locales/fr
touch locales/fr/messages.json
```

### 2. Скопировать структуру

```json
{
  "common": {
    "start_new": "👋 Bonjour, {first_name}! Bienvenue sur MyAggryBot!",
    "start_return": "👋 Bon retour, {first_name}!",
    ...
  },
  "admin": {
    ...
  }
}
```

### 3. Добавить в список языков

**Файл:** `bot/keyboards/settings.py`

```python
LANGUAGE_BUTTONS = [
    ("🇷🇺 Русский", "lang:ru"),
    ("🇬🇧 English", "lang:en"),
    ("🇺🇦 Українська", "lang:uk"),
    ("🇧🇾 Беларуская", "lang:be"),
    ("🇫🇷 Français", "lang:fr"),  # ← Добавить новый
]
```

---

## ⚠️ Особенности

1. **Fallback:** При отсутствии перевода используется английский
2. **Кэширование:** Переводы кэшируются в памяти
3. **Форматирование:** Поддержка `{placeholder}` в текстах
4. **HTML:** Поддержка HTML-тегов (`<b>`, `<i>`, `<a>`)

---

## 📊 Статистика переводов

| Язык | Файл | Строк | Статус |
|------|------|-------|--------|
| Русский | `ru/messages.json` | ~100 | ✅ 100% |
| English | `en/messages.json` | ~100 | ✅ 100% |
| Українська | `uk/messages.json` | ~100 | ✅ 100% |
| Беларуская | `be/messages.json` | ~100 | ✅ 100% |

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор i18n
- [`../02-handlers/settings.md`](../02-handlers/settings.md) — Смена языка
- [`../01-general/deployment.md`](../01-general/deployment.md) — Развёртывание

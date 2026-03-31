# ⌨️ Клавиатуры (InlineKeyboardMarkup)

**Папка:** `bot/keyboards/`

---

## 📋 Обзор

Модуль inline-клавиатур для бота. **Только InlineKeyboardMarkup** (с версии 5.7).

---

## 📁 Структура

```
bot/keyboards/
├── __init__.py              # Экспорт функций
├── main_menu.py             # Главное меню
├── admin.py                 # Админ-панель
├── settings.py              # Настройки
├── sources.py               # Добавление источников
├── destinations.py          # Выбор назначений
└── my_sources.py            # Навигация по источникам

bot/utils/
└── menu_message.py          # Управление сообщениями меню
```

---

## 🎯 Типы клавиатур

| Файл | Функции | Назначение |
|------|---------|------------|
| [`main_menu.py`](main_menu.py) | `get_main_menu_inline()` | Главное меню |
| [`admin.py`](admin.py) | `get_admin_panel_menu_inline()`, `get_groups_inline_kb()`, `get_topics_inline_kb()` | Админ-панель |
| [`settings.py`](settings.py) | `get_settings_menu_inline()`, `get_language_menu()`, `get_back_to_settings_kb()` | Настройки |
| [`sources.py`](sources.py) | `get_confirm_channel_kb()`, `get_cancel_kb()`, `get_source_list_kb()` | Источники |
| [`destinations.py`](destinations.py) | `get_destinations_inline_kb()` | Назначения |
| [`my_sources.py`](my_sources.py) | `get_overview_kb()`, `get_topics_tree_kb()` | Мои источники |

---

## 📝 Документы

| Файл | Описание | Статус |
|------|----------|--------|
| [`pagination.md`](pagination.md) | Система пагинации | ✅ Готово |
| [`menu-system.md`](menu-system.md) | Управление сообщениями меню | ✅ Готово |
| [`menu_message.md`](menu_message.md) | Утилиты menu_message.py | ✅ Готово |
| [`reference.md`](reference.md) | Справочник клавиатур | ✅ Готово |

---

## 🔄 Пагинация

Все списки используют единую систему пагинации:

- **Лимит:** 5 элементов на странице
- **Навигация:** `[◀️ .] [1/N] [. ▶️]`
- **Заглушки:** Точка `.` вместо неактивных кнопок

**См. подробнее:** [`pagination.md`](pagination.md)

---

## 📝 Управление сообщениями

Все клавиатуры используются с функцией `update_or_send_menu()`:

```python
from bot.utils.menu_message import update_or_send_menu

await update_or_send_menu(
    bot=callback.bot,
    chat_id=user_id,
    text="Текст",
    keyboard=get_main_menu_inline(get_text),
    state=state
)
```

**См. подробнее:** [`menu-system.md`](menu-system.md)

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `aiogram.types.InlineKeyboardMarkup` | Тип клавиатуры |
| `aiogram.types.InlineKeyboardButton` | Кнопки |
| `core.utils.i18n` | Локализация текстов |

---

## ⚠️ Особенности

1. **Inline-only:** Только inline-клавиатуры (с v5.7)
2. **Локализация:** Все тексты через i18n
3. **Универсальность:** Одна функция для всех экранов

---

## 🔗 Связанные документы

- [`../02-handlers/README.md`](../02-handlers/README.md) — Хендлеры
- [`pagination.md`](pagination.md) — Пагинация
- [`menu-system.md`](menu-system.md) — Управление сообщениями

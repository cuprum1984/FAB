# 🎮 Хендлеры (обработчики команд)

**Папка:** `bot/handlers/`

---

## 📋 Обзор

Хендлеры обрабатывают все команды и callback-запросы пользователей. Используется **только InlineKeyboardMarkup** (с версии 5.7).

---

## 📁 Структура

```
bot/handlers/
├── common.py                    # /start, /help, /refresh
├── admin.py                     # /activ, /plus, /mytopics
├── settings_handler.py          # /settings, смена языка
├── my_sources_interactive.py    # /list, навигация по источникам
├── my_overview.py               # /overview
├── topics_auto.py               # Авто-публикация в темы
│
└── sources/                     # Добавление источников
    ├── add_channel.py           # /add — начало процесса
    ├── telegram_handlers.py     # Добавление Telegram каналов
    ├── youtube_handlers.py      # Добавление YouTube каналов
    ├── destination_handlers.py  # Выбор назначения
    ├── group_select_handlers.py # Выбор группы
    ├── finalize_handlers.py     # Завершение добавления
    ├── cancel_handlers.py       # Отмена процесса
    └── list_handlers.py         # Просмотр списка
```

---

## 📊 Таблица хендлеров

| Файл | Команды | Callback префиксы | Описание |
|------|---------|-------------------|----------|
| [`common.md`](common.md) | `/start`, `/help`, `/refresh` | `menu_` | Общие команды, главное меню |
| [`admin.md`](admin.md) | `/activ`, `/plus`, `/mytopics` | `admin_`, `group_`, `topic_` | Админ-панель, управление группами |
| [`settings.md`](settings.md) | `/settings` | `settings_`, `lang_` | Настройки пользователя |
| [`my_sources.md`](my_sources.md) | `/list` | `list_`, `src_` | Навигация по источникам |
| [`my_overview.md`](my_overview.md) | `/overview` | `overview_` | Обзор источников |
| [`sources/add_channel.md`](sources/add_channel.md) | `/add` | `add_` | Начало добавления канала |
| [`sources/telegram.md`](sources/telegram.md) | — | `tg_` | Добавление Telegram каналов |
| [`sources/youtube.md`](sources/youtube.md) | — | `yt_` | Добавление YouTube каналов |
| [`sources/destination.md`](sources/destination.md) | — | `dest_` | Выбор назначения |
| [`sources/cancel.md`](sources/cancel.md) | — | `cancel_` | Отмена процесса |

---

## 🔄 FSM состояния

Состояния определены в `bot/states.py`:

| StatesGroup | Состояния | Назначение |
|-------------|-----------|------------|
| `AddChannel` | `waiting_for_username`, `confirm_channel`, `choose_group`, `choose_destination`, `edit_title` | Добавление канала |
| `AdminPanel` | `main`, `add_group`, `manage_groups`, `manage_topics`, `group_selected`, `topic_selected` | Админ-панель |
| `Settings` | `main`, `language`, `icons`, `notifications`, `confirm_delete` | Настройки |
| `MySources` | `viewing`, `selecting_group`, `selecting_topic`, `viewing_sources` | Навигация по источникам |
| `AddRSS` | `waiting_for_url`, `confirm_feed`, `choose_destination` | Добавление RSS (устарело) |

---

## 🎯 Inline-клавиатуры

Все хендлеры используют inline-клавиатуры из модуля `bot/keyboards/`:

```python
from bot.keyboards import (
    get_main_menu_inline,
    get_admin_panel_menu_inline,
    get_settings_menu_inline,
    get_groups_inline_kb,
    get_topics_inline_kb,
    get_source_list_kb,
)
```

**См. подробнее:** [`../../03-keyboards/README.md`](../../03-keyboards/README.md)

---

## 📝 Управление сообщениями

Все хендлеры используют единую функцию для управления сообщениями меню:

```python
from bot.utils.menu_message import update_or_send_menu, DEFAULT_DELETE_DELAY

await update_or_send_menu(
    bot=callback.bot,
    chat_id=user_id,
    text="Текст сообщения",
    keyboard=inline_kb,
    state=state
)
```

**См. подробнее:** [`../../03-keyboards/menu-system.md`](../../03-keyboards/menu-system.md)

---

## 🔗 Связанные документы

- [`../../03-keyboards/`](../../03-keyboards/) — Клавиатуры
- [`../../03-keyboards/menu-system.md`](../../03-keyboards/menu-system.md) — Управление сообщениями
- [`../01-general/architecture.md`](../01-general/architecture.md) — Архитектура

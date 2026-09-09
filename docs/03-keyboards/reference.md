# 📖 Справочник клавиатур

**Файл:** `bot/keyboards/`

---

## 📋 Полный список функций

### Главное меню (`main_menu.py`)

| Функция | Описание | Возвращает |
|---------|----------|------------|
| `get_main_menu_inline(get_text)` | Главное меню бота | InlineKeyboardMarkup |

**Кнопки:**
```
[➕ Добавить канал]  [📚 Мои источники]
[📰 Лента]         [⚙️ Настройки]
[❓ Помощь]        [🔄 Обновить]
```

---

### Админ-панель (`admin.py`)

| Функция | Описание | Возвращает |
|---------|----------|------------|
| `get_admin_panel_menu_inline(get_text)` | Меню админ-панели | InlineKeyboardMarkup |
| `get_groups_inline_kb(groups, page, page_size, get_text, back_callback)` | Список групп с пагинацией | InlineKeyboardMarkup |
| `get_topics_inline_kb(topics, page, page_size, get_text, back_callback)` | Список тем с пагинацией | InlineKeyboardMarkup |

**Кнопки админ-панели:**
```
[👥 Группы]  [🗨️ Темы]
[📊 Статистика]
[🔙 Назад]
```

---

### Настройки (`settings.py`)

| Функция | Описание | Возвращает |
|---------|----------|------------|
| `get_settings_menu_inline(get_text)` | Меню настроек | InlineKeyboardMarkup |
| `get_language_menu()` | Выбор языка | InlineKeyboardMarkup |
| `get_back_to_settings_kb(get_text)` | Назад в настройки | InlineKeyboardMarkup |
| `get_confirm_delete_kb(get_text)` | Подтверждение удаления | InlineKeyboardMarkup |

**Кнопки настроек:**
```
[🌐 Язык]  [🎨 Иконки]
[🔔 Уведомления]
[🗑️ Удалить данные]
[🔙 Назад]
```

**Кнопки выбора языка:**
```
[🇷🇺 Русский]  [🇬🇧 English]
[🇺🇦 Українська]  [🇧🇾 Беларуская]
[🔙 Назад]
```

---

### Источники (`sources.py`)

| Функция | Описание | Возвращает |
|---------|----------|------------|
| `get_confirm_channel_kb(source_info, get_text)` | Подтверждение добавления канала | InlineKeyboardMarkup |
| `get_cancel_kb(get_text)` | Кнопка отмены | InlineKeyboardMarkup |
| `get_source_list_kb(sources, page, page_size, get_text)` | Список источников с пагинацией | InlineKeyboardMarkup |
| `get_confirm_delete_source_kb(get_text)` | Подтверждение удаления источника | InlineKeyboardMarkup |

**Кнопки подтверждения канала:**
```
[✅ Добавить]  [❌ Отмена]
```

**Кнопки списка источников:**
```
[📰 @durov] [❌]
[📹 YouTube] [❌]
[◀️ .] [1/2] [. ▶️]
[🔙 Назад]
```

---

### Назначения (`destinations.py`)

| Функция | Описание | Возвращает |
|---------|----------|------------|
| `get_destinations_inline_kb(destinations, get_text)` | Выбор назначения | InlineKeyboardMarkup |

---

### Мои источники (`my_sources.py`)

| Функция | Описание | Возвращает |
|---------|----------|------------|
| `get_overview_kb(get_text)` | Обзор источников | InlineKeyboardMarkup |
| `get_topics_tree_kb(group, topics, get_text)` | Дерево тем группы | InlineKeyboardMarkup |

---

## 📊 Параметры пагинации

Все функции с пагинацией принимают:

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `page` | int | 0 | Номер страницы (0-based) |
| `page_size` | int | 5 | Элементов на странице |
| `get_text` | callable | None | Функция локализации |
| `back_callback` | str | "list_cancel" | Callback для кнопки "Назад" |

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор клавиатур
- [`pagination.md`](pagination.md) — Пагинация
- [`menu-system.md`](menu-system.md) — Управление сообщениями

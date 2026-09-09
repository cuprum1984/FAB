# Реализация пагинации для inline-клавиатур в MyAggryBot

## Обзор

Добавлена единая система пагинации для всех списков в боте:
- **Группы** — выбор группы для просмотра тем
- **Топики** — выбор темы для просмотра источников
- **Источники** — список подписок в теме

## Основные принципы

1. **Лимит элементов на странице:** 5 элементов
2. **Навигация всегда видна:** даже при 1 странице
3. **Заглушки вместо неактивных кнопок:** точка `.` вместо "Назад"/"Вперёд"
4. **Формат навигации:** `[◀️ .] [1/N] [. ▶️]`

## Реализованные функции

### 1. `get_groups_inline_kb()` (bot/keyboards.py)

```python
def get_groups_inline_kb(
    groups: List[dict],
    page: int = 0,
    page_size: int = 5,          # Лимит 5 групп на странице
    get_text: Optional[GetTextFunc] = None,
    back_callback: str = "list_cancel"
) -> InlineKeyboardMarkup:
```

**Структура клавиатуры:**
```
[👥 Группа 1]
[👥 Группа 2]
[👥 Группа 3]
[👥 Группа 4]
[👥 Группа 5]
[◀️ .] [1/3] [. ▶️]   ← навигация всегда
[❌ Отмена]           ← кнопка назад
```

**Логика навигации:**
- Страница 1: `[ . ] [1/3] [▶️ Вперед]`
- Страница 2: `[◀️ Назад] [2/3] [▶️ Вперед]`
- Страница 3: `[◀️ Назад] [3/3] [ . ]`

---

### 2. `get_topics_inline_kb()` (bot/keyboards.py)

```python
def get_topics_inline_kb(
    topics: List[dict],
    page: int = 0,
    page_size: int = 5,          # Лимит 5 топиков на странице
    get_text: Optional[GetTextFunc] = None,
    back_callback: str = "list_back:groups"
) -> InlineKeyboardMarkup:
```

**Структура клавиатуры:**
```
[🗨️ General]        ← всегда первый
[🗨️ Топик 1]
[🗨️ Топик 2]
[🗨️ Топик 3]
[🗨️ Топик 4]
[◀️ .] [1/2] [. ▶️]   ← навигация всегда
[← Назад]            ← кнопка назад к группам
```

**Особенности:**
- General топик всегда первый (telegram_thread_id is None)
- Остальные сортируются по названию

---

### 3. `get_source_list_kb()` (bot/keyboards.py)

```python
def get_source_list_kb(
    sources: List[dict],
    page: int = 0,
    page_size: int = 5,          # Лимит 5 источников на странице
    get_text: Optional[GetTextFunc] = None,
    use_subscription_id: bool = False,  # Для del_sub callback
    back_callback: str = "close_sources"
) -> InlineKeyboardMarkup:
```

**Структура клавиатуры:**
```
[📰 Источник 1] [❌]   ← две кнопки в одной строке
[📰 Источник 2] [❌]
[📰 Источник 3] [❌]
[📰 Источник 4] [❌]
[📰 Источник 5] [❌]
[◀️ .] [1/2] [. ▶️]   ← навигация всегда
[❌ Закрыть]          ← кнопка закрытия
```

**Особенности:**
- `use_subscription_id=True` → callback `del_sub:{id}` (для my_sources_interactive.py)
- `use_subscription_id=False` → callback `del_source:{id}` (для sources.py)

---

## Формула расчёта страниц

### ✅ Правильная формула:
```python
total_pages = (len(elements) + page_size - 1) // page_size if elements else 1
```

### ❌ Неправильная формула (было):
```python
total_pages = max(1, len(elements))  # ОШИБКА: не делит на page_size!
```

### Примеры расчёта (page_size=5):
| Элементов | Страниц | Формула |
|-----------|---------|---------|
| 0 | 1 | `(0 + 4) // 5 = 0` → `else 1` |
| 1-5 | 1 | `(5 + 4) // 5 = 1` |
| 6-10 | 2 | `(10 + 4) // 5 = 2` |
| 11-15 | 3 | `(15 + 4) // 5 = 3` |

---

## Обработчики (bot/handlers/my_sources_interactive.py)

### 1. `cmd_my_sources_interactive()` — показ групп
```python
@router.message(F.command.in_(["list", "mysources"]))
async def cmd_my_sources_interactive(...):
    groups = await get_user_groups(user_id, session)
    keyboard = get_groups_inline_kb(groups=groups, page=0, page_size=5, get_text=get_text)
    await message.answer(text, reply_markup=keyboard)
```

### 2. `on_group_selected()` — показ топиков
```python
@router.callback_query(F.data.startswith("list_group:"))
async def on_group_selected(...):
    topics = await session.execute(select(GroupTopic).where(...))
    
    # Преобразуем SQLAlchemy объекты в словари
    topics_as_dicts = [
        {
            'topic_name': t.topic_name,
            'topic_identifier': t.topic_identifier,
            'telegram_thread_id': t.telegram_thread_id
        }
        for t in topics
    ]
    
    keyboard = get_topics_inline_kb(topics=topics_as_dicts, page=0, page_size=5, get_text=get_text)
    await callback.message.edit_text(text, reply_markup=keyboard)
```

### 3. `on_topics_page_change()` — пагинация топиков
```python
@router.callback_query(F.data.startswith("topics_page:"))
async def on_topics_page_change(...):
    page = int(callback.data.split(":")[1])
    await state.update_data(topics_page=page)
    
    # Преобразуем объекты в словари
    topics_as_dicts = [...]
    
    keyboard = get_topics_inline_kb(topics=topics_as_dicts, page=page, page_size=5, get_text=get_text)
    await callback.message.edit_text(text, reply_markup=keyboard)
```

### 4. `on_groups_page_change()` — пагинация групп
```python
@router.callback_query(F.data.startswith("groups_page:"))
async def on_groups_page_change(...):
    page = int(callback.data.split(":")[1])
    await state.update_data(groups_page=page)
    
    keyboard = get_groups_inline_kb(groups=groups, page=page, page_size=5, get_text=get_text)
    await callback.message.edit_text(text, reply_markup=keyboard)
```

### 5. `on_delete_source()` — удаление источника
```python
@router.callback_query(F.data.startswith("del_sub:"))
async def on_delete_source(...):
    # Удаляем подписку
    await session.delete(subscription)
    await session.commit()
    
    # Получаем обновлённый список
    rows = await session.execute(stmt)
    
    # Преобразуем в словари
    sources = [
        {
            'source_global_id': source.source_global_id,
            'name': source.channel_title or ...,
            'subscription_id': subscription.subscription_id,
            'public_url': source.public_url,
            'source_type': source.source_type
        }
        for row in rows
        for source, subscription in [(row[0], row[1])]
    ]
    
    keyboard = get_source_list_kb(sources=sources, page=page, page_size=5, get_text=get_text, use_subscription_id=True)
    await callback.message.edit_text(text, reply_markup=keyboard)
```

---

## Состояния (FSM)

Сохраняемые данные в состоянии пользователя:

```python
await state.update_data(
    user_id=user_id,
    groups=groups,              # Список групп
    groups_page=0,              # Текущая страница групп
    sources_message_id=msg_id,  # ID сообщения с клавиатурой (для удаления)
    current_group=group,        # Выбранная группа
    current_topics=topics,      # Список топиков (SQLAlchemy объекты)
    topics_page=0,              # Текущая страница топиков
    topic_mapping=mapping,      # hash → topic_identifier
    current_topic_identifier=id # Выбранный топик
)
```

**Удаление предыдущего сообщения:**

При повторном вызове `/list` старое сообщение с клавиатурой удаляется:

```python
# В cmd_my_sources_interactive()
old_message_id = data.get('sources_message_id')
if old_message_id:
    await bot.delete_message(chat_id=user_id, message_id=old_message_id)

# Отправляем новое и сохраняем message_id
sent_message = await message.answer(...)
await state.update_data(sources_message_id=sent_message.message_id)
```

При нажатии "Отмена" сообщение также удаляется:

```python
# В on_cancel_pressed()
sources_message_id = data.get('sources_message_id')
if sources_message_id:
    await callback.bot.delete_message(chat_id=callback.from_user.id, message_id=sources_message_id)
await state.clear()
```

---

## Локализация (locales/ru.py, locales/en.py)

### Добавленные ключи:

```python
# groups_menu
"groups_menu": {
    "prev": "◀️ Назад",
    "next": "Вперед ▶️",
    "cancel": "❌ Отмена",
    "dot": ".",
}

# topics_menu
"topics_menu": {
    "prev": "◀️ Назад",
    "next": "Вперед ▶️",
    "back": "← Назад",
    "dot": ".",
}

# sources_list
"sources_list": {
    "view_source": "📰 {name}",
    "delete": "❌",
    "prev": "◀️ Назад",
    "next": "Вперед ▶️",
    "close": "❌ Закрыть",
    "dot": ".",
}

# destinations_inline
"destinations_inline": {
    "prev": "◀️ Назад",
    "next": "Вперед ▶️",
    "dot": ".",
}
```

---

## Callback данные

| Кнопка | Callback | Обработчик |
|--------|----------|------------|
| Группа | `list_group:{chat_id}` | `on_group_selected()` |
| Топик | `list_topic:{hash}` | `on_topic_selected()` |
| Страница групп | `groups_page:{page}` | `on_groups_page_change()` |
| Страница топиков | `topics_page:{page}` | `on_topics_page_change()` |
| Страница источников | `sources_page:{page}` | `on_sources_page_change()` |
| Удалить источник | `del_sub:{subscription_id}` | `on_delete_source()` |
| Назад к группам | `list_back:groups` | `on_back_pressed()` |
| Отмена | `list_cancel` | `on_cancel_pressed()` |

---

## Исправленные ошибки

### 1. `scalar_one_or_none()` → `first()`

**Проблема:**
```python
assignment = assign_result.scalar_one_or_none()
# ImportError: Multiple rows were found when one or none was required
```

**Решение:**
```python
assignment = assign_result.first()
if assignment:
    assignment = assignment[0]  # Извлекаем из кортежа
```

### 2. Объекты SQLAlchemy → словари

**Проблема:**
```python
topics = await session.execute(select(GroupTopic))
keyboard = get_topics_inline_kb(topics=topics)  # AttributeError: 'GroupTopic' object has no attribute 'get'
```

**Решение:**
```python
topics = await session.execute(select(GroupTopic))
topics_as_dicts = [
    {
        'topic_name': t.topic_name,
        'topic_identifier': t.topic_identifier,
        'telegram_thread_id': t.telegram_thread_id
    }
    for t in topics
]
keyboard = get_topics_inline_kb(topics=topics_as_dicts)
```

### 3. Формула пагинации

**Проблема:**
```python
total_pages = max(1, len(sorted_groups))  # 10 групп = 10 страниц!
```

**Решение:**
```python
total_pages = (len(sorted_groups) + page_size - 1) // page_size if sorted_groups else 1
# 10 групп / 5 на страницу = 2 страницы
```

---

## Экспорт функций (bot/keyboards.py)

```python
__all__ = [
    'get_main_menu',
    'get_groups_inline_kb',      # ← добавлено
    'get_topics_inline_kb',      # ← добавлено
    'get_source_list_kb',
    'get_destinations_inline_kb',
    # ... остальные
]
```

---

## Тестирование

### Сценарий 1: 1-5 элементов (1 страница)
```
Ожидание: [ . ] [1/1] [ . ]
Результат: ✅ Обе кнопки — заглушки
```

### Сценарий 2: 6-10 элементов (2 страницы)
```
Страница 1: [ . ] [1/2] [▶️ Вперед]
Страница 2: [◀️ Назад] [2/2] [ . ]
Результат: ✅ Кнопки появляются только когда есть страница
```

### Сценарий 3: Удаление источника
```
До: 5 источников, страница 1/1
После удаления: 4 источника, страница 1/1
Результат: ✅ Навигация обновляется корректно
```

---

## Файлы для изменения

1. **bot/keyboards.py**
   - Добавить `get_groups_inline_kb()`
   - Добавить `get_topics_inline_kb()`
   - Обновить `get_source_list_kb()` (параметр `use_subscription_id`)
   - Обновить `__all__`

2. **bot/handlers/my_sources_interactive.py**
   - Обновить `cmd_my_sources_interactive()` → `get_groups_inline_kb`
   - Обновить `on_group_selected()` → `get_topics_inline_kb`
   - Обновить `on_back_pressed()` → пагинация
   - Добавить `on_groups_page_change()`
   - Добавить `on_topics_page_change()`
   - Обновить `on_delete_source()` → `get_source_list_kb`

3. **locales/ru.py, locales/en.py**
   - Добавить ключи `groups_menu`, `topics_menu`

---

## Примечания

1. **Преобразование объектов SQLAlchemy:**
   - `get_topics_inline_kb()` требует словари, а не объекты
   - Всегда преобразовывать перед передачей

2. **Callback данные:**
   - `del_sub:{id}` — для my_sources_interactive.py
   - `del_source:{id}` — для sources.py
   - Использовать параметр `use_subscription_id`

3. **Пагинация:**
   - Всегда проверять `total_pages` перед доступом к странице
   - Использовать `max(0, min(page, total_pages - 1))`

---

**Дата реализации:** 2026-03-01  
**Версия бота:** MyAggryBot (aiogram 3.x)

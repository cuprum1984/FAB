# 📝 Menu Message (утилиты сообщений меню)

**Файл:** `bot/utils/menu_message.py`  
**Версия:** 5.7 (9 марта 2026)

---

## 📋 Обзор

Единая система управления сообщениями меню. Все экраны бота обновляют **одно сообщение** вместо отправки новых.

---

## 🎯 Концепция

```
ОДНО СООБЩЕНИЕ ДЛЯ ВСЕЙ НАВИГАЦИИ
├─ Все экраны обновляют одно сообщение через edit_message_text
├─ message_id сохраняется в FSM состоянии
├─ При успешном действии — старое удаляется, создаётся новое
└─ Задержка удаления настраивается (DEFAULT_DELETE_DELAY)
```

---

## 🔧 Основные функции

### `update_or_send_menu()`

Обновить существующее сообщение или отправить новое.

**Параметры:**
```python
async def update_or_send_menu(
    bot: Bot,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
    state: FSMContext,
    parse_mode: str = "HTML",
    use_draft: bool = False,
    fallback_message: Optional[Message] = None
) -> int:
```

**Логика:**
1. Получить `message_id` из состояния
2. Попытаться обновить сообщение
3. Если не вышло — отправить новое

**Пример:**
```python
await update_or_send_menu(
    bot=callback.bot,
    chat_id=user_id,
    text="🚀 MyAggryBot\nДобро пожаловать!",
    keyboard=get_main_menu_inline(get_text),
    state=state
)
```

---

### `send_menu_message()`

Отправить новое сообщение меню.

**Параметры:**
```python
async def send_menu_message(
    bot: Bot,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
    state: FSMContext,
    parse_mode: str = "HTML",
    use_draft: bool = False,
    fallback_message: Optional[Message] = None
) -> int:
```

**Возвращает:** `message_id` отправленного сообщения

---

### `clear_menu_message()`

Очистить сообщение меню (удалить `message_id` из состояния).

**Пример:**
```python
await clear_menu_message(state)
```

---

### `delete_menu_message()`

Удалить сообщение меню.

**Параметры:**
```python
async def delete_menu_message(
    bot: Bot,
    chat_id: int,
    state: FSMContext
) -> bool:
```

---

### `delete_after_delay()`

Удалить сообщение с задержкой.

**Параметры:**
```python
async def delete_after_delay(
    bot: Bot,
    chat_id: int,
    message_id: int,
    delay: int = DEFAULT_DELETE_DELAY
):
```

**Пример:**
```python
# Удалить через 2 секунды
await delete_after_delay(bot, user_id, message_id, delay=2)
```

---

## ⚙️ Константы

### `MENU_MESSAGE_ID_KEY`

Ключ для хранения `message_id` в FSM состоянии.

```python
MENU_MESSAGE_ID_KEY = "_menu_message_id"
```

**Важно:** Ключ **глобальный** для всех состояний FSM. Это означает:
- Все экраны используют один `message_id`
- При смене состояния `message_id` сохраняется
- При `state.clear()` ключ очищается

**Пример хранения в FSM:**
```python
# Состояние: AddChannel.waiting_for_username
state_data = {"_menu_message_id": 1234}

# Переход в: AddChannel.confirm_channel
state_data = {"_menu_message_id": 1234, "channel_username": "@durov"}

# state.clear()
state_data = {}
```

---

### `DEFAULT_DELETE_DELAY`

Глобальная задержка удаления сообщений (в секундах).

```python
DEFAULT_DELETE_DELAY = 0  # Мгновенное удаление
```

**Используется:**
- При удалении/добавлении источников
- При возврате в главное меню
- При успешных действиях

---

## 🔄 Схема работы

```
Пользователь нажимает кнопку
  ↓
[Callback handler]
  ↓
[Обработка действия]
  ↓
[update_or_send_menu()]
  ├─→ Получить message_id из состояния
  ├─→ Попытаться обновить (edit_message_text)
  └─→ Если ошибка → отправить новое (send_message)
  ↓
[Сохранить новый message_id]
```

---

## 📊 Примеры использования

### В хендлерах

```python
from bot.utils.menu_message import update_or_send_menu

@router.callback_query(F.data == "menu_settings")
async def on_menu_settings(callback: CallbackQuery, state: FSMContext, get_text: callable):
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['settings', 'main']),
        keyboard=get_settings_menu_inline(get_text),
        state=state
    )
```

### С задержкой удаления

```python
from bot.utils.menu_message import (
    update_or_send_menu,
    delete_after_delay,
    DEFAULT_DELETE_DELAY
)

@router.callback_query(F.data == "source_delete")
async def on_source_delete(callback: CallbackQuery, state: FSMContext):
    # Удалить источник
    await delete_source(source_id)
    
    # Удалить старое сообщение через 2 сек
    await delete_after_delay(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        delay=2
    )
    
    # Показать новое меню
    await update_or_send_menu(...)
```

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `aiogram.types.Message` | Тип сообщения |
| `aiogram.types.InlineKeyboardMarkup` | Клавиатура |
| `aiogram.fsm.context.FSMContext` | FSM состояние |
| `aiogram.Bot` | Бот |
| `aiogram.exceptions.TelegramBadRequest` | Ошибки API |

---

## ⚠️ Особенности

1. **Единое сообщение:** Все экраны обновляют одно сообщение
2. **FSM хранение:** `message_id` хранится в состоянии
3. **Fallback:** Если edit не сработал — send
4. **Задержка:** Настраиваемая задержка удаления

---

## 🔗 Связанные документы

- [`../03-keyboards/menu-system.md`](../03-keyboards/menu-system.md) — Управление сообщениями (общее)
- [`../03-keyboards/README.md`](../03-keyboards/README.md) — Клавиатуры
- [`../02-handlers/README.md`](../02-handlers/README.md) — Хендлеры

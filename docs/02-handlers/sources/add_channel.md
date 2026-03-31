# ➕ Добавление канала (add_channel.py)

**Файл:** `bot/handlers/sources/add_channel.py`  
**Версия:** 5.7 (9 марта 2026)

---

## 📋 Обзор

Начало процесса добавления источника. Выбор типа источника.

**Команда:** `/add`

---

## 🎯 Команды

### `/add` — Добавить источник

**Описание:** Начало процесса добавления источника.

**Логика:**
1. Проверка пользователя в БД
2. Показ меню выбора типа источника
3. Переход в состояние `AddChannel.waiting_for_username`

**Клавиатура:**
```
[📺 Telegram канал]
[📹 YouTube канал]
[❌ Отмена]
```

---

## 🔁 Callback-запросы

### `add_telegram` — Добавить Telegram канал

**Логика:**
1. Переход в состояние `AddChannel.waiting_for_username`
2. Запрос username канала

**Текст:** `sources.enter_telegram_username`

---

### `add_youtube` — Добавить YouTube канал

**Логика:**
1. Переход в состояние `AddChannel.waiting_for_username`
2. Запрос URL или названия канала

**Текст:** `sources.enter_youtube_url`

---

### `add_cancel` — Отмена

**Логика:**
1. Очистка состояния FSM
2. Показ главного меню

**Клавиатура:** `get_main_menu_inline()`

**Текст:** `common.cancelled`

---

## 📊 Схема работы

```
/add
  ↓
[Выбор типа источника]
  ├─→ Telegram → telegram_handlers.py
  ├─→ YouTube → youtube_handlers.py
  └─→ Отмена → Главное меню
```

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `bot.keyboards.get_confirm_channel_kb` | Клавиатура подтверждения |
| `bot.utils.menu_message.update_or_send_menu` | Управление сообщением |
| `bot.states.AddChannel` | FSM состояния |

---

## 🧪 Тесты

Прямых тестов нет. Тестируется косвенно через:
- Интеграционные тесты
- Ручное тестирование

---

## ⚠️ Особенности

1. **Валидация ввода:** На следующих этапах
2. **Inline-only:** Только inline-клавиатуры (с v5.7)

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор источников
- [`telegram.md`](telegram.md) — Добавление Telegram
- [`youtube.md`](youtube.md) — Добавление YouTube
- [`cancel.md`](cancel.md) — Отмена

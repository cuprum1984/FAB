# 📺 Добавление Telegram каналов (telegram_handlers.py)

**Файл:** `bot/handlers/sources/telegram_handlers.py`  
**Версия:** 5.7 (9 марта 2026)

---

## 📋 Обзор

Добавление Telegram каналов как источников.

---

## 🎯 Обработчики

### Ввод username (message handler)

**Состояние:** `AddChannel.waiting_for_username`

**Логика:**
1. Получение username от пользователя
2. Валидация формата (@username или https://t.me/username)
3. Проверка канала через парсер
4. Показ информации о канале
5. Запрос подтверждения

**Валидация:**
- Начало с `@` или `https://t.me/`
- Длина 5-32 символов
- Только латиница, цифры, подчёркивания

**Текст:**
```
📺 Telegram канал

Название: @durov
Подписчики: 1.2M
Описание: ...

[✅ Добавить] [❌ Отмена]
```

---

## 🔁 Callback-запросы

### `tg_confirm_add` — Подтвердить добавление

**Логика:**
1. Сохранение источника в БД (`ContentSource`)
2. Переход к выбору группы
3. Переход в состояние `AddChannel.choose_group`

**Клавиатура:** `get_groups_inline_kb()`

---

### `tg_cancel` — Отмена

**Логика:**
1. Очистка состояния FSM
2. Показ главного меню

**Текст:** `common.cancelled`

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `core.parser.telegram.TelegramParser` | Парсинг канала |
| `core.models.ContentSource` | Модель источника |
| `bot.keyboards.get_confirm_channel_kb` | Подтверждение |
| `bot.utils.menu_message.update_or_send_menu` | Управление сообщением |

---

## 🗄️ База данных

### Сохраняемые данные

| Таблица | Поля |
|---------|------|
| `content_sources` | `source_type='telegram'`, `username`, `title`, `description` |

---

## ⚠️ Особенности

1. **Rate Limiting:** Проверка через парсер с ограничением
2. **Кэширование:** Информация о канале кэшируется
3. **Inline-only:** Только inline-клавиатуры

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор источников
- [`../../04-services/rate-limiting.md`](../../04-services/rate-limiting.md) — Rate Limiting
- [`../../05-parsers/telegram.md`](../../05-parsers/telegram.md) — Telegram парсер

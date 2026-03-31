# 📹 Добавление YouTube каналов (youtube_handlers.py)

**Файл:** `bot/handlers/sources/youtube_handlers.py`  
**Версия:** 5.7 (9 марта 2026)

---

## 📋 Обзор

Добавление YouTube каналов как источников.

---

## 🎯 Обработчики

### Ввод URL/канала (message handler)

**Состояние:** `AddChannel.waiting_for_username`

**Логика:**
1. Получение URL или названия канала
2. Валидация формата
3. Проверка канала через парсер
4. Показ информации о канале
5. Запрос подтверждения

**Валидация:**
- URL: `https://www.youtube.com/channel/...` или `https://www.youtube.com/@...`
- Название: @username

**Текст:**
```
📹 YouTube канал

Название: MrBeast
Подписчики: 200M
Видео: 741

[✅ Добавить] [❌ Отмена]
```

---

## 🔁 Callback-запросы

### `yt_confirm_add` — Подтвердить добавление

**Логика:**
1. Сохранение источника в БД (`ContentSource`)
2. Переход к выбору группы
3. Переход в состояние `AddChannel.choose_group`

**Клавиатура:** `get_groups_inline_kb()`

---

### `yt_cancel` — Отмена

**Логика:**
1. Очистка состояния FSM
2. Показ главного меню

**Текст:** `common.cancelled`

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `core.parser.youtube_simple.YouTubeParser` | Парсинг канала |
| `core.models.ContentSource` | Модель источника |
| `bot.keyboards.get_confirm_channel_kb` | Подтверждение |
| `bot.utils.menu_message.update_or_send_menu` | Управление сообщением |

---

## 🗄️ База данных

### Сохраняемые данные

| Таблица | Поля |
|---------|------|
| `content_sources` | `source_type='youtube'`, `url`, `title`, `description` |

---

## ⚠️ Особенности

1. **Rate Limiting:** Строгое ограничение (1 запрос/сек)
2. **Кэширование:** Информация о канале кэшируется
3. **Inline-only:** Только inline-клавиатуры

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор источников
- [`../../04-services/rate-limiting.md`](../../04-services/rate-limiting.md) — Rate Limiting
- [`../../05-parsers/youtube.md`](../../05-parsers/youtube.md) — YouTube парсер

# ✅ Завершение (finalize_handlers.py)

**Файл:** `bot/handlers/sources/finalize_handlers.py`  
**Версия:** 5.7 (9 марта 2026)

---

## 📋 Обзор

Финальное подтверждение и сохранение источника.

---

## 🎯 Обработчики

### Финальное подтверждение (callback handler)

**Состояние:** `AddChannel.confirm_channel`

**Логика:**
1. Получение данных из состояния:
   - Тип источника (Telegram/YouTube)
   - Username/URL
   - Выбранная группа
   - Выбранная тема
2. Сохранение в БД:
   - `ContentSource` — источник
   - `SourceSubscription` — подписка группы
   - `TopicSourceAssignment` — назначение в тему
3. Очистка состояния FSM
4. Показ подтверждения

**Текст:**
```
✅ Источник добавлен!

Название: @durov
Группа: Проект Альфа
Тема: Новости

[➕ Добавить ещё] [🔙 В главное меню]
```

---

## 🔁 Callback-запросы

### `final_confirm` — Подтвердить

**Логика:**
1. Сохранение источника
2. Создание подписки
3. Создание назначения
4. Показ подтверждения

---

### `final_add_more` — Добавить ещё

**Логика:**
1. Очистка состояния
2. Возврат к началу добавления
3. Переход в состояние `AddChannel.waiting_for_username`

---

### `final_back` — В главное меню

**Логика:**
1. Очистка состояния
2. Показ главного меню

**Клавиатура:** `get_main_menu_inline()`

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `core.models.ContentSource` | Модель источника |
| `core.models.SourceSubscription` | Подписка |
| `core.models.TopicSourceAssignment` | Назначение |
| `core.services.destination_service` | Сервис назначений |
| `bot.utils.menu_message.update_or_send_menu` | Управление сообщением |

---

## 🗄️ База данных

### Сохраняемые данные

| Таблица | Поля |
|---------|------|
| `content_sources` | `source_type`, `username/url`, `title`, `description` |
| `source_subscriptions` | `source_global_id`, `telegram_chat_id`, `added_by` |
| `topic_source_assignments` | `subscription_id`, `topic_identifier` |

---

## ⚠️ Особенности

1. **Транзакционность:** Все операции в одной транзакции
2. **Каскад:** При ошибке — откат всех изменений
3. **Inline-only:** Только inline-клавиатуры

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор источников
- [`../../04-services/destinations.md`](../../04-services/destinations.md) — Destination Service
- [`../../06-database/schema.md`](../../06-database/schema.md) — Схема БД

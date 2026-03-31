# 🎯 Выбор назначения (destination_handlers.py)

**Файл:** `bot/handlers/sources/destination_handlers.py`  
**Версия:** 5.7 (9 марта 2026)

---

## 📋 Обзор

Выбор назначения для источника: группа → тема.

---

## 🎯 Обработчики

### Выбор группы (callback handler)

**Состояние:** `AddChannel.choose_group`

**Логика:**
1. Получение списка групп пользователя
2. Показ списка групп
3. Ожидание выбора группы

**Клавиатура:** `get_groups_inline_kb()`

**Пагинация:** 5 групп на странице

---

### Выбор темы (callback handler)

**Состояние:** `AddChannel.choose_destination`

**Логика:**
1. Получение списка тем выбранной группы
2. Показ списка тем
3. Ожидание выбора темы

**Клавиатура:** `get_topics_inline_kb()`

**Пагинация:** 5 тем на странице

---

## 🔁 Callback-запросы

### `dest_group:{chat_id}` — Выбрать группу

**Параметры:**
- `chat_id` — ID группы

**Логика:**
1. Сохранение выбранной группы в состоянии
2. Получение тем группы
3. Показ списка тем
4. Переход в состояние `AddChannel.choose_destination`

---

### `dest_topic:{topic_id}` — Выбрать тему

**Параметры:**
- `topic_id` — ID темы

**Логика:**
1. Сохранение выбранной темы в состоянии
2. Переход к финальному подтверждению
3. Переход в состояние `AddChannel.confirm_channel`

---

### `dest_back` — Назад

**Логика:**
1. Возврат к выбору группы
2. Очистка выбранной темы

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `core.services.destination_service.get_user_groups` | Получение групп |
| `core.models.GroupTopic` | Модель темы |
| `bot.keyboards.get_groups_inline_kb` | Список групп |
| `bot.keyboards.get_topics_inline_kb` | Список тем |
| `bot.utils.menu_message.update_or_send_menu` | Управление сообщением |

---

## 🗄️ База данных

### Запросы

| Операция | Таблица | Условия |
|----------|---------|---------|
| Получить группы | `managed_groups` | `user_id = ?` |
| Получить темы | `group_topics` | `chat_id = ?` |

---

## ⚠️ Особенности

1. **Пагинация:** 5 элементов на странице
2. **Inline-only:** Только inline-клавиатуры
3. **Каскад:** Источник привязывается к теме

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор источников
- [`../../03-keyboards/pagination.md`](../../03-keyboards/pagination.md) — Пагинация
- [`../../04-services/destinations.md`](../../04-services/destinations.md) — Destination Service

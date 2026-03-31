# 🎯 Destination Service

**Папка:** `core/services/destinations/`  
**Версия:** 4.0 (18 февраля 2026)

---

## 📋 Обзор

Сервис для управления назначениями источников в темы.

---

## 📁 Структура

| Файл | Описание |
|------|----------|
| `access.py` | Проверка доступа к группам/темам |
| `assignments.py` | Назначения источников |
| `cache.py` | Кэш назначений |
| `sources.py` | Управление источниками |
| `subscriptions.py` | Подписки на источники |
| `topics.py` | Управление темами |
| `topic_utils.py` | Утилиты для тем |

---

## 🎯 Основные функции

### `get_user_groups(user_id)`

Получение списка групп пользователя.

**Возвращает:**
```python
List[dict] = [
    {
        'chat_id': int,
        'title': str,
        'topics_count': int,
        'sources_count': int
    }
]
```

---

### `create_or_update_topic(...)`

Создание или обновление темы.

**Параметры:**
- `chat_id` — ID группы
- `topic_name` — Название темы
- `topic_id` — ID темы (опционально)

**Возвращает:**
```python
dict = {
    'topic_id': int,
    'chat_id': int,
    'name': str,
    'created': bool
}
```

---

### `TopicUtils.get_topic_by_id(topic_id)`

Получение темы по ID.

**Возвращает:** `GroupTopic | None`

---

### `TopicUtils.get_topics_for_group(chat_id)`

Получение всех тем группы.

**Возвращает:** `List[GroupTopic]`

---

## 🔁 Каскадные операции

### Удаление источника

```
Удаление SourceSubscription
  ↓
Поиск всех TopicSourceAssignment
  ↓
Удаление всех назначений
  ↓
Готово
```

### Удаление темы

```
Удаление GroupTopic
  ↓ (CASCADE)
Удаление TopicSourceAssignment
  ↓
Готово
```

---

## 🗄️ База данных

### Таблицы

| Таблица | Назначение |
|---------|------------|
| `managed_groups` | Управляемые группы |
| `group_topics` | Темы в группах |
| `content_sources` | Источники |
| `source_subscriptions` | Подписки групп на источники |
| `topic_source_assignments` | Назначения источников в темы |

---

## 🧪 Тесты

**Файл:** `tests/test_destination_service.py`

| Тест | Описание | Статус |
|------|----------|--------|
| `test_get_user_groups` | Получение групп пользователя | ✅ |
| `test_create_or_update_topic` | Создание/обновление темы | ✅ |
| `test_topic_utils` | Утилиты тем | ✅ |
| `test_cascade_delete` | Каскадное удаление | ✅ |

**Всего:** 23 теста, 23 ✅

---

## ⚠️ Особенности

1. **Каскадные операции:** Автоматическое удаление связанных данных
2. **Кэширование:** Кэш назначений для производительности
3. **Валидация:** Проверка корректности назначений

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор сервисов
- [`../02-handlers/sources/destination.md`](../02-handlers/sources/destination.md) — Выбор назначения
- [`../06-database/schema.md`](../06-database/schema.md) — Схема БД

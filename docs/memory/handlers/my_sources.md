# My Sources Handlers — Контекст

**Последнее обновление:** 2026-04-20  
**Версия:** 6.9.8+

---

## 📋 Что это

Интерактивная навигация по источникам: группы → темы → источники.

---

## 🎯 Ключевые файлы

- `bot/handlers/my_sources_interactive.py` — навигация
- `bot/keyboards/admin.py` — клавиатуры групп/тем
- `bot/keyboards/sources.py` — клавиатуры источников

---

## 🎯 Команды

| Команда | Описание |
|---------|----------|
| `/list` | Мои источники (навигация) |

---

## 🔄 Процесс

```
/list → Группы → Темы → Источники → Детали
```

---

## ⚠️ Важные решения

- **v6.9.8:** Удалён функционал "Обзор" (overview_page, get_overview_kb)
- **v6.9.8:** Добавлен `session: AsyncSession` в `on_back_pressed()`
- **v6.9.8:** Переименовано `format_sources_overview_page` → `format_sources_page`
- **v5.7:** Интерактивная навигация (вместо статичного списка)
- **v5.7:** Пагинация 5 элементов на странице
- **v5.7:** Inline-only клавиатуры
- **v5.4:** Каскадное удаление источников

---

## 🗄️ БД

```python
# Запросы
managed_groups → group_topics → source_subscriptions → topic_source_assignments
```

---

## 🔗 Связанные документы

- `docs/02-handlers/my_sources.md` — полная документация
- `docs/03-keyboards/pagination.md` — пагинация
- `docs/04-services/destinations.md` — Destination Service
- `docs/09-versions/v6.9.8.md` — версия

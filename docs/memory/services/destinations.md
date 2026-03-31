# Destinations Service — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 4.0+

---

## 📋 Что это

Управление назначениями источников в темы.

---

## 🎯 Ключевые файлы

- `core/services/destinations/` — модуль (7 файлов)
- `core/services/destinations/assignments.py` — назначения
- `core/services/destinations/topics.py` — темы

---

## ⚙️ Процесс

```
Источник → Подписка группы → Назначение в тему
```

---

## ⚠️ Важные решения

- **v4.0:** Destination Service (центральный компонент)
- **v4.0:** Каскадные операции (удаление)
- **v4.0:** Валидация назначений
- **v5.4:** Разделение на модули

---

## 🗄️ БД

```python
# Таблицы
source_subscriptions → topic_source_assignments → group_topics
```

---

## 🔗 Связанные документы

- `docs/04-services/destinations.md` — полная документация
- `docs/09-versions/v4.0.md` — версия
- `docs/06-database/schema.md` — схема БД

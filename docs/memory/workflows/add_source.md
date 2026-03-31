# Добавление источника — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 5.7+

---

## 📋 Что это

Пошаговый процесс добавления источника (Telegram или YouTube).

---

## 🎯 Ключевые файлы

- `bot/handlers/sources/add_channel.py` — начало (`/add`)
- `bot/handlers/sources/telegram_handlers.py` — Telegram
- `bot/handlers/sources/youtube_handlers.py` — YouTube
- `bot/handlers/sources/destination_handlers.py` — выбор назначения

---

## 🔄 Процесс

```
/add
  ↓
Выбор типа (Telegram/YouTube)
  ↓
Ввод username/URL → Проверка
  ↓
Подтверждение
  ↓
Выбор группы → Выбор темы
  ↓
Сохранение в БД
```

---

## ⚠️ Важные решения

- **v5.7:** Inline-only клавиатуры
- **v5.7:** Пошаговый FSM процесс
- **v5.7:** Отмена на любом этапе
- **v4.0:** Destination Service для назначений

---

## 🗄️ БД

```python
# Сохраняемые данные
ContentSource         # Источник
SourceSubscription    # Подписка группы
TopicSourceAssignment # Назначение в тему
```

---

## 🔗 Связанные документы

- `docs/02-handlers/sources/README.md` — хендлеры
- `docs/04-services/destinations.md` — Destination Service

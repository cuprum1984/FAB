# Добавление источника — Контекст

**Последнее обновление:** 2026-04-08
**Версия:** 6.9.1+

---

## 📋 Что это

Пошаговый процесс добавления источника (Telegram или YouTube).

---

## 🎯 Ключевые файлы

- `bot/handlers/sources/add_channel.py` — начало (`/add`) + проверка блокировки
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
⛔ Проверка is_blocked (v6.9.1) — отказ если заблокирован
  ↓
Подтверждение
  ↓
Выбор группы → Выбор темы
  ↓
Сохранение в БД
```

---

## ⚠️ Важные решения

- **v6.9.1:** Проверка `is_blocked` после парсинга — отказ с локализацией
- **v5.7:** Inline-only клавиатуры
- **v5.7:** Пошаговый FSM процесс
- **v5.7:** Отмена на любом этапе
- **v4.0:** Destination Service для назначений

---

## 🗄️ БД

```python
# Сохраняемые данные
ContentSource         # Источник (+ is_blocked, blocked_reason в v6.9.1)
SourceSubscription    # Подписка группы
TopicSourceAssignment # Назначение в тему
```

---

## 🔗 Связанные документы

- `docs/02-handlers/sources/README.md` — хендлеры
- `docs/04-services/destinations.md` — Destination Service
- `docs/09-versions/v6.9.1.md` — блокировка источников

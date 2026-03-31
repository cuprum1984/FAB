# Monitoring Service — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 6.1+

---

## 📋 Что это

Автоматический парсинг источников (Telegram, YouTube) и добавление в очередь.

---

## 🎯 Ключевые файлы

- `core/services/monitoring/` — модуль мониторинга
- `core/services/monitoring/telegram_monitor.py` — Telegram
- `core/services/monitoring/youtube_monitor.py` — YouTube
- `core/services/monitoring/post_sender.py` — отправка постов

---

## ⚙️ Процесс

```
Планировщик (каждые N минут)
  ↓
Получение источников из БД
  ↓
Для каждого источника:
  ├─→ Проверка Rate Limit
  ├─→ Парсинг
  ├─→ Новые посты → очередь
  └─→ Обновление last_check
```

---

## ⚠️ Важные решения

- **v6.1:** Semaphore для ограничения параллелизма
- **v6.1:** N+1 оптимизация запросов к БД
- **v6.1:** TaskDispatcher для управления задачами
- **v6.2:** Bulk update для отправки постов
- **v6.2:** Кэш тем для производительности

---

## 🔗 Связанные документы

- `docs/04-services/monitoring.md` — полная документация
- `docs/09-versions/v6.1.md` — масштабирование
- `docs/09-versions/v6.2.md` — оптимизация PostSender

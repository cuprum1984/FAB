# Публикация постов — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 6.2+

---

## 📋 Что это

Автоматическая публикация постов из очереди в темы Telegram.

---

## 🎯 Ключевые файлы

- `core/services/monitoring/post_sender.py` — отправка постов
- `core/services/monitoring/telegram_monitor.py` — мониторинг
- `core/services/rate_limiter.py` — Rate Limiting

---

## 🔄 Процесс

```
Monitoring Service
  ↓
Парсинг источников
  ↓
Новые посты → очередь (Redis)
  ↓
Post Sender (каждые N минут)
  ├─→ Проверка Rate Limit
  ├─→ Получение темы из кэша
  ├─→ Отправка поста (bulk)
  └─→ Логирование
```

---

## ⚠️ Важные решения

- **v6.2:** Bulk update для отправки
- **v6.2:** Кэш тем (не запрашивать БД каждый раз)
- **v6.2:** Изоляция ошибок (ошибка не ломает другие)
- **v6.1:** Semaphore для ограничения параллелизма
- **v5.3:** Rate Limiting для защиты от бана

---

## 📊 Производительность

```
До v6.2:  ~50 сек на 100 постов
После v6.2: ~15 сек на 100 постов (3.3x быстрее)
```

---

## 🔗 Связанные документы

- `docs/04-services/monitoring.md` — Monitoring Service
- `docs/09-versions/v6.2.md` — оптимизация
- `docs/04-services/rate-limiting.md` — Rate Limiting

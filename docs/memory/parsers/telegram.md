# Telegram Parser — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 2.0+

---

## 📋 Что это

Парсинг публичных Telegram каналов для получения постов.

---

## 🎯 Ключевые файлы

- `core/parser/telegram.py` — парсер канала
- `core/parser/telegram_posts.py` — обработка постов
- `core/services/monitoring/telegram_monitor.py` — мониторинг

---

## ⚙️ Процесс

```
Запрос к Telegram API
  ↓
Получение канала
  ↓
Получение постов (limit=10)
  ↓
Для каждого поста:
  ├─→ Текст
  ├─→ Медиа (фото, видео, документы)
  └─→ Metadata (views, forwards)
```

---

## ⚠️ Важные решения

- **v2.0:** Telethon для парсинга
- **v5.3:** Rate Limiting (10 запросов/сек)
- **v5.3:** Exponential Backoff при ошибках
- **v6.2:** Кэширование информации о канале

---

## 🔧 Конфигурация

```python
# Rate Limiting
RATE_LIMIT_TELEGRAM_TOKENS=20
RATE_LIMIT_TELEGRAM_REFILL=10.0
```

---

## 🔗 Связанные документы

- `docs/05-parsers/telegram.md` — полная документация
- `docs/04-services/rate-limiting.md` — Rate Limiting
- `docs/09-versions/v2.0.md` — версия (первая)

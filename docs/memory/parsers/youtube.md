# YouTube Parser — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 5.0+

---

## 📋 Что это

Парсинг YouTube каналов для получения новых видео.

---

## 🎯 Ключевые файлы

- `core/parser/youtube_simple.py` — парсер (без API)
- `core/services/youtube_simple_service.py` — сервис
- `core/services/monitoring/youtube_monitor.py` — мониторинг

---

## ⚙️ Процесс

```
Запрос к YouTube (HTML парсинг)
  ↓
Получение канала
  ↓
Получение видео (limit=5)
  ↓
Для каждого видео:
  ├─→ video_id, title, url
  ├─→ published, thumbnail
  └─→ Проверка: новое ли?
```

---

## ⚠️ Важные решения

- **v5.0:** Без YouTube API (парсинг HTML)
- **v5.0:** Не требует API key
- **v5.3:** Rate Limiting (1 запрос/сек, строго)
- **v5.3:** Exponential Backoff при ошибках

---

## 🔧 Конфигурация

```python
# Rate Limiting (строгий!)
RATE_LIMIT_YOUTUBE_TOKENS=5
RATE_LIMIT_YOUTUBE_REFILL=1.0
```

---

## 🔗 Связанные документы

- `docs/05-parsers/youtube.md` — полная документация
- `docs/04-services/youtube.md` — YouTube Service
- `docs/09-versions/v5.0.md` — версия

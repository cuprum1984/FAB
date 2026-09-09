# 🕸️ Парсеры

**Папка:** `core/parser/`

---

## 📋 Обзор

Парсеры для получения контента из внешних источников: **Telegram** (веб-парсинг) и **YouTube** (HTML-парсинг).

**Общие принципы:**
- ✅ Без внешних API (не требуют ключей)
- ✅ Rate Limiting (Token Bucket)
- ✅ Exponential Backoff при ошибках
- ✅ Async/await (aiohttp)

---

## 📁 Структура

```
core/parser/
├── __init__.py
├── telegram.py              # Проверка существования канала
├── telegram_posts.py        # Основная функция get_new_posts()
└── youtube_simple.py        # Класс YouTubeSimpleParser
```

---

## 📊 Таблица парсеров

| Парсер | Файл | Метод | Статус |
|--------|------|-------|--------|
| Telegram | `telegram_posts.py` | `get_new_posts(username, last_post_id)` | ✅ Готово |
| YouTube | `youtube_simple.py` | `get_latest_video_id(username)` | ✅ Готово |

---

## 📡 Telegram Парсер

**Метод:** Веб-парсинг `t.me/s/{username}`

**Возвращает:**
```python
[
    {
        'post_id': '12345',
        'text': 'Текст поста (plain text)',
        'media': [{'type': 'photo', 'url': '...'}],
        'url': 'https://t.me/username/12345',
        'timestamp': None
    }
]
```

**Ограничения:**
- ❌ Форматирование теряется (`.get_text()`)
- ❌ `timestamp` не извлекается
- ❌ Views/Reactions не извлекаются

**Полная документация:** [`telegram.md`](telegram.md)

---

## 📺 YouTube Парсер

**Метод:** HTML-парсинг `youtube.com/@{username}/videos`

**Возвращает:**
```python
video_id = 'abc123xyz'  # 11-символьный ID
```

**Ограничения:**
- ❌ Только video_id (без title, duration, thumbnail)
- ❌ Зависит от вёрстки YouTube
- ❌ Строгий Rate Limiting (1 запрос/сек)

**Полная документация:** [`youtube.md`](youtube.md)

---

## 🔄 Процесс парсинга

```
[TaskDispatcher.start_all()]
  ↓
[MonitoringService.start(interval_minutes=5)]
  ↓
[check_all_sources()]
  ├─→ Semaphore (ограничение параллелизма)
  ├─→ Для каждого источника:
  │   ├─→ Проверка безопасности (URLSecurity)
  │   ├─→ Проверка интервала (5 мин TG, 30 мин YT)
  │   ├─→ Проверка активных назначений
  │   ├─→ Проверка простоя (downtime)
  │   └─→ Парсер:
  │       ├─→ Telegram: get_new_posts()
  │       └─→ YouTube: get_latest_video_id()
  │   ↓
  │   [PostSender]
  │       ├─→ send_media_to_assignment()  (если file_id)
  │       └─→ send_text_to_assignment()   (если нет)
  │   ↓
  │   [Обновление last_post_id в БД + Redis]
  └─→ session.commit()
```

---

## ⚠️ Особенности

### Rate Limiting

| Источник | Токены | Refill | Интервал |
|----------|--------|--------|----------|
| Telegram | 20 | 10/сек | 5 мин |
| YouTube | 5 | 1/сек | 30 мин |

### Кэширование

- **Telegram:** file_id медиа в БД (`CachedMedia`)
- **Telegram:** last_post_id в Redis + БД
- **YouTube:** last_video_id в БД

### Обработка ошибок

- **Exponential Backoff** — при повторяющихся ошибках
- **Should Skip** — после N ошибок подряд источник пропускается
- **Flood Control** — sleep при `429 Too Many Requests`

---

## 🔗 Связанные документы

- [`../04-services/monitoring.md`](../04-services/monitoring.md) — Мониторинг
- [`../04-services/rate-limiting.md`](../04-services/rate-limiting.md) — Rate Limiting
- [`../memory/parsers/README.md`](../memory/parsers/README.md) — Память парсеров

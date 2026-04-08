# 🕸️ Парсеры — Контекст

**Последнее обновление:** 6 апреля 2026
**Версия:** 6.7

---

## 📋 Что это

Парсеры для получения контента из внешних источников: **Telegram** (веб-парсинг + HTML) и **YouTube** (HTML-парсинг).

---

## 🎯 Ключевые файлы

### Telegram

- `core/parser/telegram.py` — проверка существования канала
- `core/parser/telegram_posts.py` — основная функция `get_new_posts()` (HTML + timestamp + альбомы, v6.7)
- `core/utils/html_sanitizer.py` — HTML санитизация (v6.7)
- `core/services/monitoring/telegram_monitor.py` — оркестрация проверки

### YouTube

- `core/parser/youtube_simple.py` — класс `YouTubeSimpleParser`
- `core/services/youtube_simple_service.py` — сервис мониторинга
- `core/services/monitoring/youtube_monitor.py` — оркестрация

---

## ⚙️ Telegram — Процесс

```
GET https://t.me/s/{username}
  ↓
BeautifulSoup(html)
  ↓
Найти div.tgme_widget_message_wrap
  ↓
Для каждого поста:
  ├─→ post_id (из href)
  ├─→ text (get_text() — plain text)
  ├─→ media (фото из CSS, видео из <video>)
  └─→ url (формируется вручную)
  ↓
Список постов (от старых к новым)
```

**Возвращаемая структура:**
```python
{
    'post_id': '12345',        # Строковый ID
    'text': 'Текст поста',     # Plain text (без форматирования)
    'media': [                 # Список медиа
        {'type': 'photo', 'url': '...'},
        {'type': 'video', 'url': '...'}
    ],
    'url': 'https://t.me/username/12345',
    'timestamp': None          # Всегда None (не извлекается)
}
```

---

## ⚙️ YouTube — Процесс

```
GET https://www.youtube.com/@{username}/videos
  ↓
Регулярные выражения
  ↓
Найти data-id="..." или watch?v=...
  ↓
video_id (11 символов)
  ↓
Сравнить с last_video_id в БД
```

**Возвращаемая структура:**
```python
{
    'video_id': 'abc123xyz',   # 11-символьный ID
}
```

---

## ⚠️ Важные решения

### Telegram

- **Веб-парсинг** — `t.me/s/` (не Telethon, не Bot API)
- **Rate Limiting** — 20 токенов, 10/сек refill
- **Exponential Backoff** — при ошибках
- **Дедупликация** — по `post_id` (сравнение с `last_successful_post_id`)

### YouTube

- **Без API Key** — парсинг HTML (не YouTube Data API)
- **Rate Limiting** — 5 токенов, 1/сек refill (строже!)
- **Случайная задержка** — 1-2 сек между запросами
- **Ротация User-Agent** — 4 разных браузера
- **Только video_id** — без title, duration, thumbnail

---

## 🔧 Конфигурация

```bash
# Telegram
RATE_LIMIT_TELEGRAM_TOKENS=20
RATE_LIMIT_TELEGRAM_REFILL=10.0

# YouTube (строже!)
RATE_LIMIT_YOUTUBE_TOKENS=5
RATE_LIMIT_YOUTUBE_REFILL=1.0

# Глобальный
RATE_LIMIT_GLOBAL_PER_MINUTE=60
```

---

## 🔗 Связанные документы

- [`../04-services/monitoring.md`](../04-services/monitoring.md) — Мониторинг
- [`../04-services/rate-limiting.md`](../04-services/rate-limiting.md) — Rate Limiting
- [`../../docs/memory/parsers/telegram.md`](../../docs/memory/parsers/telegram.md) — Память Telegram
- [`../../docs/memory/parsers/youtube.md`](../../docs/memory/parsers/youtube.md) — Память YouTube

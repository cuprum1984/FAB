# YouTube Parser — Контекст

**Последнее обновление:** 4 апреля 2026
**Версия:** 6.6

---

## 📋 Что это

Парсинг YouTube каналов через **HTML-парсинг** (без YouTube Data API).

**Не используется:**
- ❌ YouTube Data API v3
- ❌ OAuth
- ❌ Официальный API

---

## 🎯 Ключевые файлы

| Файл | Назначение |
|------|------------|
| `core/parser/youtube_simple.py` | Класс `YouTubeSimpleParser` |
| `core/services/youtube_simple_service.py` | Сервис мониторинга |
| `core/services/monitoring/youtube_monitor.py` | Оркестрация |

---

## ⚙️ Как работает

### 1. Запрос к `/videos`

```python
url = f"https://www.youtube.com/@{username}/videos"
html = await self.fetch_page(url, username=username)
```

### 2. Поиск video_id

```python
# Паттерн 1: data-id (самый частый)
match = re.search(r'data-id="([a-zA-Z0-9_-]{11})"', html)

# Паттерн 2: watch?v= (запасной)
match = re.search(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
```

### 3. Дедупликация

```python
if source.last_video_id == video_id:
    return  # Нет новых видео
```

---

## 📦 Возвращаемая структура

**Основной метод:**
```python
video_id = await parser.get_latest_video_id(username)
# Возвращает: 'abc123xyz' (11-символьный ID) или None
```

**Полные данные канала:**
```python
data = await parser.get_channel_data(username)
# Возвращает:
{
    'channel_id': 'UC...',           # ID канала
    'channel_title': 'Название',     # Из og:title
    'video_id': 'abc123xyz',         # Последнее видео
}
```

---

## ⚠️ Важные решения

| Версия | Решение | Причина |
|--------|---------|---------|
| **5.0** | Без YouTube API | Не требует API Key |
| **5.0** | Парсинг HTML | "Как видит человек" |
| **5.3** | Rate Limiting (строгий) | 1 запрос/сек |
| **5.3** | Exponential Backoff | При ошибках |
| **6.0** | Ротация User-Agent | 4 разных браузера |
| **6.0** | Случайная задержка | 1-2 сек (вежливость) |

---

## 🔧 Конфигурация

```python
# Rate Limiting (строже чем Telegram!)
RATE_LIMIT_YOUTUBE_TOKENS=5        # Ёмкость ведра
RATE_LIMIT_YOUTUBE_REFILL=1.0      # Токенов/сек
```

---

## 🔄 Поток выполнения

```
youtube_monitor.check_youtube_source()
    ↓
YouTubeSimpleMonitoringService.check_source()
    ↓
parser.get_latest_video_id(username)
    ↓
Сравнить с source.last_video_id
    ↓
Если новое:
    ├─→ _get_source_assignments()
    ├─→ _send_video()
    │   └─→ bot.send_message(chat_id, text, parse_mode="HTML")
    ├─→ source.last_video_id = video_id
    └─→ session.commit()
```

---

## 🔗 Связанные документы

- [`../../docs/05-parsers/youtube.md`](../../docs/05-parsers/youtube.md) — полная документация
- [`../../docs/04-services/youtube.md`](../../docs/04-services/youtube.md) — YouTube Service
- [`../../docs/memory/parsers/README.md`](README.md) — обзор парсеров

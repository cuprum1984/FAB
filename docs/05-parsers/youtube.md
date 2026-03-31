# 📹 YouTube Парсер

**Файл:** `core/parser/youtube_simple.py`  
**Версия:** 5.0 (23 февраля 2026)

---

## 📋 Обзор

Парсер для получения информации о YouTube каналах и новых видео.

---

## 🎯 Основные функции

### `YouTubeParser.get_channel_info(url)`

Получение информации о канале.

**Параметры:**
- `url` — URL канала или @username

**Возвращает:**
```python
dict = {
    'channel_id': str,
    'title': str,
    'description': str,
    'subscribers': str,  # Текст (например, "1.2M")
    'video_count': int,
    'thumbnail': str
}
```

---

### `YouTubeParser.get_latest_videos(channel_id, limit=5)`

Получение последних видео канала.

**Параметры:**
- `channel_id` — ID канала
- `limit` — количество видео (по умолчанию 5)

**Возвращает:**
```python
List[dict] = [
    {
        'video_id': str,
        'title': str,
        'url': str,
        'published': datetime,
        'thumbnail': str,
        'duration': str
    }
]
```

---

## 🔄 Процесс парсинга

```
[Запрос к YouTube]
  ↓
[Получение канала]
  ↓
[Получение видео]
  ↓
[Для каждого видео:]
  ├─→ Извлечение metadata
  ├─→ Проверка даты
  └─→ Сохранение в структуру
  ↓
[Возврат списка видео]
```

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `requests` / `aiohttp` | HTTP запросы |
| `bs4` | Парсинг HTML |
| `core.services.rate_limiter` | Rate Limiting |

---

## ⚠️ Особенности

1. **Rate Limiting:** 1 запрос/сек (строгое ограничение)
2. **Без API:** Использует парсинг HTML (не требует API key)
3. **Exponential Backoff:** При ошибках

---

## 🧪 Тесты

**Файл:** `tests/test_youtube_parser.py`

| Тест | Описание | Статус |
|------|----------|--------|
| `test_get_channel_info` | Информация о канале | ✅ |
| `test_get_latest_videos` | Последние видео | ✅ |

**Всего:** Тесты в составе test_youtube_*.py

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор парсеров
- [`../04-services/rate-limiting.md`](../04-services/rate-limiting.md) — Rate Limiting
- [`../04-services/youtube.md`](../04-services/youtube.md) — YouTube Service
- [`../02-handlers/sources/youtube.md`](../02-handlers/sources/youtube.md) — Добавление YouTube

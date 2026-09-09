# 📹 YouTube Service

**Файл:** `core/services/youtube_simple_service.py`  
**Версия:** 5.0 (23 февраля 2026)

---

## 📋 Обзор

Сервис для работы с YouTube: парсинг, кэширование, проверка новых видео.

---

## 🎯 Основные функции

### `YouTubeService.get_channel_info(url)`

Получение информации о канале.

**Параметры:**
- `url` — URL канала или @username

**Возвращает:**
```python
dict = {
    'title': str,           # Название канала
    'description': str,     # Описание
    'subscribers': str,     # Подписчики (текст)
    'video_count': int,     # Количество видео
    'thumbnail': str        # URL превью
}
```

---

### `YouTubeService.get_latest_videos(channel_id, limit=5)`

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
        'thumbnail': str
    }
]
```

---

### `YouTubeService.check_new_videos(channel_id, last_check)`

Проверка новых видео с последней проверки.

**Параметры:**
- `channel_id` — ID канала
- `last_check` — дата последней проверки

**Возвращает:**
```python
List[dict] = [...]  # Новые видео
```

---

## 🔄 Процесс мониторинга

```
[Планировщик: каждые N минут]
  ↓
[Получение подписок на YouTube]
  ↓
[Для каждого канала:]
  ├─→ Проверка новых видео
  ├─→ Добавление в очередь
  └─→ Обновление last_check
  ↓
[Sender отправляет в темы]
```

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `core.parser.youtube_simple.YouTubeParser` | Парсер YouTube |
| `core.services.rate_limiter` | Rate Limiting |
| `core.models.ContentSource` | Модель источника |
| `core.models.SourceSubscription` | Подписка |

---

## 🗄️ База данных

### Обновляемые поля

| Таблица | Поле | Описание |
|---------|------|----------|
| `content_sources` | `last_check` | Дата последней проверки |
| `content_sources` | `last_video_id` | ID последнего видео |

---

## 🧪 Тесты

**Файл:** `tests/test_youtube_service.py`

| Тест | Описание | Статус |
|------|----------|--------|
| `test_get_channel_info` | Информация о канале | ✅ |
| `test_get_latest_videos` | Последние видео | ✅ |
| `test_check_new_videos` | Проверка новых видео | ✅ |

**Всего:** 11 тестов, 11 ✅

---

## ⚠️ Особенности

1. **Rate Limiting:** 1 запрос/сек (строгое ограничение)
2. **Кэширование:** Кэш информации о канале
3. **Exponential Backoff:** При ошибках API

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор сервисов
- [`../05-parsers/youtube.md`](../05-parsers/youtube.md) — YouTube парсер
- [`rate-limiting.md`](rate-limiting.md) — Rate Limiting

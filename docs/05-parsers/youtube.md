# 📺 YouTube Парсер

**Файл:** `core/parser/youtube_simple.py`
**Версия:** 2.0 (28 февраля 2026)

---

## 📋 Обзор

Простой парсер YouTube каналов через **HTML-парсинг** (без YouTube Data API).

**Принцип:** "Как видит человек" — заходим на `/videos`, берём первое видео.

**Не использует:**
- ❌ YouTube Data API v3
- ❌ OAuth
- ❌ Официальный API

---

## 🎯 Класс `YouTubeSimpleParser`

### Основные методы

#### `get_latest_video_id(username)`

**Основной метод.** Берёт ПЕРВОЕ видео на вкладке `/videos`.

**Параметры:**
- `username` — username канала (без `@`)

**Возвращает:**
```python
str = 'abc123xyz'  # 11-символьный video_id
# или None если не удалось найти
```

---

#### `get_channel_id(username)`

Получить `channel_id` канала (нужно для БД).

**Параметры:**
- `username` — username канала

**Возвращает:**
```python
str = 'UC...'  # channel_id
# или None если не удалось найти
```

---

#### `get_channel_data(username)`

Полные данные канала (для добавления источника).

**Параметры:**
- `username` — username канала

**Возвращает:**
```python
{
    'channel_id': 'UC...',
    'channel_title': 'Название канала',  # Из og:title
    'video_id': 'abc123xyz',
}
```

---

## 🔄 Процесс парсинга

```
1. GET https://www.youtube.com/@{username}/videos
   ↓
2. Регулярные выражения:
   ├─→ Паттерн 1: data-id="([a-zA-Z0-9_-]{11})"
   └─→ Паттерн 2: watch\?v=([a-zA-Z0-9_-]{11})
   ↓
3. Возврат video_id
```

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `aiohttp` | HTTP-запросы |
| `re` | Регулярные выражения |
| `random` | Ротация User-Agent |
| `core.services.rate_limiter` | Rate Limiting |

---

## ⚠️ Особенности

### 1. Только video_id

Парсер возвращает **только `video_id`**. Без:
- ❌ `title`
- ❌ `duration`
- ❌ `thumbnail`
- ❌ `published`

### 2. Rate Limiting (строгий!)

```python
RATE_LIMIT_YOUTUBE_TOKENS=5        # Ёмкость ведра
RATE_LIMIT_YOUTUBE_REFILL=1.0      # Токенов/сек
```

**Дополнительно:**
- Случайная задержка 1-2 сек между запросами
- Ротация User-Agent (4 браузера)

### 3. Exponential Backoff

При повторяющихся ошибках парсер увеличивает задержку между запросами.

### 4. Глобальный экземпляр

```python
from core.parser.youtube_simple import get_parser

parser = get_parser()  # Глобальный синглтон
video_id = await parser.get_latest_video_id('username')
```

---

## 🧪 Тесты

Тесты находятся в `tests/test_youtube_*.py`.

| Тест | Описание | Статус |
|------|----------|--------|
| `test_get_channel_id` | Получение channel_id | ✅ |
| `test_get_latest_video_id` | Получение последнего видео | ✅ |
| `test_get_channel_data` | Полные данные канала | ✅ |

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор парсеров
- [`../04-services/youtube.md`](../04-services/youtube.md) — YouTube Service
- [`../memory/parsers/youtube.md`](../memory/parsers/youtube.md) — Память парсера

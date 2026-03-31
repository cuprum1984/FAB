# 📺 Telegram Парсер

**Файл:** `core/parser/telegram.py`  
**Версия:** 2.0 (10 февраля 2026)

---

## 📋 Обзор

Парсер для получения постов из публичных Telegram каналов.

---

## 🎯 Основные функции

### `TelegramParser.get_channel_info(username)`

Получение информации о канале.

**Параметры:**
- `username` — username канала (без @)

**Возвращает:**
```python
dict = {
    'username': str,
    'title': str,
    'description': str,
    'subscribers': int,
    'photo': str  # URL фото
}
```

---

### `TelegramParser.get_posts(username, limit=10)`

Получение последних постов канала.

**Параметры:**
- `username` — username канала
- `limit` — количество постов (по умолчанию 10)

**Возвращает:**
```python
List[dict] = [
    {
        'post_id': int,
        'text': str,
        'date': datetime,
        'views': int,
        'forwards': int,
        'media': List[dict]  # Фото, видео, документы
    }
]
```

---

## 📁 Обработка постов

**Файл:** `telegram_posts.py`

### `PostParser.parse_post(post)`

Разбор поста на компоненты.

**Извлекает:**
- Текст
- Фото (URL)
- Видео (файл ID)
- Документы (файл ID)
- Ссылки
- Пересылки

---

## 🔄 Процесс парсинга

```
[Запрос к Telegram API]
  ↓
[Получение канала]
  ↓
[Получение постов]
  ↓
[Для каждого поста:]
  ├─→ Извлечение текста
  ├─→ Извлечение медиа
  ├─→ Обработка ссылок
  └─→ Сохранение в структуру
  ↓
[Возврат списка постов]
```

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `telethon` | Telegram клиент |
| `core.services.rate_limiter` | Rate Limiting |
| `core.parser.telegram_posts` | Обработка постов |

---

## ⚠️ Особенности

1. **Rate Limiting:** 10 запросов/сек
2. **Кэширование:** Кэш информации о канале
3. **Обработка ошибок:** Exponential Backoff

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор парсеров
- [`../04-services/rate-limiting.md`](../04-services/rate-limiting.md) — Rate Limiting
- [`../02-handlers/sources/telegram.md`](../02-handlers/sources/telegram.md) — Добавление Telegram

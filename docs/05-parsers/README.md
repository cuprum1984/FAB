# 🕸️ Парсеры

**Папка:** `core/parser/`

---

## 📋 Обзор

Парсеры для получения контента из внешних источников: Telegram, YouTube.

---

## 📁 Структура

```
core/parser/
├── telegram.py              # Telegram парсер
├── telegram_posts.py        # Обработка постов Telegram
└── youtube_simple.py        # YouTube парсер
```

---

## 📊 Таблица парсеров

| Парсер | Файл | Описание | Статус |
|--------|------|----------|--------|
| [`telegram.md`](telegram.md) | `telegram.py` | Парсинг Telegram каналов | 🔴 Не начато |
| [`youtube.md`](youtube.md) | `youtube_simple.py` | Парсинг YouTube каналов | 🔴 Не начато |

---

## 🔄 Процесс парсинга

```
[Планировщик]
  ↓
[Получение источников из БД]
  ↓
[Для каждого источника:]
  ├─→ Проверка Rate Limit
  ├─→ Запрос к API
  ├─→ Обработка ответа
  ├─→ Извлечение постов/видео
  └─→ Сохранение в очередь
  ↓
[Sender отправляет в темы]
```

---

## ⚠️ Особенности

1. **Rate Limiting:** Все парсеры используют Rate Limiter
2. **Кэширование:** Кэш результатов для производительности
3. **Обработка ошибок:** Exponential Backoff при ошибках

---

## 🔗 Связанные документы

- [`../04-services/README.md`](../04-services/README.md) — Сервисы
- [`../04-services/rate-limiting.md`](../04-services/rate-limiting.md) — Rate Limiting
- [`../04-services/monitoring.md`](../04-services/monitoring.md) — Мониторинг

# 🔧 Сервисы

**Папка:** `core/services/`

---

## 📋 Обзор

Бизнес-логика проекта: обработка данных, парсинг, очистка, назначения.

---

## 📁 Структура

```
core/services/
├── rate_limiter.py                # Rate Limiting (Token Bucket)
├── youtube_simple_service.py      # YouTube сервис
│
├── cleanup/                       # GDPR очистка
│   ├── base.py                    # Базовый класс
│   ├── user_cleanup.py            # Очистка пользователей
│   ├── subscription_cleanup.py    # Очистка подписок
│   ├── topic_cleanup.py           # Очистка тем
│   └── media_cleanup.py           # Очистка медиа
│
├── destinations/                  # Назначения
│   ├── access.py                  # Проверка доступа
│   ├── assignments.py             # Назначения источников
│   ├── cache.py                   # Кэш назначений
│   ├── sources.py                 # Управление источниками
│   ├── subscriptions.py           # Подписки
│   ├── topics.py                  # Управление темами
│   └── topic_utils.py             # Утилиты тем
│
└── monitoring/                    # Мониторинг
    ├── base.py                    # Базовый класс
    ├── group_checker.py           # Проверка групп
    ├── post_sender.py             # Отправка постов
    ├── telegram_monitor.py        # Мониторинг Telegram
    └── youtube_monitor.py         # Мониторинг YouTube
```

---

## 📊 Таблица сервисов

| Сервис | Файл | Описание | Статус |
|--------|------|----------|--------|
| [`rate-limiting.md`](rate-limiting.md) | `rate_limiter.py` | Rate Limiting (Token Bucket) | ✅ Готово |
| [`limits.md`](limits.md) | `limits.py` | Лимиты Free плана | ✅ Готово (v6.4) |
| [`monitoring.md`](monitoring.md) | `monitoring/` | Мониторинг источников | ✅ Готово |
| [`destinations.md`](destinations.md) | `destinations/` | Назначения источников | 🔴 Не начато |
| [`cleanup-gdpr.md`](cleanup-gdpr.md) | `cleanup/` | GDPR очистка | 🔴 Не начато |
| [`youtube.md`](youtube.md) | `youtube_simple_service.py` | YouTube сервис | 🔴 Не начато |

---

## 🔗 Связанные документы

- [`../02-handlers/README.md`](../02-handlers/README.md) — Хендлеры
- [`../05-parsers/README.md`](../05-parsers/README.md) — Парсеры
- [`../06-database/README.md`](../06-database/README.md) — База данных

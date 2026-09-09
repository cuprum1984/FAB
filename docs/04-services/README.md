# 🔧 Сервисы

**Папка:** `core/services/`

---

## 📋 Обзор

Бизнес-логика проекта: мониторинг источников, отправка постов, Rate Limiting, GDPR очистка, назначения.

---

## 📁 Структура

```
core/services/
├── __init__.py
├── rate_limiter.py                # Rate Limiting (Token Bucket)
├── limits.py                      # Лимиты Free плана (v6.4)
├── cleanup_service.py             # Устаревший (заменён cleanup/)
├── destination_service.py         # Устаревший (заменён destinations/)
├── monitoring_service.py          # Устаревший (заменён monitoring/)
├── youtube_simple_service.py      # YouTube сервис
│
├── cleanup/                       # GDPR очистка
│   ├── base.py                    # Базовый класс
│   ├── user_cleanup.py            # Очистка пользователей
│   ├── subscription_cleanup.py    # Очистка подписок
│   ├── topic_cleanup.py           # Очистка тем
│   └── media_cleanup.py           # Очистка медиа
│
├── destinations/                  # Назначения источников
│   ├── access.py                  # Проверка доступа
│   ├── assignments.py             # Назначения источников
│   ├── cache.py                   # Кэш last_post_id
│   ├── sources.py                 # Управление источниками
│   ├── subscriptions.py           # Подписки
│   ├── topics.py                  # Управление темами
│   └── topic_utils.py             # Утилиты тем
│
└── monitoring/                    # Мониторинг
    ├── base.py                    # Основной цикл MonitoringService
    ├── telegram_monitor.py        # Проверка Telegram каналов
    ├── youtube_monitor.py         # Проверка YouTube каналов
    ├── post_sender.py             # Отправка постов в темы
    └── group_checker.py           # Проверка групп (2 раза в день)
```

---

## 📊 Таблица сервисов

| Сервис | Файл | Описание | Статус |
|--------|------|----------|--------|
| Rate Limiting | `rate_limiter.py` | Token Bucket + Exponential Backoff | ✅ Готово (v5.3) |
| Лимиты Free | `limits.py` | Проверка лимитов Free плана | ✅ Готово (v6.4) |
| Мониторинг | `monitoring/` | Основной цикл + подсервисы | ✅ Готово (v6.2) |
| Назначения | `destinations/` | Управление источниками/темами | ✅ Готово |
| GDPR очистка | `cleanup/` | Очистка неактивных пользователей | ✅ Готово (v5.6) |
| YouTube | `youtube_simple_service.py` | Проверка YouTube каналов | ✅ Готово (v5.0) |

---

## 🔄 Основной цикл

```
TaskDispatcher.start_all()
    ↓
MonitoringService.start(interval_minutes=5)
    ↓
while is_running:
    ├─→ check_all_sources()
    │   ├─→ Semaphore (ограничение параллелизма)
    │   ├─→ Для каждого источника:
    │   │   ├─→ Проверка безопасности
    │   │   ├─→ Проверка интервала
    │   │   ├─→ Проверка назначений
    │   │   ├─→ Проверка простоя
    │   │   └─→ Парсер + PostSender
    │   └─→ session.commit()
    └─→ smart_sleep()
```

---

## 🔗 Связанные документы

- [`rate-limiting.md`](rate-limiting.md) — Rate Limiting
- [`limits.md`](limits.md) — Лимиты Free плана
- [`monitoring.md`](monitoring.md) — Мониторинг источников
- [`destinations.md`](destinations.md) — Назначения
- [`cleanup-gdpr.md`](cleanup-gdpr.md) — GDPR очистка
- [`youtube.md`](youtube.md) — YouTube сервис
- [`../05-parsers/README.md`](../05-parsers/README.md) — Парсеры
- [`../06-database/README.md`](../06-database/README.md) — База данных

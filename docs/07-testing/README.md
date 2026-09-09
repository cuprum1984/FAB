# 🧪 Тестирование

**Папка:** `tests/`

---

## 📋 Обзор

Тесты проекта на pytest (99 тестов, 99 ✅).

---

## 📁 Структура

```
tests/
├── conftest.py                # Фикстуры pytest
├── fixtures/                  # Дополнительные фикстуры
│   ├── db.py                  # БД фикстуры
│   ├── bot.py                 # Бот фикстуры
│   └── data.py                # Тестовые данные
│
├── test_cleanup.py            # GDPR очистка (14 тестов)
├── test_destination_service.py # Destination Service (23 теста)
├── test_monitoring_service.py # Monitoring Service (9 тестов)
├── test_topic_assignments.py  # Назначения (8 тестов)
├── test_rate_limiter.py       # Rate Limiting (23 теста)
├── test_youtube_parser.py     # YouTube парсер
├── test_youtube_service.py    # YouTube сервис
└── test_parser.py             # Парсеры
```

---

## 📊 Статистика тестов

| Категория | Файл | Тестов | Пройдено |
|-----------|------|--------|----------|
| Очистка (GDPR) | `test_cleanup.py` | 14 | 14 ✅ |
| Destination Service | `test_destination_service.py` | 23 | 23 ✅ |
| Monitoring Service | `test_monitoring_service.py` | 9 | 9 ✅ |
| Назначения | `test_topic_assignments.py` | 8 | 8 ✅ |
| Rate Limiting | `test_rate_limiter.py` | 23 | 23 ✅ |
| YouTube | `test_youtube_*.py` | 11 | 11 ✅ |
| **ИТОГО** | | **99** | **99 ✅** (5 skip) |

---

## 📝 Документы

| Файл | Описание | Статус |
|------|----------|--------|
| [`fixtures.md`](fixtures.md) | Фикстуры pytest | 🔴 Не начато |
| [`categories.md`](categories.md) | Категории тестов | 🔴 Не начато |
| [`running.md`](running.md) | Запуск тестов | 🔴 Не начато |

---

## 🔗 Связанные документы

- [`../01-general/deployment.md`](../01-general/deployment.md) — Развёртывание
- [`../04-services/README.md`](../04-services/README.md) — Сервисы

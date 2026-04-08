# Сервисы — Контекст

**Последнее обновление:** 6 апреля 2026

---

## 📋 Обзор

| Сервис | Файл | Назначение |
|--------|------|------------|
| **PostSender** | `post_sender.py` | Отправка постов (HTML + медиа) |
| **Rate Limiter** | `rate_limiter.py` | Token Bucket + Backoff |
| **Telegram Monitor** | `telegram_monitor.py` | Проверка TG каналов |
| **Cleanup** | `cleanup/` | GDPR очистка |
| **Destinations** | `destinations/` | Назначения источников |
| **Monitoring** | `monitoring/` | Мониторинг групп |

---

## 📁 PostSender (v6.7)

**Файл:** [`post_sender.md`](post_sender.md)

- HTML + медиа по URL + Inline кнопка
- Скачивание во временный файл → FSInputFile → удаление
- Fallback на plain text (теги удаляются, не экранируются)
- Caption ≤ 1024 символа

---

## 📁 Rate Limiter (v5.3)

**Файл:** `rate_limiter.py`

- Token Bucket (Telegram: 20 токенов, 10/сек; YouTube: 5, 1/сек)
- Exponential Backoff при ошибках
- Singleton паттерн

---

## 📁 Cleanup (v5.6)

**Папка:** `cleanup/` (5 файлов)

- GDPR очистка неактивных пользователей
- Удаление мёртвых групп и тем
- Очистка orphan источников

---

## 📁 Destinations (v4.0)

**Папка:** `destinations/` (7 файлов)

- Назначения источников в темы
- Проверка доступа
- Source last post ID

---

## 📁 Monitoring (v3.0)

**Папка:** `monitoring/` (5 файлов)

- Проверка статуса групп
- APScheduler фоновые задачи

---

## 🔗 Связанные документы

- [`../parsers/README.md`](../parsers/README.md) — парсеры
- [`../database/README.md`](../database/README.md) — база данных

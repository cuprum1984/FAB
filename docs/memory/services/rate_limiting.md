# Rate Limiting — Контекст

**Последнее обновление:** 2026-03-30  
**Версия:** 5.3+

---

## 📋 Что это

Защита от блокировок Telegram/YouTube за частые запросы.

---

## 🎯 Ключевые файлы

- `core/services/rate_limiter.py` — Rate Limiter
- `core/parser/telegram.py` — парсер Telegram
- `core/parser/youtube_simple.py` — парсер YouTube

---

## ⚙️ Алгоритм

**Token Bucket + Exponential Backoff**

```
Telegram: 20 токенов, 10 токенов/сек
YouTube:   5 токенов,  1 токен/сек
Глобально: 60 запросов/мин
```

---

## ⚠️ Важные решения

- **v5.3:** Token Bucket для каждого домена
- **v5.3:** Exponential Backoff при ошибках
- **v5.3:** Глобальный лимит запросов/мин

---

## 🔧 Конфигурация

```bash
RATE_LIMIT_TELEGRAM_TOKENS=20
RATE_LIMIT_TELEGRAM_REFILL=10.0
RATE_LIMIT_YOUTUBE_TOKENS=5
RATE_LIMIT_YOUTUBE_REFILL=1.0
RATE_LIMIT_GLOBAL_PER_MINUTE=60
```

---

## 📊 Backoff

```
1 ошибка: 1с → 2 ошибки: 2с → 3 ошибки: 4с → 4 ошибки: 8с
```

---

## 🔗 Связанные документы

- `docs/04-services/rate-limiting.md` — полная документация
- `docs/09-versions/v5.3.md` — версия

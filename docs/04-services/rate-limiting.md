# Rate Limiting в MyAggryBot

**Версия:** 5.3  
**Дата:** 28 февраля 2026

---

## 📋 Описание

Rate limiting защищает бота от блокировок со стороны Telegram и YouTube за слишком частые запросы.

### Проблемы которые решает

- ❌ **Блокировка IP** за частые запросы
- ❌ **429 Too Many Requests** ошибки
- ❌ **Временные баны** аккаунта
- ❌ **DNS ошибки** без обработки

### Решение

- ✅ **Token Bucket** алгоритм для каждого домена
- ✅ **Exponential Backoff** при ошибках
- ✅ **Глобальный лимит** запросов в минуту
- ✅ **Статистика** и логирование

---

## 🔧 Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Rate Limiter                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐         ┌─────────────┐               │
│  │  Telegram   │         │   YouTube   │               │
│  │   Bucket    │         │   Bucket    │               │
│  │  20 токенов │         │   5 токенов │               │
│  │  10 ток/сек │         │   1 ток/сек │               │
│  └─────────────┘         └─────────────┘               │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │        Global Limit: 60 запросов/мин        │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │         Error Backoff (экспонента)          │       │
│  │  1ош: 1с → 2ош: 2с → 3ош: 4с → 4ош: 8с     │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Конфигурация

### Переменные окружения (.env)

```bash
# Telegram: 10 запросов/сек, ведро 20 токенов
RATE_LIMIT_TELEGRAM_TOKENS=20
RATE_LIMIT_TELEGRAM_REFILL=10.0

# YouTube: 1 запрос/сек, ведро 5 токенов
RATE_LIMIT_YOUTUBE_TOKENS=5
RATE_LIMIT_YOUTUBE_REFILL=1.0

# Глобальный лимит: 60 запросов в минуту
RATE_LIMIT_GLOBAL_PER_MINUTE=60
```

### Настройки по умолчанию

| Параметр | Значение | Описание |
|----------|----------|----------|
| `RATE_LIMIT_TELEGRAM_TOKENS` | 20 | Ёмкость ведра Telegram |
| `RATE_LIMIT_TELEGRAM_REFILL` | 10.0 | Токенов в секунду (Telegram) |
| `RATE_LIMIT_YOUTUBE_TOKENS` | 5 | Ёмкость ведра YouTube |
| `RATE_LIMIT_YOUTUBE_REFILL` | 1.0 | Токенов в секунду (YouTube) |
| `RATE_LIMIT_GLOBAL_PER_MINUTE` | 60 | Глобальный лимит запросов/мин |

---

## 💡 Использование

### В парсерах

```python
from core.services.rate_limiter import get_rate_limiter

rate_limiter = get_rate_limiter()

# Перед запросом к Telegram
wait_time = await rate_limiter.acquire("telegram")
if wait_time > 0:
    await asyncio.sleep(wait_time)

# Делаем запрос к Telegram
response = await session.get("https://t.me/s/channel")

# При успехе
rate_limiter.record_success("telegram", "channel_name")

# При ошибке
rate_limiter.record_error("telegram", "channel_name")
```

### Проверка на пропуск

```python
# Пропустить источник после 5 ошибок подряд
if rate_limiter.should_skip_source("telegram", "channel_name"):
    logger.warning("⏭️ Пропускаем канал: слишком много ошибок")
    continue

# Получить текущую задержку backoff
delay = rate_limiter.get_backoff_delay("telegram", "channel_name")
if delay > 0:
    await asyncio.sleep(delay)
```

---

## 📈 Статистика

### Получение статистики

```python
stats = rate_limiter.get_stats()
# {
#     "telegram": {
#         "total_requests": 100,
#         "total_waits": 10,
#         "avg_wait_time": 0.5,
#         "error_rate": 0.05
#     },
#     "youtube": {...},
#     "global": {...}
# }
```

### Статус bucket'ов

```python
status = rate_limiter.get_bucket_status()
# {
#     "telegram": {
#         "tokens": 15.5,
#         "capacity": 20,
#         "refill_rate": 10.0
#     },
#     "youtube": {...}
# }
```

---

## 🔍 Алгоритмы

### Token Bucket

```
Ведро ёмкостью N токенов
Токены добавляются со скоростью R токенов/сек
Каждый запрос потребляет 1 токен
Если токенов нет — ждём пока восстановятся
```

**Пример для Telegram:**
- Ёмкость: 20 токенов
- Скорость: 10 токенов/сек
- Можно сделать: 20 запросов сразу + 10 запросов/сек

**Пример для YouTube:**
- Ёмкость: 5 токенов
- Скорость: 1 токен/сек
- Можно сделать: 5 запросов сразу + 1 запрос/сек

### Exponential Backoff

```
Задержка = min(база * 2^(ошибки-1), максимум) + jitter

где:
- база = 1 секунда
- максимум = 60 секунд
- jitter = ±10% (случайность)
```

**Пример:**
| Ошибки | Задержка |
|--------|----------|
| 1 | 1 сек |
| 2 | 2 сек |
| 3 | 4 сек |
| 4 | 8 сек |
| 5+ | Пропуск источника |

---

## 🧪 Тесты

### Запуск тестов

```bash
# Все тесты rate limiter
pytest tests/test_rate_limiter.py -v

# Конкретный тест
pytest tests/test_rate_limiter.py::TestTokenBucket::test_acquire_tokens -v

# Тесты производительности
pytest tests/test_rate_limiter.py::TestPerformance -v
```

### Покрытие

- ✅ Token Bucket алгоритм (5 тестов)
- ✅ Error Backoff (5 тестов)
- ✅ RateLimiter интеграция (9 тестов)
- ✅ Singleton паттерн (2 теста)
- ✅ Производительность (2 теста)

**Всего:** 23 теста, 100% покрытие

---

## 🛠️ Отладка

### Логирование

```python
# Включить debug логи
logging.getLogger("core.services.rate_limiter").setLevel(logging.DEBUG)

# Примеры логов:
# ⏳ Rate limit Telegram: ждём 0.50с
# ✅ Успех telegram (channel_name)
# ⚠️ Error backoff для channel_name: 3 ошибок, задержка 4.2с
# ❌ Ошибка telegram (channel_name): backoff 4.2с
# ⏭️ Пропускаем channel_name: слишком много ошибок подряд
```

### Мониторинг

```python
# Проверка статуса
status = rate_limiter.get_bucket_status()
print(f"Telegram токены: {status['telegram']['tokens']}")
print(f"YouTube токены: {status['youtube']['tokens']}")

# Проверка статистики
stats = rate_limiter.get_stats()
print(f"Ошибки Telegram: {stats['telegram']['error_rate']*100:.1f}%")
```

---

## 📝 Файлы

| Файл | Описание |
|------|----------|
| `core/services/rate_limiter.py` | Основной модуль rate limiting |
| `core/parser/telegram.py` | Парсер Telegram с rate limiting |
| `core/parser/youtube_simple.py` | Парсер YouTube с rate limiting |
| `tests/test_rate_limiter.py` | Тесты (23 теста) |
| `.env.example` | Шаблон переменных окружения |

---

## 🔗 Ссылки

- [Token Bucket алгоритм](https://en.wikipedia.org/wiki/Token_bucket)
- [Exponential Backoff](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Rate Limiting Best Practices](https://stripe.com/blog/rate-limiters)

---

**Обновлено:** 28 февраля 2026  
**Версия:** 5.3

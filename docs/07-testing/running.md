# 🧪 Запуск тестов

**Версия:** 5.0  
**Последнее обновление:** 30 марта 2026

---

## 🚀 Быстрый старт

### Запуск всех тестов

```bash
pytest -v
```

### Запуск с выводом покрытия

```bash
pytest -v --cov=core --cov=bot
```

---

## 📊 Запуск отдельных категорий

### Тесты очистки (GDPR)

```bash
pytest tests/test_cleanup.py -v
```

### Тесты Destination Service

```bash
pytest tests/test_destination_service.py -v
```

### Тесты Monitoring Service

```bash
pytest tests/test_monitoring_service.py -v
```

### Тесты назначений

```bash
pytest tests/test_topic_assignments.py -v
```

### Тесты Rate Limiting

```bash
pytest tests/test_rate_limiter.py -v
```

### Тесты YouTube

```bash
pytest tests/test_youtube_parser.py -v
pytest tests/test_youtube_service.py -v
```

---

## 🔍 Фильтрация тестов

### По имени

```bash
# Тесты с "gdpr" в имени
pytest -k gdpr -v

# Тесты с "cascade" в имени
pytest -k cascade -v

# Тесты с "rate" в имени
pytest -k rate -v
```

### По маркерам

```bash
# Медленные тесты
pytest -m slow -v

# Тесты БД
pytest -m database -v
```

---

## 📁 Конфигурация

**Файл:** `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

---

## 🔧 Фикстуры

### Автосоздание

Фикстуры автоматически создают:
- Тестовую БД (SQLite)
- Тестового бота
- Тестовые данные

### Использование

```python
async def test_example(db_session):
    # db_session автоматически создаётся
    user = await create_test_user(db_session)
    assert user is not None
```

---

## 📊 Покрытие

### Запуск с покрытием

```bash
pytest --cov=core --cov=bot --cov-report=html
```

### Открыть отчёт

```bash
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## ⚠️ Особенности

1. **Изоляция:** Каждый тест в отдельной транзакции
2. **Rollback:** Изменения откатываются после теста
3. **Async:** Все тесты асинхронные (asyncio_mode = auto)

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор тестирования
- [`fixtures.md`](fixtures.md) — Фикстуры
- [`../01-general/deployment.md`](../01-general/deployment.md) — Развёртывание

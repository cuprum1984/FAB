# 📂 Категории тестов

**Версия:** 5.0  
**Последнее обновление:** 30 марта 2026

---

## 📋 Обзор

Тесты разделены по категориям для удобного запуска.

---

## 📊 Категории

### 1. Очистка (GDPR)

**Файл:** `tests/test_cleanup.py`  
**Тестов:** 14  
**Статус:** ✅ 14/14

| Тест | Описание |
|------|----------|
| `test_check_inactive_users` | Проверка неактивных пользователей |
| `test_delete_user` | Удаление пользователя |
| `test_cascade_cleanup` | Каскадная очистка данных |
| `test_cleanup_old_media` | Очистка старого кэша медиа |

**Запуск:**
```bash
pytest tests/test_cleanup.py -v
pytest -k gdpr -v
```

---

### 2. Destination Service

**Файл:** `tests/test_destination_service.py`  
**Тестов:** 23  
**Статус:** ✅ 23/23

| Тест | Описание |
|------|----------|
| `test_get_user_groups` | Получение групп пользователя |
| `test_create_or_update_topic` | Создание/обновление темы |
| `test_topic_utils` | Утилиты тем |
| `test_cascade_delete` | Каскадное удаление |

**Запуск:**
```bash
pytest tests/test_destination_service.py -v
pytest -k destination -v
```

---

### 3. Monitoring Service

**Файл:** `tests/test_monitoring_service.py`  
**Тестов:** 9  
**Статус:** ✅ 9/9

| Тест | Описание |
|------|----------|
| `test_monitor_sources` | Мониторинг источников |
| `test_check_group_access` | Проверка доступа к группе |
| `test_post_sender` | Отправка постов |

**Запуск:**
```bash
pytest tests/test_monitoring_service.py -v
pytest -k monitoring -v
```

---

### 4. Назначения (Topic Assignments)

**Файл:** `tests/test_topic_assignments.py`  
**Тестов:** 8  
**Статус:** ✅ 8/8

| Тест | Описание |
|------|----------|
| `test_create_assignment` | Создание назначения |
| `test_cascade_delete_assignment` | Каскадное удаление |
| `test_unique_constraint` | Уникальность назначения |

**Запуск:**
```bash
pytest tests/test_topic_assignments.py -v
pytest -k assignment -v
```

---

### 5. Rate Limiting

**Файл:** `tests/test_rate_limiter.py`  
**Тестов:** 23  
**Статус:** ✅ 23/23

| Тест | Описание |
|------|----------|
| `test_token_bucket` | Алгоритм Token Bucket |
| `test_acquire` | Получение токена |
| `test_exponential_backoff` | Экспоненциальная задержка |
| `test_global_limit` | Глобальный лимит |

**Запуск:**
```bash
pytest tests/test_rate_limiter.py -v
pytest -k rate -v
```

---

### 6. YouTube

**Файлы:** `tests/test_youtube_parser.py`, `tests/test_youtube_service.py`  
**Тестов:** 11  
**Статус:** ✅ 11/11

| Тест | Описание |
|------|----------|
| `test_get_channel_info` | Информация о канале |
| `test_get_latest_videos` | Последние видео |
| `test_check_new_videos` | Проверка новых видео |

**Запуск:**
```bash
pytest tests/test_youtube_*.py -v
pytest -k youtube -v
```

---

### 7. Парсеры

**Файл:** `tests/test_parser.py`  
**Тестов:** N/A  
**Статус:** 🔴 В разработке

---

## 🏷️ Маркеры pytest

### Встроенные маркеры

| Маркер | Описание |
|--------|----------|
| `@pytest.mark.asyncio` | Асинхронный тест |
| `@pytest.mark.slow` | Медленный тест |
| `@pytest.mark.database` | Тест с БД |

### Пользовательские маркеры

```python
@pytest.mark.gdpr
async def test_cleanup():
    ...

@pytest.mark.cascade
async def test_cascade_delete():
    ...
```

**Запуск по маркеру:**
```bash
pytest -m gdpr -v
pytest -m cascade -v
pytest -m "not slow" -v
```

---

## 📊 Итоговая статистика

| Категория | Файл | Тестов | Пройдено |
|-----------|------|--------|----------|
| Очистка (GDPR) | `test_cleanup.py` | 14 | 14 ✅ |
| Destination Service | `test_destination_service.py` | 23 | 23 ✅ |
| Monitoring Service | `test_monitoring_service.py` | 9 | 9 ✅ |
| Назначения | `test_topic_assignments.py` | 8 | 8 ✅ |
| Rate Limiting | `test_rate_limiter.py` | 23 | 23 ✅ |
| YouTube | `test_youtube_*.py` | 11 | 11 ✅ |
| **ИТОГО** | | **99** | **99 ✅** |

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор тестирования
- [`fixtures.md`](fixtures.md) — Фикстуры
- [`running.md`](running.md) — Запуск тестов

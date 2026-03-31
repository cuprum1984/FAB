# Задача: Аудит и организация архитектуры фоновых задач (Tasks Architecture Refactor)

**Время:** 16:30  
**Дата:** 17.03.2026  
**Приоритет:** 🔴 ПРИОРИТЕТ 0 (Фундамент для всех оптимизаций)  
**Оценка времени:** ~3.5 часа  
**Статус:** Подготовка к v6.1  

---

## 📋 Контекст

**Проект:** MyAggryBot (Telegram бот-агрегатор)  
**Документ:** SCALABILITY_PLAN.md (раздел "🔍 Анализ текущей архитектуры")  
**Текущая проблема:** 
- Файл `core/tasks/monitor.py` пустой (0 строк кода)
- Логика мониторинга размазана по `core/services/monitoring/base.py`
- Нет единой точки входа для фоновых задач
- Неясно, где и как запускается основной цикл мониторинга

**Цель:** Создать чёткую архитектуру задач, которая работает одинаково хорошо:
- ✅ **Локально** (домашний ПК, разработка, отладка)
- ✅ **Продакшен** (3 отдельных хоста: БД, Бот, Redis — без Docker или с минимальным использованием)

---

## 🎯 Требования к архитектуре

### 1. Единая точка входа для всех задач

Все фоновые задачи должны запускаться из одного места:

```
bot/main.py (точка входа бота)
    ├── Запуск polling / webhook
    └── Запуск фоновых задач (TaskDispatcher)
            ├── Мониторинг источников
            ├── Очистка устаревших данных
            └── Проверка статуса групп
```

### 2. Разделение ответственности

| Слой | Модуль | Ответственность | Пример |
|------|--------|-----------------|--------|
| **Tasks** | `core/tasks/*.py` | КОГДА и КАК запускать (оркестрация) | Циклы, интервалы, параллелизм |
| **Services** | `core/services/*.py` | ЧТО делать (бизнес-логика) | Проверка источника, отправка поста |
| **Bot** | `bot/handlers/*.py` | Реакция на действия пользователя | Команды, кнопки, сообщения |

### 3. Одинаковый код для dev и prod

**НЕ делать:**
- ❌ Разные файлы для dev/prod
- ❌ Hardcoded пути или настройки
- ❌ Зависимость от конкретных переменных окружения
- ❌ Жёсткая привязка к Docker (продакшен: 3 отдельных хоста)

**Делать:**
- ✅ Переключение через переменные окружения (`ENV=development` / `ENV=production`)
- ✅ Условная логика внутри одного файла
- ✅ Конфигурация подключений через ENV (хост БД, хост Redis)
- ✅ Поддержка запуска как напрямую (python main.py), так и через systemd/supervisor
- ✅ Опционально: Docker только для локальной разработки

---

## 🏗️ Архитектура продакшена (3 хоста)

```
┌─────────────────┐
│   Хост 1: БД    │
│   PostgreSQL    │
│   (отдельно)    │
│   Порт: 5432    │
└────────┬────────┘
         │
         │ сеть (5432)
         │
┌────────┴────────┐     ┌─────────────────┐
│   Хост 3: Бот   │────>│   Хост 2: Redis │
│   (приложение)  │     │   (кэш/очередь) │
│   Python 3.12   │<────│   (отдельно)    │
│   systemd       │     │   Порт: 6379    │
└─────────────────┘     └─────────────────┘
```

**Преимущества:**
- ✅ Изоляция ресурсов (БД не конкурирует с ботом за CPU/RAM)
- ✅ Независимое масштабирование (можно добавить RAM только БД)
- ✅ Безопасность (БД не доступна извне, только из сети бота)
- ✅ Простота резервного копирования (отдельный хост БД)

---

## 🔍 Часть 1: АУДИТ (Найти и задокументировать)

### Задание 1.1: Найти все точки входа

**Найти в коде:**
1. Где вызывается `MonitoringService.start()`?
2. Есть ли другие фоновые циклы (cleanup, scheduler)?
3. Как запускается бот сейчас (`bot/main.py`)?

**Команды для поиска:**
```bash
# Поиск вызовов MonitoringService
grep -r "MonitoringService" --include="*.py" .

# Поиск async def start()
grep -r "async def start" --include="*.py" .

# Поиск asyncio.create_task
grep -r "asyncio.create_task" --include="*.py" .

# Поиск background, scheduler, cleanup
grep -r "background\|scheduler\|cleanup" --include="*.py" .
```

**Ожидаемый результат:**
- Список всех файлов, где запускаются фоновые задачи
- Понимание текущего потока выполнения
- Выявление дублирования логики

---

### Задание 1.2: Проанализировать текущую структуру `core/tasks/`

**Проверить файлы:**
- `core/tasks/__init__.py` — есть ли экспорты?
- `core/tasks/monitor.py` — почему пустой?
- `core/tasks/scheduler.py` — что внутри?
- Есть ли другие файлы в `core/tasks/`?

**Ожидаемый результат:**
- Понимание, какие файлы уже существуют
- Решение: удалить, переписать или сохранить каждый файл

---

### Задание 1.3: Найти все фоновые процессы

**Проверить сервисы:**
- `core/services/monitoring/base.py` — основной цикл мониторинга
- `core/services/cleanup_service.py` — очистка данных
- `core/services/monitoring/group_checker.py` — проверка групп (2 раза в день)
- Другие сервисы с бесконечными циклами `while True`

**Ожидаемый результат:**
- Список всех фоновых процессов
- Их интервалы выполнения
- Зависимости между процессами

---

## 🏗️ Часть 2: ПРОЕКТ НОВОЙ АРХИТЕКТУРЫ

### Задание 2.1: Предложить структуру `core/tasks/`

**Рекомендуемая структура:**

```
core/tasks/
├── __init__.py              # Экспорты всех задач
├── dispatcher.py            # Диспетчер задач (НОВЫЙ)
├── monitor.py               # Мониторинг источников (перенос из services)
├── scheduler.py             # Планировщик (существующий, доработать)
├── cleanup.py               # Задачи очистки (перенос из services)
└── worker.py                # Воркер для Celery/RQ (будущее, v7.0)
```

**Описание модулей:**

#### `dispatcher.py` (НОВЫЙ)
```python
"""
Диспетчер фоновых задач.
Запускает все фоновые процессы из одной точки.
"""
import asyncio
import logging
from typing import List, Callable

logger = logging.getLogger(__name__)

class TaskDispatcher:
    """Диспетчер фоновых задач."""
    
    def __init__(self, bot, session_factory):
        self.bot = bot
        self.session_factory = session_factory
        self.tasks: List[asyncio.Task] = []
    
    async def start_all(self):
        """Запустить все фоновые задачи."""
        logger.info("🚀 Запуск фоновых задач...")
        
        # Задача 1: Мониторинг источников
        self.tasks.append(
            asyncio.create_task(self.run_monitoring())
        )
        
        # Задача 2: Очистка устаревших данных
        self.tasks.append(
            asyncio.create_task(self.run_cleanup())
        )
        
        # Задача 3: Проверка статуса групп
        self.tasks.append(
            asyncio.create_task(self.run_group_checker())
        )
        
        logger.info(f"✅ Запущено задач: {len(self.tasks)}")
        
        # Ждём завершения всех задач (никогда не завершатся)
        await asyncio.gather(*self.tasks, return_exceptions=True)
    
    async def stop_all(self):
        """Остановить все фоновые задачи."""
        logger.info("⏹️ Остановка фоновых задач...")
        
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("✅ Все задачи остановлены")
    
    async def run_monitoring(self):
        """Запустить мониторинг источников."""
        from core.services.monitoring.base import MonitoringService
        
        monitoring = MonitoringService(self.bot)
        await monitoring.start(interval_minutes=5)
    
    async def run_cleanup(self):
        """Запустить очистку устаревших данных."""
        # Реализация будет в cleanup.py
        pass
    
    async def run_group_checker(self):
        """Запустить проверку статуса групп."""
        from core.services.monitoring.group_checker import GroupChecker
        
        checker = GroupChecker(self.bot, None)
        await checker.schedule_groups_check()
```

#### `monitor.py` (ПЕРЕНОС ИЗ services/monitoring/base.py)
```python
"""
Задача мониторинга источников.
Оркестрация: КОГДА и КАК запускать проверку.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.services.monitoring.telegram_monitor import TelegramMonitor
from core.services.monitoring.youtube_monitor import YouTubeMonitor

logger = logging.getLogger(__name__)

class MonitoringTask:
    """Задача мониторинга источников."""
    
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.telegram_monitor = TelegramMonitor(bot, self)
        self.youtube_monitor = YouTubeMonitor(bot, self)
    
    async def run(self, interval_minutes: int = 5):
        """Основной цикл мониторинга."""
        self.is_running = True
        logger.info(f"🔍 Запуск мониторинга (интервал: {interval_minutes} мин)")
        
        while self.is_running:
            try:
                async with async_session() as session:
                    await self._check_all_sources(session)
                    await session.commit()
            except Exception as e:
                logger.error(f"❌ Ошибка в мониторинге: {e}", exc_info=True)
                await asyncio.sleep(60)
            
            await self._smart_sleep(interval_minutes)
    
    async def stop(self):
        """Остановить мониторинг."""
        self.is_running = False
        logger.info("⏹️ Мониторинг остановлен")
    
    async def _check_all_sources(self, session: AsyncSession):
        """Проверить все источники."""
        # Логика из base.py, но без управления жизненным циклом
        pass
    
    async def _smart_sleep(self, base_interval_minutes: int):
        """Умное ожидание с учётом часов пик."""
        # Логика из base.py
        pass
```

#### `cleanup.py` (НОВЫЙ, перенос из services/cleanup_service.py)
```python
"""
Задачи очистки устаревших данных.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

class CleanupTask:
    """Задача очистки."""
    
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
    
    async def run(self, interval_hours: int = 6):
        """Основной цикл очистки."""
        self.is_running = True
        logger.info(f"🧹 Запуск очистки (интервал: {interval_hours} ч)")
        
        while self.is_running:
            try:
                async with async_session() as session:
                    await self._run_cleanup(session)
                    await session.commit()
            except Exception as e:
                logger.error(f"❌ Ошибка в очистке: {e}", exc_info=True)
            
            await asyncio.sleep(interval_hours * 3600)
    
    async def stop(self):
        """Остановить очистку."""
        self.is_running = False
    
    async def _run_cleanup(self, session: AsyncSession):
        """Выполнить очистку."""
        # Перенос логики из services/cleanup_service.py
        pass
```

---

### Задание 2.2: Обновить `bot/main.py`

**Текущая структура (предположительно):**
```python
# bot/main.py
async def main():
    bot = Bot(settings.BOT_TOKEN)
    
    # Регистрация хендлеров
    dp.include_router(...)
    
    # Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

**Требуемая структура:**
```python
# bot/main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from core.database import async_session
from core.tasks.dispatcher import TaskDispatcher

logger = logging.getLogger(__name__)

async def main():
    """Точка входа бота."""
    logger.info("🚀 Запуск MyAggryBot...")
    
    # Инициализация бота и диспетчера
    bot = Bot(settings.BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация хендлеров
    from bot.handlers import admin, common, settings_handler, sources
    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(settings_handler.router)
    dp.include_router(sources.router)
    
    # Инициализация диспетчера фоновых задач
    task_dispatcher = TaskDispatcher(bot, async_session)
    
    # Обработчик остановки (graceful shutdown)
    async def on_shutdown(dp):
        logger.info("🛑 Получен сигнал остановки")
        await task_dispatcher.stop_all()
        await bot.session.close()
    
    dp.shutdown.register(on_shutdown)
    
    # Запуск фоновых задач
    asyncio.create_task(task_dispatcher.start_all())
    logger.info("✅ Фоновые задачи запущены")
    
    # Запуск polling
    logger.info("📡 Запуск polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await task_dispatcher.stop_all()
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

---

### Задание 2.3: Создать `.env.example` с новыми переменными

**Добавить переменные для управления задачами и 3-х хостовой архитектуры:**

```bash
# .env.example

# ===== ENVIRONMENT =====
ENV=development  # development / production

# ===== DATABASE (Хост 1) =====
# Для development (локально)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=myaggrybot
DATABASE_USER=myaggrybot
DATABASE_PASSWORD=dev_password

# Для production (отдельный хост БД)
# DATABASE_HOST=192.168.1.10
# DATABASE_PORT=5432
# DATABASE_NAME=myaggrybot
# DATABASE_USER=myaggrybot
# DATABASE_PASSWORD=secure_password

# ===== REDIS (Хост 2) =====
# Для development (локально)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0

# Для production (отдельный хост Redis)
# REDIS_HOST=192.168.1.11
# REDIS_PORT=6379
# REDIS_URL=redis://192.168.1.11:6379/0

# ===== TASKS =====
# Режим запуска задач
TASKS_ENABLED=true                    # Включить фоновые задачи
TASKS_MODE=single                     # single / distributed (для Celery в будущем)

# Мониторинг
MONITORING_ENABLED=true
MONITORING_INTERVAL_MINUTES=5
SEMAPHORE_LIMIT=10                    # Макс. одновременных запросов (v6.1)

# YouTube
YOUTUBE_PARSING_INTERVAL=1800         # 30 минут (v6.1)

# Очистка
CLEANUP_ENABLED=true
CLEANUP_INTERVAL_HOURS=6

# Проверка групп
GROUP_CHECKER_ENABLED=true
GROUP_CHECKER_INTERVAL_HOURS=12

# ===== PRODUCTION VS DEVELOPMENT =====
# Для production (3 хоста)
# ENV=production
# TASKS_MODE=single
# SEMAPHORE_LIMIT=10                  # Полный лимит для одного воркера

# Для development (локальный запуск)
# ENV=development
# TASKS_MODE=single
# SEMAPHORE_LIMIT=10                  # Полный лимит для тестов
```

---

## 🧪 Часть 3: ТЕСТЫ ДЛЯ ПРОВЕРКИ

### Тест 3.1: Локальный запуск (development)

```bash
# 1. Запустить бота локально
python -m bot.main

# Ожидается:
# - Бот запускается без ошибок
# - В логах: "🚀 Запуск фоновых задач..."
# - В логах: "✅ Запущено задач: 3"
# - Мониторинг работает (проверка источников)
# - Очистка работает (раз в 6 часов)
# - Проверка групп работает (раз в 12 часов)
```

### Тест 3.2: Graceful Shutdown

```bash
# Нажать Ctrl+C

# Ожидается:
# - В логах: "🛑 Получен сигнал остановки"
# - В логах: "⏹️ Остановка фоновых задач..."
# - В логах: "✅ Все задачи остановлены"
# - Бот корректно закрывает соединение
```

### Тест 3.3: Конфигурация для 3-х хостов (production-like)

**Архитектура продакшена:**
```
Хост 1: PostgreSQL
  - Порт: 5432
  - IP: 192.168.1.10 (пример)

Хост 2: Redis
  - Порт: 6379
  - IP: 192.168.1.11 (пример)

Хост 3: Бот (приложение)
  - Python 3.12
  - Подключается к БД и Redis по сети
```

**Настройка `.env.production` на хосте бота:**
```bash
# Подключение к БД (отдельный хост)
DATABASE_HOST=192.168.1.10
DATABASE_PORT=5432
DATABASE_NAME=myaggrybot
DATABASE_USER=myaggrybot
DATABASE_PASSWORD=secure_password

# Подключение к Redis (отдельный хост)
REDIS_HOST=192.168.1.11
REDIS_PORT=6379
REDIS_URL=redis://192.168.1.11:6379/0

# Режим работы
ENV=production
TASKS_MODE=single
SEMAPHORE_LIMIT=10
```

**Запуск на хосте бота:**
```bash
# Через systemd (рекомендуется для продакшена)
sudo systemctl start myaggrybot

# Или напрямую
python -m bot.main

# Или через supervisor
supervisorctl start myaggrybot
```

**Опционально: Docker только для локальной разработки:**
```yaml
# docker-compose.dev.yml (ТОЛЬКО ДЛЯ DEV!)
version: '3.8'

services:
  bot:
    build: .
    env_file: .env.development
    volumes:
      - .:/app
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: myaggrybot
      POSTGRES_USER: myaggrybot
      POSTGRES_PASSWORD: dev_password
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

```bash
# Запустить локально (dev)
docker-compose -f docker-compose.dev.yml up

# Ожидается:
# - Все сервисы запускаются локально
# - Бот подключается к локальным БД и Redis
# - Фоновые задачи работают
```

### Тест 3.4: Существующие тесты проекта

```bash
# Запустить существующие тесты
pytest tests/ -v

# Ожидается:
# - Все тесты проходят
# - Нет регрессий
```

---

## 📝 Часть 4: ДОКУМЕНТАЦИЯ

### Задание 4.1: Обновить README.md

**Добавить раздел "Фоновые задачи":**

```markdown
## 🔄 Фоновые задачи

MyAggryBot использует следующие фоновые задачи:

### Мониторинг источников
- **Интервал:** 5 минут (Telegram), 30 минут (YouTube)
- **Описание:** Проверка новых постов в каналах и видео на YouTube
- **Настройка:** `MONITORING_INTERVAL_MINUTES`, `YOUTUBE_PARSING_INTERVAL`

### Очистка данных
- **Интервал:** 6 часов
- **Описание:** Удаление устаревших кэшей, закрытых тем, неактивных подписок
- **Настройка:** `CLEANUP_INTERVAL_HOURS`

### Проверка групп
- **Интервал:** 12 часов
- **Описание:** Проверка доступности групп, обновление статуса бота
- **Настройка:** `GROUP_CHECKER_INTERVAL_HOURS`

### Запуск задач

**Локально (development):**
```bash
python -m bot.main
# Все задачи запускаются автоматически в одном процессе
```

**Продакшен (3 хоста):**
```bash
# Настроить .env.production с IP хостов БД и Redis
sudo systemctl start myaggrybot
# Все задачи запускаются автоматически через systemd
```

### Архитектура продакшена

```
Хост 1: PostgreSQL ←→ Хост 3: Бот ←→ Хост 2: Redis
```

См. `docs/DEPLOYMENT_3HOSTS.md` для подробной инструкции.

### Переменные окружения

См. `.env.example` для полного списка настроек задач.
```

---

### Задание 4.2: Создать `docs/TASKS_ARCHITECTURE.md`

**Содержание:**
- Архитектура фоновых задач
- Диаграмма последовательности
- Описание каждого модуля
- Рекомендации по масштабированию
- **Инструкция по развёртыванию на 3-х хостах** (БД, Redis, Бот)
- Настройка systemd/supervisor для продакшена
- Сетевая конфигурация и firewall

---

### Задание 4.3: Создать `docs/DEPLOYMENT_3HOSTS.md`

**Содержание:**
- Схема архитектуры (3 хоста)
- Пошаговая настройка каждого хоста:
  - Хост 1: Установка и настройка PostgreSQL
  - Хост 2: Установка и настройка Redis
  - Хост 3: Установка Python, зависимостей, настройка бота
- Конфигурация сетевого взаимодействия
- Переменные окружения для каждого хоста
- Запуск через systemd (unit-файл)
- Мониторинг и логирование
- Резервное копирование БД

---

## ⚠️ Ограничения и требования

### НЕ делать:
- ❌ Не удалять существующую логику из `services/monitoring/base.py` до завершения рефакторинга
- ❌ Не менять API существующих сервисов (обратная совместимость)
- ❌ Не добавлять новые зависимости (Celery, RQ) — это будет в v7.0
- ❌ Не создавать разные файлы для dev/prod
- ❌ Жёсткая привязка к Docker (продакшен только на 3 хостах)

### Делать:
- ✅ Использовать переменные окружения для переключения режимов
- ✅ Сохранять обратную совместимость со старым кодом
- ✅ Добавить подробное логирование всех этапов
- ✅ Написать инструкцию по миграции для разработчиков
- ✅ Поддерживать запуск напрямую (python main.py) и через systemd

---

## 📊 Ожидаемый результат

| Компонент | До изменений | После изменений |
|-----------|--------------|-----------------|
| Точки входа | Разбросаны | Единая (`TaskDispatcher`) |
| `core/tasks/monitor.py` | Пустой | Рабочий код мониторинга |
| Запуск задач | Неясно | Явный в `bot/main.py` |
| Dev vs Prod | Потенциально разный | Одинаковый через ENV |
| Документация | Отсутствует | Полная в README + docs/ |
| Архитектура | Неясная | Чёткое разделение Tasks/Services |
| Поддержка Docker | Неясно | Опционально (только для dev) |
| Поддержка 3-х хостов | Нет | ✅ Полная поддержка |
| Масштабируемость | Ограничена | Готово к Celery (v7.0) |

---

## 🚀 План реализации (по шагам)

### Шаг 1: Аудит (30 минут)
- [ ] Найти все точки входа
- [ ] Проанализировать `core/tasks/`
- [ ] Найти все фоновые процессы
- [ ] Задокументировать находки

### Шаг 2: Проектирование (30 минут)
- [ ] Предложить структуру `core/tasks/`
- [ ] Написать код `dispatcher.py`
- [ ] Написать код `monitor.py`
- [ ] Написать код `cleanup.py`

### Шаг 3: Интеграция (1 час)
- [ ] Обновить `bot/main.py`
- [ ] Обновить `.env.example` (с разделением на dev/prod)
- [ ] Создать `.env.development` (шаблон для локальной разработки)
- [ ] Создать `.env.production` (шаблон для продакшена с 3 хостами)
- [ ] Протестировать локальный запуск
- [ ] Протестировать graceful shutdown
- [ ] Документировать настройку для 3-х хостов

### Шаг 4: Документация (45 минут)
- [ ] Обновить README.md
- [ ] Создать `docs/TASKS_ARCHITECTURE.md`
- [ ] Создать `docs/DEPLOYMENT_3HOSTS.md`
- [ ] Добавить комментарии в код

### Шаг 5: Тестирование (30 минут)
- [ ] Запустить существующие тесты
- [ ] Протестировать в Docker (опционально, только dev)
- [ ] Проверить логи

**Общее время:** ~3.5 часа

---

## 🔗 Связанные документы

- SCALABILITY_PLAN.md (общий план масштабирования)
- core/services/monitoring/base.py (текущая реализация мониторинга)
- core/tasks/monitor.py (пустой файл, требует заполнения)
- bot/main.py (точка входа бота)

---

## 💡 Примечания

### Почему это важно для масштабирования:

1. **Единая точка входа** упрощает отладку и мониторинг
2. **Разделение Tasks/Services** позволяет легко заменить оркестрацию (например, на Celery)
3. **Одинаковый код для dev/prod** уменьшает количество багов при деплое
4. **Переменные окружения** позволяют гибко настраивать без изменения кода
5. **Поддержка 3-х хостов** обеспечивает изоляцию ресурсов и безопасность

### Что будет дальше (v6.1):

После завершения этой задачи:
1. ✅ Промпт 1: Добавить Semaphore в `monitor.py`
2. ✅ Промпт 2: Оптимизировать SQL запросы
3. ✅ Промпт 3: Добавить кэширование в Redis
4. ✅ Промпт 4: Добавить метрики производительности

### Что будет в v7.0:

- Переход на Celery/RQ для распределённой обработки
- Несколько воркеров на разных серверах (горизонтальное масштабирование)
- Очередь задач в Redis
- Балансировка нагрузки
- Поддержка кластера БД (master/slave)

### Текущая целевая архитектура (v6.1):

```
┌─────────────────┐
│   Хост 1: БД    │
│   PostgreSQL    │
│   (отдельно)    │
└────────┬────────┘
         │
         │ сеть (5432)
         │
┌────────┴────────┐     ┌─────────────────┐
│   Хост 3: Бот   │────>│   Хост 2: Redis │
│   (приложение)  │     │   (кэш/очередь) │
│   Python 3.12   │<────│   (отдельно)    │
│   systemd       │     └─────────────────┘
└─────────────────┘
```

**Преимущества:**
- ✅ Изоляция ресурсов (БД не конкурирует с ботом за CPU/RAM)
- ✅ Независимое масштабирование (можно добавить RAM только БД)
- ✅ Безопасность (БД не доступна извне, только из сети бота)
- ✅ Простота резервного копирования (отдельный хост БД)

---

**Готово к реализации!** Начните с Шага 1 (Аудит) и предоставьте отчёт о найденных точках входа перед переходом к Шагу 2.

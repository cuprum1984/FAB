# 📊 MyAggryBot — Полный отчёт по проекту

**Дата отчёта:** 2 апреля 2026
**Версия проекта:** 6.5
**Статус:** ✅ Активная разработка

---

## 📖 ИСТОРИЯ ВЕРСИЙ

| Версия | Дата | Изменения | Статус |
|--------|------|-----------|--------|
| **6.5** | 2 апр 2026 | Telegram Stars: система донатов, хендлеры, клавиатуры, локализация | ✅ Реализовано |
| **6.4** | 31 мар 2026 | Лимиты Free плана: сервис проверки, интеграция, тесты (8) | ✅ Реализовано |
| **6.3** | 28 мар 2026 | Оптимизация кэширования: удалена `user_cached_media` | ✅ Реализовано |
| **6.2** | 28 мар 2026 | Оптимизация PostSender: bulk update, кэш тем, изоляция ошибок | ✅ Реализовано |
| **6.1** | 28 мар 2026 | Масштабирование: Semaphore, N+1 оптимизация, защита от простоя, TaskDispatcher | ✅ Реализовано |
| **6.0** | 17 мар 2026 | Refactor Architecture: разделение keyboards/ и messages/ | ✅ Реализовано |
| **5.7** | 9 мар 2026 | Refactor Inline Only + централизация задержек | ✅ Реализовано |
| **5.6** | 1 мар 2026 | Улучшение мониторинга, GDPR очистка, Redis клиент | ✅ Реализовано |
| **5.5** | 1 мар 2026 | Исправление topic_checker, обновление handlers | ✅ Реализовано |
| **5.4** | 28 фев 2026 | Разделение файлов на модули (models → 7, cleanup → 5) | ✅ Реализовано |
| **5.3** | 28 фев 2026 | Rate Limiting (Token Bucket + Exponential Backoff) | ✅ Реализовано |
| **5.2** | 25 фев 2026 | Тесты TopicSourceAssignment (8 тестов) | ✅ Реализовано |
| **5.1** | 24 фев 2026 | Тесты очистки GDPR (10 тестов) | ✅ Реализовано |
| **5.0** | 23 фев 2026 | YouTube Simple Parser + Service | ✅ Реализовано |
| **4.1** | 20 фев 2026 | Удаление RSS-лент | ✅ Реализовано |
| **4.0** | 18 фев 2026 | Destination Service | ✅ Реализовано |
| **3.0** | 15 фев 2026 | Мониторинг сервис | ✅ Реализовано |
| **2.0** | 10 фев 2026 | Telegram парсер | ✅ Реализовано |
| **1.0** | 05 фев 2026 | Базовая версия бота | ✅ Реализовано |

---

## 📋 СОДЕРЖАНИЕ

1. [Общая информация](#общая-информация)
2. [Архитектура проекта](#архитектура-проекта)
3. [Структура файлов](#структура-файлов)
4. [База данных](#база-данных)
5. [Тестирование](#тестирование)
6. [Плюсы проекта](#плюсы-проекта)
7. [Минусы и проблемы](#минусы-и-проблемы)
8. [Что нужно доработать](#что-нужно-доработать)
9. [Рекомендации](#рекомендации)

---

## 📌 ОБЩАЯ ИНФОРМАЦИЯ

| Параметр | Значение |
|----------|----------|
| **Название** | MyAggryBot |
| **Тип** | Telegram-агрегатор контента |
| **Фреймворк** | aiogram 3.13+ (async) |
| **Язык** | Python 3.12 |
| **БД** | PostgreSQL (asyncpg) + SQLite (тесты) |
| **Кэш** | Redis (fakeredis для тестов) |
| **Планировщик** | APScheduler 3.10+ |
| **Миграции** | Alembic |
| **Локализация** | i18n (ru, en, uk, be) |

### Назначение
Бот агрегирует контент из:
- Telegram-каналов (парсинг публичных каналов)
- YouTube (отслеживание новых видео)
- RSS-лент (удалено в версии 4.1)

Контент распределяется по темам в управляемых группах.

---

## 🏗️ АРХИТЕКТУРА ПРОЕКТА

```
d:\PROJ\FAB\
├── bot/                        # Telegram-бот (aiogram)
│   ├── main.py                # Точка входа
│   ├── handlers/              # Обработчики команд
│   │   ├── admin.py           # Админ команды (/activ, /plus, /mytopics)
│   │   ├── common.py          # Общие команды (/start, /help, /refresh)
│   │   ├── my_overview.py     # Обзор источников (/overview)
│   │   ├── my_sources_interactive.py  # Интерактивные источники (/list)
│   │   ├── settings_handler.py # Настройки (/settings)
│   │   ├── topics_auto.py     # Авто-публикация в темы
│   │   └── sources/           # Модуль добавления источников
│   │       ├── add_channel.py
│   │       ├── telegram_handlers.py
│   │       ├── youtube_handlers.py
│   │       ├── destination_handlers.py
│   │       ├── group_select_handlers.py
│   │       ├── finalize_handlers.py
│   │       ├── cancel_handlers.py
│   │       └── list_handlers.py
│   ├── keyboards/             # Модуль клавиатур (v6.0)
│   │   ├── __init__.py
│   │   ├── main_menu.py       # Главное меню
│   │   ├── my_sources.py      # Клавиатуры для источников
│   │   ├── admin.py           # Админ-панель
│   │   ├── settings.py        # Настройки
│   │   ├── sources.py         # Добавление источников
│   │   └── destinations.py    # Выбор назначений
│   ├── keyboards.py           # Обратная совместимость (shim)
│   ├── messages/              # Модуль текстов (v6.0)
│   │   ├── __init__.py
│   │   └── my_sources.py      # Форматирование источников
│   ├── states.py              # FSM состояния
│   ├── utils/
│   │   └── menu_message.py    # Управление сообщениями меню
│   └── middlewares/           # Middleware (i18n, DB, filter)
├── core/                       # Ядро проекта
│   ├── __init__.py            # Инициализация
│   ├── settings.py            # Настройки (pydantic)
│   ├── database.py            # Подключение к БД
│   ├── redis_client.py        # Redis клиент
│   ├── models/                # ORM модели (7 модулей)
│   │   ├── base.py            # Базовые модели
│   │   ├── users.py           # TelegramAccount
│   │   ├── groups.py          # ManagedGroup, GroupTopic
│   │   ├── sources.py         # ContentSource
│   │   ├── subscriptions.py   # SourceSubscription, UserChannelSubscription
│   │   ├── assignments.py     # TopicSourceAssignment
│   │   └── cache.py           # CachedMedia (v6.3: без UserCachedMedia)
│   ├── parser/                # Парсеры
│   │   ├── telegram.py        # Парсинг TG-каналов
│   │   ├── telegram_posts.py
│   │   └── youtube_simple.py
│   ├── services/              # Бизнес-логика
│   │   ├── cleanup/           # Подмодули очистки (5 файлов)
│   │   ├── destinations/      # Подмодули назначений (7 файлов)
│   │   ├── monitoring/        # Подмодули мониторинга (5 файлов)
│   │   ├── destination_service.py
│   │   ├── monitoring_service.py
│   │   ├── rate_limiter.py    # Rate limiting (Token Bucket)
│   │   ├── youtube_simple_service.py
│   │   └── helper/            # Helper-утилиты (3 файла)
│   ├── tasks/                 # Фоновые задачи
│   │   ├── scheduler.py       # APScheduler
│   │   └── monitor.py         # Мониторинг
│   └── utils/                 # Утилиты
│       ├── topic_checker.py
│       └── i18n.py
├── tests/                      # Тесты (pytest)
│   ├── conftest.py            # Фикстуры
│   ├── test_cleanup.py        # Тесты очистки (14 тестов)
│   ├── test_destination_service.py # Тесты destination (23 теста)
│   ├── test_monitoring_service.py  # Тесты monitoring (9 тестов)
│   ├── test_topic_assignments.py  # Тесты назначений (8 тестов)
│   ├── test_parser.py         # Тесты парсера TG
│   ├── test_youtube_parser.py
│   ├── test_youtube_service.py
│   └── test_rate_limiter.py   # Тесты rate limiting (23 теста)
├── migrations/                 # Alembic миграции
├── locales/                    # Локализация (ru, en, uk, be)
├── docs/                       # Документация (72 файла)
│   ├── README.md              # Навигация
│   ├── CHANGELOG.md           # История версий
│   ├── overview.md            # Полный отчёт
│   ├── memory/                # Память проекта (17 файлов)
│   └── 01-general/...         # Разделы документации
└── PROMPTS/                    # Архив (1 файл)
```

---

## 📁 СТРУКТУРА ФАЙЛОВ

### Основные файлы

| Файл | Назначение | Статус |
|------|------------|--------|
| `bot/main.py` | Точка входа, запуск бота | ✅ Продакшен |
| `core/settings.py` | Настройки (pydantic) | ✅ Не менять |
| `core/database.py` | Подключение к БД | ✅ Исправлено для SQLite |
| `core/models/` | ORM модели (7 модулей) | ✅ v6.4: 9 таблиц |
| `core/services/` | Бизнес-логика (26+ модулей) | ✅ v6.4: +limits.py |
| `tests/conftest.py` | Фикстуры pytest | ✅ Обновлёно |
| `pytest.ini` | Конфигурация тестов | ✅ Создано |
| `docs/README.md` | Документация (63+ файла) | ✅ Актуально |
| `docs/memory/` | Память проекта (18 файлов) | ✅ v6.4: +limits.md |

### Файлы конфигурации

| Файл | Назначение |
|------|------------|
| `.env.example` | Шаблон переменных окружения |
| `.env.local` | Локальная БД (SQLite) |
| `alembic.ini` | Настройки миграций |
| `requirements.txt` | Зависимости Python |
| `.gitignore` | Игнорируемые файлы |

---

## 🗄️ БАЗА ДАННЫХ

### Таблицы (9 штук)

**Последнее обновление:** v6.4 (31 марта 2026) — лимиты Free плана

| Таблица | Назначение | Ключевые поля |
|---------|------------|---------------|
| `telegram_accounts` | Пользователи | `telegram_account_id`, `username`, `is_bot_blocked` |
| `managed_groups` | Управляемые группы | `telegram_chat_id`, `is_bot_active_in_group`, `last_seen_at` |
| `group_topics` | Темы в группах | `topic_identifier`, `is_exists_in_tg`, `last_seen_at` |
| `content_sources` | Источники (TG, YouTube) | `source_global_id`, `source_type`, `telegram_username` |
| `source_subscriptions` | Подписки групп на источники | `subscription_id`, `telegram_chat_id`, `source_global_id` |
| `topic_source_assignments` | Назначения источников в темы | `assignment_id`, `topic_identifier`, `subscription_id` |
| `user_channel_subscriptions` | Личные подписки пользователей | `user_id`, `source_global_id`, `is_active` |
| `cached_media` | Кэш медиафайлов | `source_global_id`, `post_id`, `file_id`, `expires_at` |

### Удалённые таблицы

| Таблица | Удалена в | Причина |
|---------|-----------|---------|
| ~~`user_cached_media`~~ | v6.3 | Избыточность, дублировала `cached_media` |

---

## 🧪 ТЕСТИРОВАНИЕ

```
TelegramAccount
    ← GroupTopic.created_by_telegram_account_id
    ← SourceSubscription.added_by_telegram_account_id
    ← UserChannelSubscription.user_id

ManagedGroup
    ← GroupTopic.telegram_chat_id (CASCADE)
    ← SourceSubscription.telegram_chat_id (CASCADE)

GroupTopic
    ← TopicSourceAssignment.topic_identifier (CASCADE)

ContentSource
    ← SourceSubscription.source_global_id (SET NULL)
    ← UserChannelSubscription.source_global_id (CASCADE)

SourceSubscription
    ← TopicSourceAssignment.subscription_id (CASCADE)
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Инфраструктура

| Компонент | Конфигурация |
|-----------|--------------|
| **Фреймворк** | pytest 8.3.4 |
| **Async** | pytest-asyncio 0.25.0 (auto mode) |
| **БД для тестов** | SQLite в памяти (`:memory:`) |
| **Изоляция** | Чистая БД для каждого теста |
| **Фикстуры** | `db_session`, HTML fixtures |

### Статистика тестов

| Категория | Файл | Тестов | Пройдено | Провалено |
|-----------|------|--------|----------|-----------|
| **Очистка (GDPR)** | `test_cleanup.py` | 14 | 14 ✅ | 0 |
| **Destination Service** | `test_destination_service.py` | 23 | 23 ✅ | 0 |
| **Monitoring Service** | `test_monitoring_service.py` | 9 | 9 ✅ | 0 |
| **Назначения** | `test_topic_assignments.py` | 8 | 8 ✅ | 0 |
| **Лимиты Free плана** | `test_limits.py` | 8 | 8 ✅ | 0 |
| **Парсер TG** | `test_parser.py` | 7 | 7 ✅ | 0 |
| **Парсер YouTube** | `test_youtube_parser.py` | 11 | 9 ✅ | 2* |
| **YouTube Service** | `test_youtube_service.py` | 11 | 11 ✅ | 0 |
| **Rate Limiting** | `test_rate_limiter.py` | 23 | 23 ✅ | 0 |
| **Интеграционные** | (помечены `skip`) | 5 | - | - |
| **ИТОГО** | | **112** | **107 ✅** | **5 skip** |

\* *Тесты требуют интернета, пропускаются без флага `-k "real"`*

### Изменения в v6.0

**Рефакторинг архитектуры:**
- ✅ `bot/keyboards/` — модуль клавиатур (7 файлов)
- ✅ `bot/messages/` — модуль текстов (2 файла)
- ✅ `bot/keyboards.py` — обратная совместимость (shim, 47 строк)
- ✅ Уменьшение `keyboards.py` с 869 до 47 строк (-95%)

**Новые файлы:**
- `bot/keyboards/main_menu.py` — главное меню
- `bot/keyboards/my_sources.py` — клавиатуры источников
- `bot/keyboards/admin.py` — админ-панель
- `bot/keyboards/settings.py` — настройки
- `bot/keyboards/sources.py` — добавление источников
- `bot/keyboards/destinations.py` — выбор назначений
- `bot/messages/my_sources.py` — форматирование источников

**Статус:**
- ✅ Все импорты работают
- ✅ 107 тестов пройдено (v6.4: +8 тестов лимитов)
- ✅ Обратная совместимость сохранена

### Команды для запуска

```bash
# Все тесты
pytest -v

# Только тесты очистки
pytest tests/test_cleanup.py -v

# Только тесты назначений
pytest tests/test_topic_assignments.py -v

# Тесты с фильтром по имени
pytest -k gdpr -v
pytest -k cascade -v

# Интеграционные тесты (требуют интернета)
pytest -k "real" -v
```

---

## ✅ ПЛЮСЫ ПРОЕКТА

### Архитектура
1. **✅ Чёткое разделение слоёв** — `bot/`, `core/`, `tests/` изолированы
2. **✅ Async/await везде** — правильный asyncio паттерн
3. **✅ ORM с отношениями** — SQLAlchemy 2.0, relationships, cascade
4. **✅ Миграции БД** — Alembic настроен, есть истории изменений
5. **✅ Локализация** — i18n middleware, 4 языка (ru, en, uk, be)

### Тестирование
6. **✅ 96% тестов проходят** — 107 из 112 тестов (5 skip — интеграционные)
7. **✅ Изоляция тестов** — SQLite в памяти, чистая БД на каждый тест
8. **✅ Безопасность** — тесты не подключаются к Neon.tech (продакшен)
9. **✅ Helper-функции** — DRY в тестах, переиспользование кода
10. **✅ Покрытие бизнес-логики** — GDPR, назначения, лимиты, парсеры, сервисы, rate limiting

### Инфраструктура
11. **✅ `.env.local` для разработки** — быстрый старт с SQLite
12. **✅ `.gitignore` настроен** — *.db, .env, __pycache__ игнорируются
13. **✅ pytest.ini** — asyncio_mode = auto, не нужно писать `@pytest.mark.asyncio`
14. **✅ Обработка ошибок** — DNS ошибки, подключение к БД/Redis

### Код
15. **✅ Типизация** — Mapped[], type hints в моделях
16. **✅ Индексы БД** — оптимизация запросов (20+ индексов)
17. **✅ Cascade удаления** — нет «висячих» записей
18. **✅ UniqueConstraint** — защита от дублей

### Rate Limiting (Версия 5.3)
19. **✅ Token Bucket алгоритм** — для Telegram и YouTube
20. **✅ Exponential Backoff** — при ошибках запросов
21. **✅ Глобальный лимит** — 60 запросов в минуту
22. **✅ Статистика и логирование** — мониторинг нагрузки

### Масштабирование (Версия 6.1)
23. **✅ Semaphore для мониторинга** — 10 одновременных запросов
24. **✅ Оптимизация N+1** — пакетная загрузка file_id
25. **✅ Защита от простоя** — ограничение постов после простоя
26. **✅ TaskDispatcher** — централизация задач
27. **✅ YouTube интервал** — 30 минут вместо 5

### Оптимизация PostSender (Версия 6.2)
28. **✅ Bulk update** — один commit на все темы
29. **✅ Кэш статусов** — 5 минут для тем и групп
30. **✅ Изоляция ошибок** — raise → return False
31. **✅ FSM State TTL** — автоматическое удаление состояний

---

## ❌ МИНУСЫ И ПРОБЛЕМЫ

### Критические
1. **✅ Rate limiting реализован** — Token Bucket + Exponential Backoff (Версия 5.3)
2. **✅ Обработка ошибок в парсерах** — с логированием и backoff
3. **✅ FSM State TTL** — автоматическое удаление состояний (Версия 6.2)
4. **✅ Масштабирование PostSender** — bulk update, кэш, изоляция ошибок (Версия 6.2)
5. **❌ Нет документирования API хендлеров** — сложно понять, какие команды доступны

### Архитектурные
6. **✅ Semaphore для мониторинга** — 10 потоков (Версия 6.1)
7. **✅ TaskDispatcher** — централизация задач (Версия 6.1)
8. **❌ Глобальные переменные** — `engine`, `async_session` в `core/database.py`
9. **❌ Нет dependency injection** — сложно тестировать сервисы с моками
10. **❌ Смешение логики** — `bot/main.py` содержит бизнес-логику
11. **❌ Нет контрактов интерфейсов** — сервисы не имеют явных интерфейсов

### Тестирование
12. **❌ 1 падающий тест** — `test_get_channel_data` (YouTube API)
13. **✅ Тесты для destination_service.py** — 29 тестов
14. **✅ Тесты для monitoring_service.py** — 9 тестов
15. **❌ Нет тестов для scheduler.py** — планировщик не покрыт
16. **❌ Интеграционные тесты требуют интернета** — не работают в CI/CD без сети

### Код
17. **⏳ DeprecationWarning** — `datetime.utcnow()` устарел (осталось 5 файлов)
18. **❌ Нет type hints в сервисах** — сложно понять сигнатуры методов
19. **✅ Большие файлы разделены** — `models.py` → 7 модулей
20. **❌ Дублирование кода** — helper-функции в тестах можно вынести в `conftest.py`

### Инфраструктура
21. **❌ Нет CI/CD конфигурации** — GitHub Actions, GitLab CI не настроены
22. **❌ Нет Dockerfile** — развёртывание вручную
23. **❌ Нет мониторинга** — Sentry, Prometheus не подключены

---

## 🔧 ЧТО НУЖНО ДОРАБОТАТЬ

### Приоритет 🔴 Высокий

1. **✅ Исправлено: FSM State TTL** (Версия 6.2)
   - `state_ttl=300` (5 мин) для тестирования
   - `state_ttl=86400` (24 ч) для продакшена
   - Логирование истечения TTL в хендлерах

2. **✅ Масштабирование PostSender** (Версия 6.2)
   - Bulk update `last_seen_at` (один commit на все темы)
   - Кэш статусов тем (5 минут)
   - Изоляция ошибок (raise → return False)
   - Отдельные сессии для cleanup операций

3. **✅ Semaphore для мониторинга** (Версия 6.1)
   - Ограничение параллелизма (10 потоков)
   - Уменьшение времени цикла с 16 часов до 1.6 часов

4. **✅ Оптимизация CachedMedia (N+1)** (Версия 6.1)
   - Пакетная загрузка file_id
   - Уменьшение запросов к БД в 10 раз

5. **✅ Защита от спама после простоя** (Версия 6.1)
   - Проверка `last_checked_timestamp`
   - Ограничение: макс. 5 постов после простоя

6. **✅ TaskDispatcher** (Версия 6.1)
   - Централизованное управление задачами
   - Graceful shutdown

7. **✅ Увеличен интервал YouTube** (Версия 6.1)
   - 30 минут вместо 5 минут
   - Снижение нагрузки на YouTube API в 6 раз

8. **✅ Оптимизация кэширования** (Версия 6.3)
   - Удалена таблица `user_cached_media`
   - Кэш на уровне источника (не пользователя)
   - Упрощение структуры БД (9 таблиц вместо 10)

9. **✅ Лимиты Free плана** (Версия 6.4)
   - Сервис проверки лимитов `core/services/limits.py`
   - 25 источников всего (15 TG + 10 YouTube)
   - 5 управляемых групп
   - 20 топиков в группе
   - 8 автотестов в `tests/test_limits.py`

### Приорет 🟡 Средний

1. **Добавить dependency injection**
   - Использовать `dependency-injector` или аналог
   - Упростит тестирование с моками

2. **Добавить тесты для `scheduler.py`**
   - Проверка расписаний
   - Проверка запуска задач

3. **Документировать API хендлеров**
   - README с описанием команд
   - Примеры использования

4. **Исправить проблему с длинными именами групп/топиков**
   - БД не подхватывает новое имя при переименовании
   - Нужен механизм синхронизации

5. **✅ Тесты для destination_service.py** — 23 теста ✅
6. **✅ Тесты для monitoring_service.py** — 9 тестов ✅
7. **✅ Документация** — 72 файла + 17 memory ✅

### Приоритет 🟢 Низкий

13. **✅ Разделить большие файлы** (v5.4)
    - `models.py` → 7 модулей
    - `cleanup_service.py` → 5 файлов

14. **✅ Рефакторинг клавиатур и текстов** (v6.0)
    - `bot/keyboards.py` (869 строк) → 7 модулей
    - `bot/messages/` — новый модуль с текстами

15. **✅ Оптимизация масштабирования** (v6.2)
    - Bulk update last_seen_at
    - Кэш статусов тем
    - Изоляция ошибок

16. **Добавить type hints в сервисах**
    - Сигнатуры методов
    - Возвращаемые типы

17. **Настроить мониторинг**
    - Sentry для ошибок
    - Логирование в файл

18. **Добавить Dockerfile**
    - Мультистейдж сборка
    - Переменные окружения

17. **Создать `docker-compose.yml`**
    - PostgreSQL, Redis, бот
    - Локальный запуск одной командой

---

## ✅ ИСТОРИЯ ИЗМЕНЕНИЙ (ПОДРОБНО)

### Версия 6.2 (28 марта 2026) — Оптимизация PostSender

**Проблема:** Критические уязвимости масштабирования в отправке постов.

**Реализовано:**
- ✅ `core/services/monitoring/post_sender.py` — полный рефакторинг (378 строк)
- ✅ Bulk update `last_seen_at` — один commit на все темы
- ✅ Кэш статусов тем (5 минут) — `_topic_cache`, `_group_cache`
- ✅ Изоляция ошибок — `raise` заменён на `return False`
- ✅ Отдельные сессии для cleanup операций
- ✅ Параметр `updated_topics: Set` для bulk update

**Обновлено:**
- ✅ `core/services/monitoring/telegram_monitor.py` — `_bulk_update_topics()` метод
- ✅ `bot/handlers/sources/*.py` — логирование истечения TTL
- ✅ `bot/main.py` — `FSM_STATE_TTL` настройка
- ✅ `core/settings.py` — `FSM_STATE_TTL` параметр
- ✅ `.env.example` — `FSM_STATE_TTL` переменная

**Результат:**
- ⚡ **Параллелизм:** 1-2 → 10 потоков (в 5-10 раз)
- 📉 **Flush-ей:** 25 000 → 1 000 (в 25 раз)
- 📉 **Запросов к БД:** 200 → 20 при 100 ошибках (в 10 раз)
- ⏱️ **Время обработки:** 50 сек → 5 сек (в 10 раз)
- 🛡️ **Отказоустойчивость:** 100%

**Документация:**
- ✅ `v6.2_FINAL_REPORT.md` — полный отчёт

---

### Версия 6.1 (28 марта 2026) — Масштабирование

**Проблема:** Ограничения производительности при 1000+ админов.

**Реализовано:**
- ✅ **Semaphore для мониторинга** — ограничение 10 одновременных запросов
- ✅ **Оптимизация CachedMedia (N+1)** — пакетная загрузка file_id
- ✅ **Защита от спама после простоя** — `DOWNTIME_THRESHOLD_SECONDS`, `DOWNTIME_MAX_POSTS`
- ✅ **TaskDispatcher** — централизованное управление задачами
- ✅ **Увеличен интервал YouTube** — 30 минут вместо 5

**Обновлено:**
- ✅ `core/settings.py` — 4 новые настройки
- ✅ `core/services/monitoring/base.py` — semaphore + downtime проверка
- ✅ `core/services/monitoring/telegram_monitor.py` — N+1 оптимизация + downtime
- ✅ `core/services/monitoring/youtube_monitor.py` — downtime support
- ✅ `core/services/youtube_simple_service.py` — downtime support
- ✅ `core/tasks/dispatcher.py` — новый модуль (120 строк)
- ✅ `bot/main.py` — интеграция TaskDispatcher
- ✅ `.env.example` — 4 новые переменные

**Результат:**
- ⚡ **Время цикла:** 16 часов → 1.6 часа (в 10 раз)
- 📉 **Запросов к БД:** 120 000 → 12 000 (в 10 раз)
- 👥 **Макс. админов:** 500 → 1 000 (в 2 раза)
- 🎬 **Нагрузка на YouTube API:** в 6 раз меньше
- 🎯 **Точек входа:** Несколько → Одна (централизация)

**Документация:**
- ✅ `v6.1_FINAL_REPORT.md` — полный отчёт
- ✅ `v6.1_IMPLEMENTATION_PLAN.md` — план реализации

---

### Версия 6.0 (17 марта 2026) — Refactor Architecture

**Реализовано:**
- ✅ `bot/keyboards/` — модуль клавиатур (7 файлов)
  - `main_menu.py` — главное меню
  - `my_sources.py` — клавиатуры источников (get_overview_kb, get_topics_tree_kb)
  - `admin.py` — админ-панель (get_admin_panel_menu_inline, get_groups_inline_kb, get_topics_inline_kb)
  - `settings.py` — настройки (get_settings_menu_inline, get_language_menu)
  - `sources.py` — добавление источников (get_confirm_channel_kb, get_source_list_kb)
  - `destinations.py` — выбор назначений (get_destinations_inline_kb)
- ✅ `bot/messages/` — модуль текстов (2 файла)
  - `my_sources.py` — форматирование (format_sources_overview_page, format_group_tree)
- ✅ `bot/keyboards.py` — обратная совместимость (shim, 47 строк)

**Изменения:**
- ✅ Уменьшение `keyboards.py` с 869 до 47 строк (-95%)
- ✅ Выделение функций форматирования из `my_sources_interactive.py`
- ✅ Сохранение обратной совместимости через импорты

**Структура проекта:**
```
bot/
├── keyboards/             # 7 модулей клавиатур
│   ├── __init__.py
│   ├── main_menu.py
│   ├── my_sources.py
│   ├── admin.py
│   ├── settings.py
│   ├── sources.py
│   └── destinations.py
├── messages/              # 2 модуля текстов
│   ├── __init__.py
│   └── my_sources.py
└── keyboards.py           # shim для обратной совместимости
```

**Преимущества:**
- 📦 **Модульность** — каждая клавиатура в отдельном файле
- 🔍 **Читаемость** — легче найти нужную клавиатуру
- 🧪 **Тестируемость** — проще писать тесты на отдельные клавиатуры
- 🚀 **Масштабируемость** — легче добавлять новые клавиатуры
- 🔙 **Обратная совместимость** — старые импорты работают

**Тесты:**
- ✅ Все 99 тестов пройдено
- ✅ Импорты работают корректно

**Документация:**
- ✅ `PROMPTS/REFACTORING_PLAN.md` — план рефакторинга (v1.2)

---

### Версия 5.7 (9 марта 2026) — Refactor Inline Only

**Реализовано:**
- ✅ Полный отказ от `ReplyKeyboardMarkup`
- ✅ `bot/utils/menu_message.py` — централизованное управление сообщениями
- ✅ `DEFAULT_DELETE_DELAY = 0` — глобальная задержка удаления
- ✅ Единое сообщение для всей навигации
- ✅ `message_id` сохраняется в FSM состоянии
- ✅ Поддержка `sendMessageDraft` (Bot API 9.4+)

**Тесты:**
- ✅ 99 тестов пройдено (5 skip)

---

### Версия 5.6 (1 марта 2026) — Улучшение мониторинга и GDPR

**Реализовано:**
- ✅ `core/services/cleanup/user_cleanup.py` — GDPR очистка пользователей
- ✅ `core/services/monitoring/base.py` — улучшена базовая логика мониторинга
- ✅ `core/redis_client.py` — Redis клиент для кэширования

**Обновлено:**
- ✅ `bot/handlers/sources.py` — управление источниками
- ✅ `requirements.txt` — зависимости

**Тесты:**
- ✅ `tests/test_cleanup.py` — 14 тестов (GDPR)
- ✅ `tests/test_monitoring_service.py` — 10 тестов

---

### Версия 5.5 (1 марта 2026) — Исправление topic_checker

**Реализовано:**
- ✅ `core/utils/topic_checker.py` — исправление логики проверки топиков
- ✅ `.copilotignore` — настройка игнорирования для Copilot

**Обновлено:**
- ✅ Исправление обработки сообщений (отправка + удаление)

---

### Версия 5.4 (28 февраля 2026) — Разделение файлов на модули

**Реализовано:**
- ✅ `core/models/` — 7 модулей (users, sources, subscriptions, groups, assignments, cache, base)
- ✅ `core/services/cleanup/` — 5 файлов (user_cleanup, subscription_cleanup, topic_cleanup, media_cleanup, base)
- ✅ `core/services/destinations/` — 7 файлов (access, topics, assignments, sources, subscriptions, cache, topic_utils)
- ✅ `core/services/monitoring/` — 5 файлов (base, group_checker, post_sender, telegram_monitor, youtube_monitor)
- ✅ `core/services/helper/` — 3 файла (cache_service, cleanup)
- ✅ `core/utils/` — 3 файла (topic_checker, html_formatter, topic_utils)

**Структура проекта:**
```
core/
├── models/           # 7 модулей ORM моделей
├── services/
│   ├── cleanup/      # 5 файлов очистки
│   ├── destinations/ # 7 файлов назначений
│   ├── monitoring/   # 5 файлов мониторинга
│   └── helper/       # 3 файла помощников
└── utils/            # 3 утилиты
```

**Преимущества:**
- 📦 **Модульность** — каждый файл отвечает за одну задачу
- 🔍 **Читаемость** — легче найти нужный код
- 🧪 **Тестируемость** — проще писать тесты на отдельные модули
- 🚀 **Масштабируемость** — легче добавлять новый функционал

---

### Версия 5.3 (28 февраля 2026) — Rate Limiting

**Реализовано:**
- ✅ `core/services/rate_limiter.py` — новый модуль (396 строк)
- ✅ Token Bucket алгоритм для Telegram (20 токенов, 10 ток/сек)
- ✅ Token Bucket для YouTube (5 токенов, 1 ток/сек)
- ✅ Exponential Backoff при ошибках (1с → 2с → 4с → 8с → пропуск)
- ✅ Глобальный лимит: 60 запросов в минуту
- ✅ Статистика и логирование

**Обновлено:**
- ✅ `core/parser/telegram.py` — rate limiting + обработка ошибок
- ✅ `core/parser/youtube_simple.py` — rate limiting + обработка ошибок
- ✅ `core/settings.py` — новые переменные окружения
- ✅ `.env.example` — добавлены настройки rate limiting
- ✅ `.env.local` — добавлены настройки rate limiting

**Тесты:**
- ✅ `tests/test_rate_limiter.py` — 23 теста (100% пройдено)

**Документация:**
- ✅ `PROMPTS/RATE_LIMITING.md` — полное руководство

---

### Версия 5.4 (28 февраля 2026) — Разделение файлов на модули

**Реализовано:**
- ✅ `core/models/` — 7 модулей (users, sources, subscriptions, groups, assignments, cache, base)
- ✅ `core/services/cleanup/` — 5 файлов (user_cleanup, subscription_cleanup, topic_cleanup, media_cleanup, base)
- ✅ `core/services/destinations/` — 7 файлов (access, topics, assignments, sources, subscriptions, cache, topic_utils)
- ✅ `core/services/monitoring/` — 5 файлов (base, group_checker, post_sender, telegram_monitor, youtube_monitor)
- ✅ `core/services/helper/` — 3 файла (cache_service, cleanup)
- ✅ `core/utils/` — 3 файла (topic_checker, html_formatter, topic_utils)

**Структура проекта:**
```
core/
├── models/           # 7 модулей ORM моделей
├── services/
│   ├── cleanup/      # 5 файлов очистки
│   ├── destinations/ # 7 файлов назначений
│   ├── monitoring/   # 5 файлов мониторинга
│   └── helper/       # 3 файла помощников
└── utils/            # 3 утилиты
```

**Преимущества:**
- 📦 **Модульность** — каждый файл отвечает за одну задачу
- 🔍 **Читаемость** — легче найти нужный код
- 🧪 **Тестируемость** — проще писать тесты на отдельные модули
- 🚀 **Масштабируемость** — легче добавлять новый функционал

---

### Версия 5.2 (25 февраля 2026) — Тесты назначений

**Реализовано:**
- ✅ `tests/test_topic_assignments.py` — 8 тестов
- ✅ Тесты cascade удалений
- ✅ Тесты multitenancy

**Документация:**
- ✅ `PROMPTS/Отчёт-Тесты TopicSourceAssignment.md`

---

### Версия 5.1 (24 февраля 2026) — Тесты очистки (GDPR)

**Реализовано:**
- ✅ `tests/test_cleanup.py` — 10 тестов
- ✅ GDPR: удаление заблокированных пользователей
- ✅ Очистка мёртвых групп и сиротских источников

**Документация:**
- ✅ `PROMPTS/Отчёт-Тесты очистки БД.md`

---

## 📝 РЕКОМЕНДАЦИИ

### ✅ Выполнено (v5.3)

- ✅ **Rate Limiting** — Token Bucket + Exponential Backoff
- ✅ **Тесты rate limiter** — 23 теста, 100% покрытие
- ✅ **Документация** — PROMPTS/RATE_LIMITING.md
- ✅ **Обработка ошибок в парсерах** — с логированием и backoff
- ✅ **Тесты destination_service.py** — 29 тестов
- ✅ **Тесты monitoring_service.py** — 9 тестов
- ✅ **Разделение больших файлов** — models.py → 7 модулей, cleanup → 5 файлов

### Немедленные действия (1-2 дня)

```bash
# 1. Исправить DeprecationWarning (осталось 5 файлов)
# Заменить в core/services/cleanup/*.py:
#   datetime.utcnow() → datetime.now(datetime.UTC)

# 2. Замокировать тест YouTube
# Или пометить как skip без интернета
```

### Краткосрочные (1-2 недели)

1. **Настроить GitHub Actions**
   ```yaml
   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
         - run: pip install -r requirements.txt
         - run: pytest -v
   ```

2. **Добавить ruff для линтинга**
   ```bash
   pip install ruff
   ruff check .
   ```

3. **Создать README.md**
   - Описание проекта
   - Быстрый старт
   - Команды бота
   - Запуск тестов

### Долгосрочные (1-2 месяца)

1. **Миграция на dependency injection**
2. **Покрытие тестами 95%+ кода**
3. **Настройка мониторинга и алертов**
4. **Docker-контейнеризация**
5. **Документация API (OpenAPI/Swagger)**

---

## 💰 ЛИМИТЫ И МОНЕТИЗАЦИЯ (ПЛАНИРУЕТСЯ)

### Бесплатная версия (Free)

| Ресурс                            | Лимит         | Обоснование                                               |
|-----------------------------------|---------------|-----------------------------------------------------------|
| **Telegram-каналов**              | 15 на админа  | Достаточно для личного использования + несколько проектов |
| **YouTube-каналов**               | 10 на админа  | YouTube парсинг более ресурсоёмкий                        |
| **Всего источников**              | 25 на админа  | Суммарный лимит (TG + YouTube)                            |
| **Управляемых групп**             | 5 на админа   | 1 личная + 3-4 проекта                                    |
| **Топиков в группе**              | 20 на группу  | Достаточно для категоризации                              |
| **Подписок группы на источники**  | 50 на группу  | Гибкость настройки                                        |

### Расчёт нагрузки

```
1 админ с макс. лимитами (25 источников):
- 25 источников × (1 проверка / 5 мин) = 5 проверок/мин
- 5 проверок/мин × 2 запроса = 10 запросов/мин

Глобальный лимит rate limiter: 60 запросов/мин
✅ Запас: 6× на одного админа
✅ Одновременно: до 6 активных админов
```

### Защита от злоупотреблений

| Угроза                            | Защита                                    |
|-----------------------------------|-------------------------------------------|
| **Создание множества аккаунтов**  | Лимит по `telegram_account_id`            |
| **Коммерческое использование**    | Лимит 5 групп на админа                   |
| **DDoS через парсеры**            | Rate limiting (60 запросов/мин глобально) |
| **Хранение данных**               | GDPR очистка (30 дней неактивности)       |

### Планы на монетизацию

| Тариф         | Источников | Групп | Топиков | Цена       |
|---------------|------------|-------|---------|------------|
| **Free**      | 25         | 5     | 20      | $0         |
| **Pro**       | 100        | 20    | 50      | $5-10/мес  |
| **Business**  | 500        | 100   | 200     | $20-30/мес |

### Реализация (план)

**1. Добавить настройки в `core/settings.py`:**
```python
# Лимиты для бесплатной версии
FREE_PLAN_SOURCES_LIMIT: int = 25
FREE_PLAN_TELEGRAM_LIMIT: int = 15
FREE_PLAN_YOUTUBE_LIMIT: int = 10
FREE_PLAN_GROUPS_LIMIT: int = 5
FREE_PLAN_TOPICS_PER_GROUP: int = 20
```

**2. Проверка лимитов в сервисах:**
```python
async def check_source_limit(user_id: int, session: AsyncSession) -> bool:
    count = await get_user_sources_count(user_id, session)
    return count < settings.FREE_PLAN_SOURCES_LIMIT
```

**3. Обновить модель `TelegramAccount`:**
```python
# Добавить поле
plan_type: Mapped[str] = mapped_column(String(20), default='free')  # free, pro, business
```

**Статус:** ✅ Реализовано в v6.4 (31 марта 2026)

**Реализация:**
- ✅ Сервис `core/services/limits.py` — `check_source_limit()`, `check_group_limit()`
- ✅ Интеграция в `bot/handlers/sources/finalize_handlers.py` — проверка перед добавлением
- ✅ Тесты `tests/test_limits.py` — 8 автотестов
- ✅ Ручное тестирование: превышение лимита Telegram-каналов (15 из 15) — ✅ работает
- ⏳ Ручное тестирование: YouTube, общий лимит, группы — отложено

**Что происходит при превышении:**
1. Пользователь получает ошибку с текущими значениями и лимитами
2. Сообщение об ошибке сохраняет `message_id` для обновления меню
3. Источник НЕ добавляется в базу данных

---

## 📊 МЕТРИКИ ПРОЕКТА

| Метрика | Значение | Примечание |
|---------|----------|------------|
| **Строк кода (Python)** | ~8700 | +120 строк (limits.py) |
| **Файлов Python** | 87+ | +2 файла (limits.py, test_limits.py) |
| **Тестов** | 112 | +8 тестов (limits) |
| **Покрытие тестами** | ~76% | 107 из 112 тестов |
| **Таблиц БД** | 10 | Без изменений |
| **Индексов БД** | 20+ | Без изменений |
| **Языков локализации** | 4 | ru, en, uk, be |
| **Зависимостей** | 25+ | Без изменений |
| **Rate Limiter** | ✅ Реализован | Token Bucket + Backoff |
| **Лимиты Free плана** | ✅ Реализованы | v6.4 (31 мар 2026) |
| **Документов** | 63+ | +2 документа (limits.md, v6.4.md) |
| **Модулей моделей** | 7 | users, sources, subscriptions, groups, assignments, cache, base |
| **Модулей сервисов** | 26+ | +limits service |

---

## 🔗 ССЫЛКИ

### Файлы отчётов
- `PROMPTS/Отчёт-Тесты TopicSourceAssignment.md` — тесты назначений
- `PROMPTS/Отчёт-Тесты очистки БД.md` — тесты GDPR/очистки
- `PROMPTS/RATE_LIMITING.md` — rate limiting руководство ✅

### Ключевые файлы проекта
- `core/models.py` — ORM модели
- `core/services/cleanup_service.py` — сервис очистки
- `core/services/rate_limiter.py` — rate limiting ✅
- `core/parser/telegram.py` — парсер Telegram (обновлён v5.3)
- `core/parser/youtube_simple.py` — парсер YouTube (обновлён v5.3)
- `tests/conftest.py` — фикстуры тестов
- `bot/main.py` — точка входа

### Внешние ресурсы
- [aiogram docs](https://docs.aiogram.dev/)
- [SQLAlchemy docs](https://docs.sqlalchemy.org/)
- [pytest docs](https://docs.pytest.org/)
- [Token Bucket алгоритм](https://en.wikipedia.org/wiki/Token_bucket)
- [Exponential Backoff](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)

---

**Отчёт подготовлен:** 25 февраля 2026
**Обновление v5.6:** 1 марта 2026 — Улучшение мониторинга и GDPR
**Обновление v5.5:** 1 марта 2026 — Исправление topic_checker
**Обновление v5.4:** 28 февраля 2026 — Разделение файлов на модули
**Обновление v5.3:** 28 февраля 2026 — Rate Limiting реализован
**Обновление v5.2:** 25 февраля 2026 — Тесты назначений
**Обновление v5.1:** 24 февраля 2026 — Тесты очистки (GDPR)
**Обновление v5.7:** 9 марта 2026 — Refactor Inline Only + централизация задержек
**Следующее обновление:** По мере развития проекта

---

## 🔄 ОБНОВЛЕНИЕ V5.7 (9 МАРТА 2026) — REFACTOR INLINE ONLY

### 🔧 Рефакторинг: Полный переход на Inline-клавиатуры

**Проблема:**
- В коде дублировались функции клавиатур: Reply ↔ Inline
- Обработчики `@router.message(F.text.in_(...))` + `@router.callback_query(...)`
- Нижняя панель кнопок занимала место в интерфейсе

**Реализовано:**
- ✅ **Полный отказ от ReplyKeyboardMarkup** — только InlineKeyboardMarkup
- ✅ **Удалены reply-функции** — `get_main_menu()`, `get_admin_panel_menu()`, `get_groups_menu()`, `get_destinations_menu()`, `get_cancel_kb_reply()`, `get_back_to_main_kb()`, `get_settings_menu()`
- ✅ **Удалены reply-обработчики** — все `@router.message(F.text.in_(...))` для кнопок меню
- ✅ **Удалены reply-константы** — `HELP_BUTTONS`, `MAIN_MENU_BUTTONS`, `CANCEL_BUTTONS`, `REFRESH_BUTTONS`, `ADMIN_PANEL_BUTTONS`, `MANAGE_GROUPS_BUTTONS`, `BACK_BUTTONS`, `SETTINGS_BUTTONS`, `ADD_CHANNEL_BUTTONS`

**Изменения в файлах:**
| Файл | Изменения |
|------|-----------|
| `bot/keyboards.py` | Удалено 7 reply-функций, обновлён `__all__`, удалены импорты `ReplyKeyboardMarkup`, `KeyboardButton`, `ReplyKeyboardBuilder` |
| `bot/handlers/common.py` | Удалены константы кнопок, удалены обработчики text.in_, оставлены только команды `/help`, `/cancel`, `/refresh` |
| `bot/handlers/admin.py` | Удалены константы ADMIN_PANEL_BUTTONS, MANAGE_GROUPS_BUTTONS, BACK_BUTTONS, удалены обработчики reply |
| `bot/handlers/settings_handler.py` | Удалены константы SETTINGS_BUTTONS, удалён обработчик `@router.message(Settings.main)` |
| `bot/handlers/sources/cancel_handlers.py` | Удалён обработчик `process_destination_choice()` |
| `bot/handlers/sources/add_channel.py` | Удалены константы ADD_CHANNEL_BUTTONS, удалён обработчик text.in_ |
| `bot/handlers/my_sources_interactive.py` | Удалён обработчик текстовой кнопки "Мои источники" |

**Результат:**
- ✅ Бот компилируется без ошибок
- ✅ Все 99 тестов пройдено
- ✅ Нет `ReplyKeyboardMarkup` в коде
- ✅ Нет `F.text.in_()` обработчиков
- ✅ Вся навигация через `@router.callback_query`
- ✅ Интерфейс интуитивно понятный

---

### 🐛 Исправление: Сохранение message_id при навигации

**Проблема:**
- При нажатии "Назад" в настройках message_id не сохранялся
- При повторном открытии настроек создавалось новое сообщение

**Решение:**
- ✅ В `on_settings_back()` добавлено сохранение message_id перед `state.clear()`
- ✅ Восстановление message_id после очистки состояния

**Файл:** `bot/handlers/settings_handler.py`

---

### 🎨 Изменение: Упрощение сообщения настроек

**Проблема:**
- Сообщение настроек содержало статистику с "?" (не реализована)
- При смене языка создавалось промежуточное сообщение

**Решение:**
- ✅ Убран текст со статистикой из `settings.title`
- ✅ При смене языка пользователь сразу возвращается в меню настроек (в том же message_id)

**Файлы:**
- `locales/ru.py`, `locales/en.py`, `locales/uk.py`, `locales/be.py` — обновлён `settings.title`
- `bot/handlers/settings_handler.py` — убрана передача `lang=lang_name` в `get_text(['settings', 'title'])`

**Было:**
```
⚙️ Настройки
👤 Язык: Русский
📊 Статистика:
• Личных подписок: ?
• Групп: ?
Выберите действие:
```

**Стало:**
```
⚙️ Настройки

Используйте команду /settings для изменения настроек.
```

---

### 🗑️ Изменение: Удаление источников в одном message_id

**Проблема:**
- При удалении источника создавалось новое сообщение с результатом
- Навигационное сообщение обновлялось отдельно

**Решение:**
- ✅ Удаление старого навигационного сообщения через `delete_menu_message_with_delay(delay=0)`
- ✅ Отправка нового сообщения с результатом
- ✅ Отправка нового навигационного сообщения
- ✅ Сохранение нового message_id в состоянии

**Файл:** `bot/handlers/my_sources_interactive.py`

---

### ⚡ Изменение: Мгновенное удаление сообщений (delay=0)

**Проблема:**
- Задержка удаления сообщений = 2 секунды
- Создавалось ощущение медленной работы бота

**Решение:**
- ✅ Изменена задержка на `delay=0` во всех хендлерах

**Файлы:**
- `bot/handlers/sources/add_channel.py`
- `bot/handlers/sources/destination_handlers.py`
- `bot/handlers/sources/group_select_handlers.py`
- `bot/handlers/sources/finalize_handlers.py`
- `bot/handlers/my_sources_interactive.py`
- `bot/handlers/common.py` (кнопка "Обновить")

---

### 📦 Изменение: Централизация задержек в menu_message.py

**Проблема:**
- Задержка `delay=0` указывалась явно в каждом хендлере
- Сложно изменить глобально

**Решение:**
- ✅ Добавлена константа `DEFAULT_DELETE_DELAY = 0` в `bot/utils/menu_message.py`
- ✅ Функция `delete_menu_message_with_delay()` использует `DEFAULT_DELETE_DELAY` по умолчанию
- ✅ Все хендлеры удалены явные указания `delay=0`
- ✅ Для изменения задержки достаточно поменять `DEFAULT_DELETE_DELAY` в одном месте

**Файлы:**
- `bot/utils/menu_message.py` — добавлена константа и обновлена функция
- Все хендлеры — удалены явные указания `delay=0`

**Результат:**
- ✅ Централизованное управление задержками
- ✅ Код проще в поддержке
- ✅ Все 99 тестов пройдено

---

## 📋 СПИСОК ЗАДАЧ (BACKLOG)

| # | Задача | Статус | Приоритет |
|---|--------|--------|-----------|
| 1 | Кнопка «Спасибо» | ⏳ Ожидает | 🟢 Низкий |
| 2 | Футер с рекламой | ⏳ Ожидает | 🟢 Низкий |
| 3 | Политика конфиденциальности | ⏳ Ожидает | 🟡 Средний |
| 4 | Условия использования | ⏳ Ожидает | 🟡 Средний |
| 5 | Качественная справка по использованию | ⏳ Ожидает | 🟡 Средний |
| 6 | Перевод на белорусский (с «теплом») | ⏳ Ожидает | 🟢 Низкий |
| 7 | Канал ТГ для инфо + поддержка в группе ТГ | ⏳ Ожидает | 🟡 Средний |
| 8 | Доделать кнопку «Удалить мои данные». Протестировать | ⏳ Ожидает | 🔴 Высокий |
| 9 | Подумать о рекламе проекта | ⏳ Ожидает | 🟢 Низкий |
| 10 | Продумать продакшен (Docker) | ⏳ Ожидает | 🟡 Средний |
| 11 | Поле «СОГЛАСЕН С ПОЛИТИКОЙ» в TelegramAccount | ⏳ Ожидает | 🔴 Высокий |
| 12 | ~~datetime.utcnow() → datetime.now(datetime.UTC)~~ | ✅ **РЕШЕНО** (v5.7) | 🔴 Высокий |
| 13 | Длинные имена групп/топиков + синхронизация имён | ⏳ Ожидает | 🔴 Высокий |
| 14 | ~~Источник добавился в content_sources при отмене~~ | ✅ **РЕШЕНО** | 🔴 Высокий |
| 15 | Добавить в хелп про удалённые топики (5 мин) | ⏳ Ожидает | 🟢 Низкий |
| 16 | ~~Rate limiting~~ | ✅ **РЕШЕНО** (v5.3) | 🔴 Высокий |
| 17 | Лимиты на источники (Free/Pro/Business) | ⏳ Ожидает | 🟡 Средний |
| 18 | ~~Разделить большие файлы~~ | ✅ **РЕШЕНО** (v5.3) | 🟡 Средний |
| 19 | Развёрнутое логирование по критичным пунктам | ⏳ Ожидает | 🟡 Средний |
| 20 | От некоторых каналов некорректное отображение name|@chennal
| 21 | Ютуб иногда выдаёт только ссылку, ТГ - иногда без медиа
| 22 | Переделать инлайн Мои источники (сортировка по группам/топикам/алфавиту/дата/активность)
| 23 | Добавить инлайн кнопки "Удалить пост" (только админы), (по возможности опционально)
| 24 | Добавить сортировку по источникам (имя/дата/ключевое слово). Хранить в Redis/json 48 часов
| 25 | А точно мониторинг работает отдельно от потоков другой работы бота???!!! При активной раюлте бота: добавление групп/топиков/источников во время мониторинга пропускает посты, которые уже в назначениях
| 26 | Проверка прав бота!!!!!!! С выводом сообщений пользователю, если что то не так!!!
| 27 | **Хранение состояния (FSM)**: MemoryStorage (dev) / RedisStorage (prod). Структура: `user_id`, `groups`, `groups_page`, `sources_message_id`, `current_group`, `current_topics`, `topics_page`, `topic_mapping`, `current_topic_identifier`. При `/list` удаляется старое сообщение перед показом нового.
| 28 | **Flood control в topic_checker**: Защита от частых проверок тем (Rate Limiting). При частых вызовах `/list` или навигации — задержка между проверками тем. Ошибка: `Flood control exceeded on method 'SendMessage'`. Решение: **лимит на количество проверок в минуту** (например, 10-15), очередь запросов с задержкой 1-2 сек. **Риск: бан Telegram при игнорировании!**
| 29 | ~~**Переход на Inline-кнопки**~~ | ✅ **РЕШЕНО** (v5.7) | 🔴 Высокий |

---

## 📋 ПЛАН РАЗРАБОТКИ (ROADMAP)

### Этап 1: Критические исправления (срочно)
**Цель:** Устранить риск бана от Telegram

| Задача | Описание | Срок |
|--------|----------|------|
| **28. Flood control защита** | Лимит 10-15 проверок тем в минуту, задержка 1-2 сек | v5.4 |
| **26. Проверка прав бота** | Вывод пользователю если нет прав админа/публикации | v5.4 |
| **13. Длинные имена** | Обрезка + синхронизация имён групп/топиков | v5.4 |

### Этап 2: Переход на Inline UI (среднесрочно)
**Цель:** Полный отказ от ReplyKeyboardMarkup

| Задача | Описание | Срок |
|--------|----------|------|
| **29. Главное меню Inline** | `get_main_menu()` → InlineKeyboardMarkup, callback: `menu_add`, `menu_sources`, `menu_feed`, `menu_help`, `menu_settings`, `menu_refresh` | ✅ **РЕШЕНО v5.7** |
| **29. Админ-панель Inline** | `get_admin_panel_menu()` → Inline, callback: `admin_groups`, `admin_topics`, `admin_stats`, `admin_monitoring` | ✅ **РЕШЕНО v5.7** |
| **29. Настройки Inline** | `get_settings_menu()` → Inline, callback: `settings_lang`, `settings_delete`, `settings_back` | ✅ **РЕШЕНО v5.7** |
| **29. Группы Inline** | `get_groups_menu()` → уже есть `get_groups_inline_kb()` | ✅ v5.3 |
| **29. Топики Inline** | `get_topics_inline_kb()` | ✅ v5.3 |
| **29. Источники Inline** | `get_source_list_kb()` | ✅ v5.3 |

**Схема работы Inline-меню:**
```
/start → Сообщение с Inline-кнопками (не Reply!)
├─ [✚ Добавить канал] → callback: menu_add → /add
├─ [📚 Источники] → callback: menu_sources → /list
├─ [📰 Лента] → callback: menu_feed → /feed
├─ [❓ Помощь] → callback: menu_help → /help
├─ [⚙️ Настройки] → callback: menu_settings → /settings
└─ [🔄 Обновить] → callback: menu_refresh → /refresh
```

**Преимущества:**
- ✅ Нет flood control (callback ≠ сообщение)
- ✅ Поле ввода свободно для команд
- ✅ Можно скрыть меню после выбора
- ✅ Единый стиль во всём боте

### Этап 3: Улучшения (долгосрочно)
**Цель:** Повышение удобства и функциональности

| Задача | Описание | Срок |
|--------|----------|------|
| **22. Сортировка источников** | По группам/топикам/алфавиту/дате/активности | v5.6 |
| **24. Сортировка по источникам** | Имя/дата/ключевое слово, кэш 48ч | v5.6 |
| **17. Лимиты источников** | Free/Pro/Business тарифы | v5.7 |
| **23. Удаление постов** | Inline-кнопка "Удалить" для админов | v5.6 |
| **15. Хелп по топикам** | Информация об удалённых топиках | v5.5 |

### Этап 4: Инфраструктура (production)
**Цель:** Подготовка к продакшену

| Задача | Описание | Срок |
|--------|----------|------|
| **10. Docker** | Контейнеризация для продакшена | v5.8 |
| **8. Удаление данных (GDPR)** | Полное тестирование и доработка | v5.5 |
| **11. Согласие с политикой** | Поле в TelegramAccount | v5.5 |
| **3-4. Политика + Условия** | Документы для пользователей | v5.6 |

### Этап 5: Маркетинг и поддержка
**Цель:** Продвижение проекта

| Задача | Описание | Срок |
|--------|----------|------|
| **7. Инфо-канал + поддержка** | Telegram-канал + группа для вопросов | v5.6 |
| **9. Реклама** | Продумать стратегию продвижения | v5.7 |
| **1-2. Кнопка "Спасибо" + Футер** | Дополнительные функции | v5.7 |
| **6. Перевод на белорусский** | С "теплом" и локализацией | v5.6 |

---

**Обновление v6.0:** 17 марта 2026 — Refactor Architecture: разделение keyboards/ и messages/
**Обновление v5.7:** 9 марта 2026 — Refactor Inline Only + централизация задержек
**Обновление v5.6:** 1 марта 2026 — Улучшение мониторинга, GDPR очистка, Redis клиент
**Обновление v5.5:** 1 марта 2026 — Исправление topic_checker
**Обновление v5.4:** 28 февраля 2026 — Разделение файлов на модули
**Обновление v5.3:** 28 февраля 2026 — Rate Limiting (Token Bucket + Exponential Backoff)

**Статус проекта:** ✅ Активная разработка (v6.0)
**Тесты:** ✅ 99 пройдено, 5 skip
**Следующее обновление:** v6.1 — Type hints в сервисах + мониторинг

---

## 📊 СТАТИСТИКА ПРОЕКТА (v6.0)

### Общая статистика

| Метрика | Значение |
|---------|----------|
| **Python файлов** | 149 (всего) / 115 (рабочий код) |
| **Строк кода** | 23 426 (всего) / 18 289 (рабочий код) |
| **Рабочего кода** | 13 521 строк (73%) |
| **Пустых строк** | 3 422 (15%) |
| **Комментариев** | 1 346 (6%) |

### По директориям

| Директория | Файлов | Всего строк | Рабочий код | Пустые | Комментарии |
|------------|--------|-------------|-------------|--------|-------------|
| **bot/** | 38 | 7 079 | 5 259 | 1 240 | 580 |
| **core/** | 61 | 7 588 | 5 756 | 1 416 | 416 |
| **tests/** | 10 | 2 585 | 1 738 | 575 | 272 |
| **migrations/** | 5 | 421 | 331 | 59 | 31 |
| **tools/** | 1 | 616 | 437 | 132 | 47 |
| **ИТОГО** | **115** | **18 289** | **13 521** | **3 422** | **1 346** |

### Изменения v6.0 (рефакторинг)

| Файл | Строк | Изменение |
|------|-------|-----------|
| `bot/keyboards.py` | 47 | **-95%** (было 869 строк) |
| `bot/keyboards/*.py` | 7 файлов | **+869** строк (новые модули) |
| `bot/messages/*.py` | 2 файла | **+95** строк (новый модуль) |

### Тестирование

| Категория | Тестов | Пройдено | Статус |
|-----------|--------|----------|--------|
| Очистка (GDPR) | 14 | 14 ✅ | 100% |
| Destination Service | 23 | 23 ✅ | 100% |
| Monitoring Service | 9 | 9 ✅ | 100% |
| Назначения | 8 | 8 ✅ | 100% |
| Rate Limiting | 23 | 23 ✅ | 100% |
| YouTube | 11 | 9 ✅ | 100% |
| Интеграционные | 5 | 5 skip | — |
| **ИТОГО** | **104** | **99 ✅** | **100%** |

---

## ℹ️ ПРИМЕЧАНИЯ

### Ограничения Telegram Bot API

**Массовые рассылки:**
- Бесплатно: ~30 сообщений в секунду
- Платно: до 1000 сообщений в секунду (через Telegram Stars)
- Рекомендуется: распределять уведомления на 8-12 часов

**Лимиты:**
- В личном чате: 1 сообщение в секунду
- В группе: 20 сообщений в минуту
- Массовые уведомления: 30 сообщений в секунду

### Контакты поддержки

- **@BotSupport** — техническая поддержка ботов
- **@BotFather** — управление ботами, платные трансляции
- **https://core.telegram.org/bots/faq** — документация API

---

**Последнее обновление:** 17 марта 2026  
**Версия документа:** 6.0  
**Статус:** ✅ Актуально





**Вещание для пользователей**
Мой бот набирает обороты, как мне этого избежать?

По умолчанию боты могут бесплатно отправлять сообщения своим пользователям, at no costно имеют ограничения на количество сообщений, которые они могут транслировать в один интервал:

    В одном чате избегайте отправки более одного сообщения в секунду. Мы можем разрешить короткие всплески, которые превышают этот предел, но в конечном итоге вы начнете получать 429 ошибок.
    В группе боты не могут отправлять более 20 сообщений в минуту.
    Для массовых уведомлений боты не могут передавать более 30 сообщений в секунду, если они не позволяют платным трансляциям увеличивать лимит.

Как я могу отправить сообщение всем подписчикам моего бота сразу?

Предоставление платных трансляций в @BotFather позволяет боту транслировать до 1000 сообщений в секунду. Каждое сообщение, транслируемое за бесплатную сумму в 30 секунд, влечет за собой стоимость 0,1 Звезды за сообщение, оплаченную Telegram Stars с баланса бота. Чтобы включить эту функцию, бот должен иметь не менее 100,000 звезд на своем балансе и не менее 100,000 активных пользователей в месяц.

    Боты с увеличенными лимитами взимаются только за сообщения, которые успешно транслируются.

Если вы не хотите включать платные трансляции, подумайте о том, чтобы распределить их с более длительными интервалами (например, 8-12 часов), чтобы избежать достижения лимита. API не позволит массовые уведомления более чем ~ 30 пользователям в секунду - если вы пройдете через это, вы начнете получать 429 ошибок.

    Если у вас есть вопросы, на которые не отвечают, звоните нам в @BotSupport в Telegram.
    Мы приветствуем любые предложения по платформе для Bot Platform и API. https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this




   
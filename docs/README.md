# 📚 Документация MyAggryBot

**Версия проекта:** 6.9
**Последнее обновление:** 8 апреля 2026

---

## 🚀 Быстрый старт

| Документ | Описание |
|----------|----------|
| [📖 Обзор проекта](overview.md) | Полная информация о проекте (1300 строк) |
| [⚙️ Как работает](01-general/how-it-works.md) | **Кратко:** парсинг → отправка → лимитеры |
| [📋 Changelog](CHANGELOG.md) | История версий со ссылками на детали |
| [🏗️ Архитектура](01-general/architecture.md) | Распределённая архитектура (бот, мониторинг, отправщик) |

---

## 📁 Структура документации

### 📌 Общая документация

| Файл | Описание |
|------|----------|
| [overview.md](overview.md) | **ГЛАВНЫЙ** — полный отчёт по проекту |
| [01-general/how-it-works.md](01-general/how-it-works.md) | **Кратко:** парсинг → отправка → лимитеры (для ИИ) |
| [01-general/architecture.md](01-general/architecture.md) | Архитектура и сервисы |
| [01-general/deployment.md](01-general/deployment.md) | Развёртывание и окружение |

### 🎮 Хендлеры (бот)

| Файл | Описание |
|------|----------|
| [02-handlers/README.md](02-handlers/README.md) | Обзор всех хендлеров |
| [02-handlers/common.md](02-handlers/common.md) | `/start`, `/help`, `/refresh` |
| [02-handlers/admin.md](02-handlers/admin.md) | `/activ`, `/plus`, `/mytopics` |
| [02-handlers/settings.md](02-handlers/settings.md) | `/settings`, смена языка |
| [02-handlers/my_sources.md](02-handlers/my_sources.md) | `/list`, навигация по источникам |
| [02-handlers/my_overview.md](02-handlers/my_overview.md) | `/overview` |
| [02-handlers/sources/](02-handlers/sources/) | Добавление источников |

### ⌨️ Клавиатуры

| Файл | Описание |
|------|----------|
| [03-keyboards/README.md](03-keyboards/README.md) | Принцип работы inline-клавиатур |
| [03-keyboards/pagination.md](03-keyboards/pagination.md) | **Готово** — система пагинации |
| [03-keyboards/menu-system.md](03-keyboards/menu-system.md) | **Готово** — управление сообщениями меню |
| [03-keyboards/reference.md](03-keyboards/reference.md) | Справочник всех клавиатур |

### 🔧 Сервисы

| Файл | Описание |
|------|----------|
| [04-services/README.md](04-services/README.md) | Обзор сервисов |
| [04-services/post-sender.md](04-services/post-sender.md) | **PostSender** — отправка постов с превью |
| [04-services/rate-limiting.md](04-services/rate-limiting.md) | **Готово** — Rate Limiting (Token Bucket) |
| [04-services/monitoring.md](04-services/monitoring.md) | **Готово** — Monitoring Service |
| [04-services/destinations.md](04-services/destinations.md) | Destination Service |
| [04-services/cleanup-gdpr.md](04-services/cleanup-gdpr.md) | GDPR очистка |
| [04-services/youtube.md](04-services/youtube.md) | YouTube Service |

### 🕸️ Парсеры

| Файл | Описание |
|------|----------|
| [05-parsers/README.md](05-parsers/README.md) | Обзор парсеров |
| [05-parsers/telegram.md](05-parsers/telegram.md) | Telegram парсер |
| [05-parsers/youtube.md](05-parsers/youtube.md) | YouTube парсер |

### 🗄️ База данных

| Файл | Описание |
|------|----------|
| [06-database/README.md](06-database/README.md) | Обзор БД |
| [06-database/schema.md](06-database/schema.md) | Схема таблиц, FK связи |
| [06-database/models.md](06-database/models.md) | ORM модели |
| [06-database/migrations.md](06-database/migrations.md) | Alembic миграции |

### 🧪 Тестирование

| Файл | Описание |
|------|----------|
| [07-testing/README.md](07-testing/README.md) | Обзор тестирования |
| [07-testing/fixtures.md](07-testing/fixtures.md) | Фикстуры pytest |
| [07-testing/categories.md](07-testing/categories.md) | Категории тестов |
| [07-testing/running.md](07-testing/running.md) | Запуск тестов |

### 🌐 Локализация (i18n)

| Файл | Описание |
|------|----------|
| [08-i18n/README.md](08-i18n/README.md) | Обзор локализации |
| [08-i18n/languages.md](08-i18n/languages.md) | Список языков, как добавить |

### � Legal (GDPR)

| Файл | Описание |
|------|----------|
| [legal/README.md](legal/README.md) | Обзор правовой документации |
| [legal/terms.md](legal/terms.md) | Условия использования (полная версия) |
| [legal/privacy.md](legal/privacy.md) | Политика конфиденциальности (полная) |
| [legal/terms-privacy.md](legal/terms-privacy.md) | Условия и конфиденциальность (кратко) |

### �📦 Версии

| Файл | Описание |
|------|----------|
| [09-versions/README.md](09-versions/README.md) | Структура файлов версий |
| [CHANGELOG.md](CHANGELOG.md) | **Готово** — история версий |
| [09-versions/v6.2.md](09-versions/v6.2.md) | **Готово** — текущая версия |
| [09-versions/v6.1.md](09-versions/v6.1.md) | **Готово** — масштабирование |
| [09-versions/v6.0.md](09-versions/v6.0.md) | **Готово** — рефакторинг архитектуры |
| [09-versions/v5.7.md](09-versions/v5.7.md) | **Готово** — inline-only |
| [09-versions/v5.6.md](09-versions/v5.6.md) | **Готово** — GDPR + Redis |
| [09-versions/v5.3.md](09-versions/v5.3.md) | **Готово** — Rate Limiting |
| [09-versions/v5.0.md](09-versions/v5.0.md) | **Готово** — YouTube |
| [09-versions/v4.0.md](09-versions/v4.0.md) | **Готово** — Destination Service |
| [09-versions/v3.0.md](09-versions/v3.0.md) | **Готово** — Monitoring Service |
| [09-versions/v1.0-v2.0.md](09-versions/) | **Готово** — ранние версии |

### 🔒 Внутренняя документация

| Файл | Описание |
|------|----------|
| [10-internal/prompts/](10-internal/prompts/) | Промпты для рефакторинга |
| [10-internal/meetings/](10-internal/meetings/) | Заметки встреч/чатов |
| [10-internal/drafts/](10-internal/drafts/) | Черновики |

---

## 📊 Статус документации

| Категория | Статус | Готово |
|-----------|--------|--------|
| Общая | 🟢 Готово | 3/3 ✅ |
| Хендлеры | 🟢 Готово | 11/11 ✅ |
| Клавиатуры | 🟢 Готово | 5/5 ✅ |
| Сервисы | 🟢 Готово | 6/6 ✅ |
| Парсеры | 🟢 Готово | 3/3 ✅ |
| БД | 🟢 Готово | 4/4 ✅ |
| Тесты | 🟢 Готово | 5/5 ✅ |
| i18n | 🟢 Готово | 2/2 ✅ |
| Legal | 🟢 Готово | 4/4 ✅ |
| Версии | 🟢 Готово | 17/17 ✅ |

**Итого:** 60/60 документов (100%) ✅

---

## 🔗 Полезные ссылки

- [QWEN.md](../QWEN.md) — документация проекта (корень)
- [PROMPTS/](../PROMPTS/) — исходные файлы (устаревшие)
- [bot/](../bot/) — код бота
- [core/](../core/) — ядро проекта
- [tests/](../tests/) — тесты

---

## 📝 Как работать с документацией

### Добавить новую версию

1. Создать файл `docs/09-versions/v{X}.{Y}.md`
2. Заполнить по шаблону (см. [09-versions/README.md](09-versions/README.md))
3. Обновить [CHANGELOG.md](CHANGELOG.md)
4. Обновить [overview.md](overview.md) — версию проекта

### Обновить существующий документ

1. Открыть файл на редактирование
2. Внести изменения
3. Обновить дату вверху файла
4. Закоммитить с описанием изменений

### Создать новый раздел

1. Создать папку в нужной категории
2. Создать `README.md` с навигацией
3. Добавить ссылки в этот файл

---

## 🤖 Настройки ИИ-ассистента

Конфигурация Qwen Code находится в [`.qwen/settings.json`](../.qwen/settings.json).

**Важно:** Ассистент обязан:
- Создавать файл версии при каждом изменении
- Обновлять CHANGELOG.md
- Поддерживать актуальность документации

# MyAggryBot — Как работает

**Проект:** Telegram-агрегатор контента v6.9

---

## 1. Парсинг и отправка

### Flow

```
scheduler запускает check_all_sources()
  ↓
для каждого ContentSource (Telegram канал):
  check_telegram_source(source)
  ↓
get_telegram_posts(username, last_post_id)
  ├─→ GET https://t.me/s/{username}
  ├─→ Парсит HTML через BeautifulSoup
  ├─→ Извлекает: текст (HTML), timestamp, медиа (photo/video/animation/audio/document)
  └─→ Возвращает список новых постов
  ↓
для каждого нового поста:
  _process_telegram_post(post)
  ↓
PostSender.send_to_assignment(post, assignment, source)
  ├─→ _check_media_ready(post)           # Проверяет доступность медиа (HEAD запрос)
  │     ├─→ Логирует количество и типы медиа
  │     ├─→ HEAD запрос к первому медиа
  │     └─→ Если не 200 → ждёт 60с → проверяет снова (макс 2 попытки)
  │
  ├─→ _format_telegram_post_message()    # HTML: "📢 Канал | @username\n14:30\n\nТекст"
  ├─→ _get_original_post_keyboard()      # Кнопка "📢 Канал → t.me/channel/123"
  ├─→ _get_link_preview_options()        # LinkPreviewOptions(url="t.me/...", is_disabled=False)
  │
  └─→ _send_message_with_retry()
        ├─→ bot.send_message(text, parse_mode="HTML", link_preview_options, keyboard)
        ├─→ Ошибка парсинга → fallback на plain text (html_to_plain_text)
        └─→ Flood control → backoff
  ↓
updated_topics → bulk update last_seen_at
```

### Ключевые файлы

| Файл | Что делает |
|------|------------|
| `core/parser/telegram_posts.py` | Парсит t.me/s/username, извлекает HTML, timestamp, медиа URL |
| `core/services/monitoring/post_sender.py` | Отправляет пост в тему (~380 строк) |
| `core/services/monitoring/telegram_monitor.py` | Orchestrator: парсер → проверка → отправка |
| `core/services/monitoring/scheduler.py` | APScheduler: запускает проверку по расписанию |

### Что НЕ отправляется

- ❌ Медиа не скачивается — только текст + превью через `LinkPreviewOptions`
- ❌ Альбомы не поддерживаются
- ❌ Нет скачивания/загрузки файлов

---

## 2. Rate Limiting (защита от бана)

### Файл: `core/services/rate_limiter.py`

### Token Bucket (для запросов к API)

```
Telegram:  capacity=20, refill=10 токенов/сек
YouTube:   capacity=5,  refill=1 токенов/сек
```

Каждый запрос забирает 1 токен. Нет токенов → ждём.

### Error Backoff (защита от ошибок)

```
1-я ошибка:   жду 5с
2-я ошибка:   жду 10с
3-я ошибка:   жду 20с
4-я ошибка:   жду 30с (макс)
Успех:        сброс
```

### Глобальный лимит

- Макс **60 запросов/мин** на всё

### Free Plan лимиты

| Ресурс | Лимит |
|--------|-------|
| Источников | 25 |
| Telegram каналов | 15 |
| YouTube | 10 |
| Групп | 5 |
| Топиков в группе | 20 |

### Защита от простоя

- Если бот был offline > 1 часа → отправляет только последние **5 постов** (DOWNTIME_MAX_POSTS)

### Кэширование

- Неактивные группы: кэш 5 минут
- Удалённые топики: кэш 5 минут
- Обработанные посты: `set` в памяти

---

## 3. Что отправляется в тему

```
┌─────────────────────────────┐
│ [ПРЕВЬЮ — если есть медиа]   │  ← Telegram сам подтягивает
└─────────────────────────────┘

📢 TechCrunch | @techcrunch
14:30

Текст поста с <b>форматированием</b>,
<i>курсивом</i>, <a href="...">ссылками</a>

[📢 TechCrunch → t.me/techcrunch/123]  ← Inline кнопка
```

---

## 4. Переменные окружения (защита)

```bash
# Rate Limiting
RATE_LIMIT_TELEGRAM_TOKENS=20
RATE_LIMIT_TELEGRAM_REFILL=10.0
RATE_LIMIT_YOUTUBE_TOKENS=5
RATE_LIMIT_YOUTUBE_REFILL=1.0
RATE_LIMIT_GLOBAL_PER_MINUTE=60

# Free Plan
FREE_PLAN_SOURCES_LIMIT=25
FREE_PLAN_TELEGRAM_LIMIT=15
FREE_PLAN_YOUTUBE_LIMIT=10
FREE_PLAN_GROUPS_LIMIT=5
FREE_PLAN_TOPICS_PER_GROUP_LIMIT=20

# Защита от простоя
DOWNTIME_MAX_POSTS=5
```

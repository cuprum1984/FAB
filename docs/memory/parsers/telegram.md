# Telegram Parser — Контекст

**Последнее обновление:** 6 апреля 2026
**Версия:** 6.7

---

## 📋 Что это

Парсинг публичных Telegram каналов через **веб-версию** `t.me/s/{username}`.

**Не используется:**
- ❌ Telethon (User API)
- ❌ Bot API (требует админства)
- ❌ Официальный Telegram API

---

## 🎯 Ключевые файлы

| Файл | Назначение |
|------|------------|
| `core/parser/telegram.py` | Проверка существования канала |
| `core/parser/telegram_posts.py` | **Основная функция** `get_new_posts()` |
| `core/utils/html_sanitizer.py` | HTML санитизация (v6.7) |
| `core/services/monitoring/telegram_monitor.py` | Оркестрация проверки |

---

## ⚙️ Как работает

### 1. Запрос к `t.me/s/`

```python
url = f"https://t.me/s/{username}"
async with aiohttp.ClientSession() as session:
    async with session.get(url, headers=headers, timeout=10) as response:
        html = await response.text()
```

### 2. Парсинг HTML

```python
soup = BeautifulSoup(html, 'html.parser')
post_elements = soup.find_all('div', class_='tgme_widget_message_wrap')
```

### 3. Извлечение данных

| Поле | Селектор | Примечание |
|------|----------|------------|
| `post_id` | `a.tgme_widget_message_date` → `href` → последний сегмент | Из URL |
| `text` | `div.tgme_widget_message_text` → **HTML** → санитизация | **HTML** (v6.7) |
| Фото | `find_all('a.tgme_widget_message_photo_wrap')` → `style` → regex | **Все фото** (альбомы, v6.7) |
| Видео | `video.tgme_widget_message_video` → `src` | Прямая ссылка |
| GIF/анимация | `a.tgme_widget_message_gif` → `data-video-src` | v6.7 |
| Аудио | `audio.tgme_widget_message_voice` → `src` | v6.7 |
| Документ | `a.tgme_widget_message_document_wrap` → `href` | v6.7 |
| `url` | Формируется: `f"https://t.me/{username}/{post_id}"` | Вручную |
| `timestamp` | `<time>` → `datetime` | ✅ **Извлекается** (v6.7) |

### 4. Исключение цитат (v6.7)

```python
# Клонируем элемент, удаляем reply, ищем основной текст
post_clone = BeautifulSoup(str(post_element), 'html.parser')
for reply in post_clone.find_all(class_='tgme_widget_message_reply'):
    reply.decompose()
text_elem = post_clone.find('div', class_='tgme_widget_message_text')
```

### 5. Дедупликация

```python
if last_post_id:
    if int(post_id) <= int(last_post_id):
        continue  # Пропускаем уже виденные
```

---

## 📦 Возвращаемая структура

```python
{
    'post_id': '12345',        # Строковый ID из URL
    'text': '<b>Жирный</b> текст...',  # HTML (v6.7)
    'media': [                 # Список медиа
        {'type': 'photo', 'url': 'https://...'},
        {'type': 'video', 'url': 'https://...'},
        {'type': 'animation', 'url': 'https://...'},
        {'type': 'audio', 'url': 'https://...'},
        {'type': 'document', 'url': 'https://...'}
    ],
    'url': 'https://t.me/username/12345',
    'timestamp': 1712345678    # Unix timestamp (v6.7)
}
```

---

## ⚠️ Важные решения

| Версия | Решение | Причина |
|--------|---------|---------|
| **5.0** | Веб-парсинг вместо Telethon | Не нужна авторизация |
| **5.3** | Rate Limiting (Token Bucket) | Защита от бана |
| **5.3** | Exponential Backoff | При ошибках |
| **6.7** | HTML вместо plain text | Сохранение форматирования |
| **6.7** | Все фото (find_all) | Поддержка альбомов |
| **6.7** | Исключение цитат | Не брать текст из reply |
| **6.7** | Извлечение timestamp | Отображение времени поста |

---

## 🔧 Конфигурация

```python
# Rate Limiting
RATE_LIMIT_TELEGRAM_TOKENS=20      # Ёмкость ведра
RATE_LIMIT_TELEGRAM_REFILL=10.0    # Токенов/сек
```

---

## 🔄 Поток выполнения

```
telegram_monitor.check_telegram_source()
    ↓
get_cached_last_post(username)  # Redis
    ↓
get_new_posts(username, last_post_id)  # Парсер
    ↓
Для каждого поста:
    ├─→ Загрузка file_id из кэша (БД)
    ├─→ _process_telegram_post()
    │   └─→ PostSender.send_to_assignment()  # HTML + медиа + кнопка (v6.7)
    ↓
update_source_last_post_id()  # БД + Redis
    ↓
session.commit()
```

---

## 🔗 Связанные документы

- [`../../docs/05-parsers/telegram.md`](../../docs/05-parsers/telegram.md) — полная документация
- [`../../docs/04-services/rate-limiting.md`](../../docs/04-services/rate-limiting.md) — Rate Limiting
- [`../../docs/memory/parsers/README.md`](README.md) — обзор парсеров
- [`../../docs/memory/services/README.md`](../services/README.md) — мониторинг

# 📡 Telegram Парсер

**Файл:** `core/parser/telegram_posts.py`
**Версия:** 5.1 (24 мая 2026)

---

## 📋 Обзор

Парсер для получения постов из публичных Telegram каналов через **веб-версию** `t.me/s/`.

**Не использует:**
- ❌ Telethon / Pyrogram (User API)
- ❌ Bot API (требует админства)
- ❌ Официальный Telegram API

---

## 🎯 Основная функция

### `get_new_posts(username, last_post_id, first_only, limit)`

Получение новых постов из канала.

**Параметры:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `username` | `str` | Username канала (без `@`) |
| `last_post_id` | `str \| None` | ID последнего известного поста |
| `first_only` | `bool` | Если `True` — вернуть только последний пост |
| `limit` | `int` | Максимум постов (по умолчанию 50) |

**Возвращает:**
```python
List[Dict] = [
    {
        'post_id': '12345',        # Строковый ID из URL
        'text': 'Текст поста',     # Plain text (без форматирования)
        'media': [                 # Список медиа
            {'type': 'photo', 'url': 'https://...'},
            {'type': 'video', 'url': 'https://...'}
        ],
        'url': 'https://t.me/username/12345',
        'timestamp': None          # Всегда None
    }
]
```

---

## 📁 Вспомогательные файлы

### `core/parser/telegram.py`

**Функция:** `check_channel_exists(username)`

Проверяет существование публичного канала.

**Возвращает:**
```python
tuple[bool, str] = (True, "Канал существует")
```

---

## 🔄 Процесс парсинга

```
1. GET https://t.me/s/{username}
   ↓
2. BeautifulSoup(html)
   ↓
3. Найти div.tgme_widget_message_wrap
   ↓
4. Для каждого поста:
   ├─→ post_id из a.tgme_widget_message_date → href
   ├─→ text из div.tgme_widget_message_text → .get_text()
   ├─→ media из:
   │   ├─→ a.tgme_widget_message_photo_wrap → style → regex
   │   └─→ video.tgme_widget_message_video → src
   └─→ url = f"https://t.me/{username}/{post_id}"
   ↓
5. Фильтрация: post_id > last_post_id
   ↓
6. Сортировка по post_id (от старых к новым)
   ↓
7. Возврат списка
```

---

## 🗂️ Зависимости

| Модуль | Назначение |
|--------|------------|
| `aiohttp` | HTTP-запросы |
| `ssl` + `certifi` | SSL-контекст (кросс-платформенный bundle сертификатов) |
| `bs4` (BeautifulSoup) | Парсинг HTML |
| `core.settings` | Настройки (USER_AGENT, REQUEST_TIMEOUT) |
| `core.security.URLSecurity` | Проверка безопасности URL |
| `core.services.rate_limiter` | Rate Limiting |

---

## ⚠️ Особенности

### 1. Форматирование теряется

```python
text = text_elem.get_text()  # ❌ Только plain text
```

Bold, italic, ссылки, code — **всё теряется**.

### 2. Timestamp не извлекается

```python
'timestamp': None  # Всегда None
```

Дата есть в HTML (`<time datetime="...">`), но не извлекается.

### 3. Rate Limiting

```python
# Из core/services/rate_limiter.py
RATE_LIMIT_TELEGRAM_TOKENS=20      # Ёмкость ведра
RATE_LIMIT_TELEGRAM_REFILL=10.0    # Токенов/сек
```

### 4. SSL-контекст (v5.1)

```python
import ssl
import certifi
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
# передаётся в session.get(url, ssl=_SSL_CTX)
```

Используется `certifi` вместо системного хранилища Windows/Linux — гарантирует доверие к сертификату `t.me` (Cloudflare) на любом окружении.

### 5. Дедупликация

```python
if last_post_id:
    if int(post_id) <= int(last_post_id):
        continue  # Пропускаем уже виденные
```

---

## 🧪 Тесты

Тесты для парсера находятся в `tests/test_telegram_posts.py`.

---

## 🔗 Связанные документы

- [`README.md`](README.md) — Обзор парсеров
- [`../04-services/monitoring.md`](../04-services/monitoring.md) — Мониторинг
- [`../memory/parsers/telegram.md`](../memory/parsers/telegram.md) — Память парсера

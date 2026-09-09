# PostSender — Отправка постов

**Версия:** 6.9
**Файл:** `core/services/monitoring/post_sender.py` (~380 строк)

---

## 📋 Что это

Сервис отправки постов в темы групп. Отправляет HTML текст с умным превью и кнопкой на оригинал.

---

## ⚙️ Как работает

### Flow

```
send_to_assignment(post, assignment, source)
  ↓
_check_media_ready(post)           # Проверка медиа
  ├─→ Логирует: "📎 Медиа: 2 шт (2xphoto)"
  ├─→ HEAD запрос к первому медиа
  └─→ Если не 200 → ждёт 60с → снова (макс 2 попытки)
  ↓
_format_telegram_post_message()    # HTML: "📢 Канал | @user\n14:30\n\nТекст"
_get_original_post_keyboard()      # Кнопка "📢 Канал → t.me/..."
_get_link_preview_options()        # LinkPreviewOptions(url="t.me/...")
  ↓
_send_message_with_retry()
  ├─→ bot.send_message(text, parse_mode="HTML", link_preview_options, keyboard)
  ├─→ Ошибка парсинга → fallback на plain text
  └─→ Flood control → backoff
```

---

## 🔑 Методы

| Метод | Назначение |
|-------|------------|
| `send_to_assignment()` | Главный метод — вызывает всё остальное |
| `_check_media_ready()` | Проверяет доступность медиа (HEAD запрос) |
| `_check_media_available()` | HEAD запрос к URL медиа |
| `_send_message_with_retry()` | Отправка с retry и обработкой ошибок |
| `_get_link_preview_options()` | LinkPreviewOptions (всегда включено) |
| `_get_original_post_keyboard()` | Inline кнопка "📢 Название канала" |
| `_format_telegram_post_message()` | Форматирование HTML текста |
| `_mark_group_inactive()` | Пометить группу как неактивную |
| `_mark_topic_deleted()` | Пометить тему как удалённую |

---

## 🔗 Превью

**Всегда включено** для всех постов:

```python
LinkPreviewOptions(
    is_disabled=False,
    url="https://t.me/channel/123",    # Обычная ссылка (откроет в Telegram app)
    prefer_large_media=True,            # Максимальный размер
    show_above_text=True                # Над текстом
)
```

---

## ⚠️ Что удалено (v6.9)

| Было | Стало |
|------|-------|
| Скачивание медиа (`_download_media`) | ❌ Удалено |
| Отправка через `FSInputFile` | ❌ Удалено |
| `_send_media_by_url()` | ❌ Удалено |
| `_send_plain_text_to_assignment()` | ❌ Удалено |
| Fallback приоритеты (3 метода) | ❌ Удалено |
| `_copy_message_to_topic()` | ❌ Удалено |
| `send_media_to_assignment()` | ❌ Удалено |
| `send_text_to_assignment()` | ❌ Удалено |

**Результат:** 956 → 380 строк (-60%)

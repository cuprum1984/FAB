# PostSender — Контекст

**Последнее обновление:** 6 апреля 2026
**Версия:** 6.7

---

## 📋 Что это

Сервис отправки постов в темы групп. v6.7: HTML + медиа по URL + Inline кнопка.

---

## 🎯 Ключевые файлы

| Файл | Назначение |
|------|------------|
| `core/services/monitoring/post_sender.py` | **Основной класс** `PostSender` |
| `core/utils/html_sanitizer.py` | HTML санитизация |
| `core/services/monitoring/telegram_monitor.py` | Вызывает `send_to_assignment()` |

---

## ⚙️ Как работает (v6.7)

### Приоритеты отправки

```
send_to_assignment()
  ↓
┌─────────────────────────────────────────┐
│ ПРИОРИТЕТ 1: HTML + медиа + кнопка      │
│                                         │
│ 1. Скачивает медиа → временный файл     │
│ 2. Отправляет FSInputFile + caption     │
│ 3. InlineKeyboardButton "Открыть"       │
│ 4. Удаляет временный файл               │
│                                         │
│ Если успех → return True                │
│ Если ошибка → fallback ↓                │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│ ПРИОРИТЕТ 2: Plain text + кнопка        │
│                                         │
│ BeautifulSoup.get_text() → без тегов    │
│ + InlineKeyboardButton                  │
└─────────────────────────────────────────┘
```

### Скачивание медиа

```python
# Скачиваем чанками по 64KB, не в RAM
fd, temp_path = tempfile.mkstemp(suffix=ext, prefix='aggry_media_')
with open(temp_path, 'wb') as f:
    async for chunk in resp.content.iter_chunked(64 * 1024):
        f.write(chunk)

# Отправляем через FSInputFile
await bot.send_photo(chat_id, photo=FSInputFile(temp_path), ...)

# Удаляем
os.unlink(temp_path)
```

### Caption лимиты

| Тип | Лимит |
|-----|-------|
| Медиа caption | **1024 символа** |
| Текст сообщения | **4096 символов** |

---

## 📁 Временные файлы

- Скачиваются в системную временную директорию (`/tmp` или `%TEMP%`)
- Формат имени: `aggry_media_*.jpg`, `aggry_media_*.mp4`, и т.д.
- **Удаляются сразу** после отправки (`finally` блок)
- **Не загружают RAM** — только диск на несколько секунд

---

## ⚠️ Важные решения

| Версия | Решение | Причина |
|--------|---------|---------|
| **6.2** | Bulk update last_seen_at | Оптимизация БД |
| **6.2** | Изоляция ошибок | Не прерывать поток |
| **6.7** | HTML вместо plain text | Сохранение форматирования |
| **6.7** | Медиа по URL (скачивание) | CDN ссылки не работают |
| **6.7** | FSInputFile | aiogram 3.x требует |
| **6.7** | Inline кнопка | Вместо ссылки в тексте |
| **6.7** | Убран copy_message | Не работает для внешних каналов |
| **6.7** | Plain text = get_text() | Не html.escape() |

---

## 🔄 Поток выполнения

```
telegram_monitor._process_telegram_post()
    ↓
PostSender.send_to_assignment()
    ↓
_send_html_text_to_assignment()
    ↓
_send_media_by_url()  (если есть медиа)
    ├─→ _download_media() → временный файл
    ├─→ bot.send_photo(FSInputFile(...), caption, reply_markup)
    └─→ os.unlink(temp_path)
    ↓
Если ошибка → _send_plain_text_to_assignment()
```

---

## 🔗 Связанные документы

- [`../../docs/memory/parsers/telegram.md`](../parsers/telegram.md) — парсер
- [`../../docs/04-services/README.md`](../../docs/04-services/README.md) — сервисы
- [`../../docs/09-versions/v6.7.md`](../../docs/09-versions/v6.7.md) — версия 6.7

# PostSender — Контекст

**Последнее обновление:** 7 апреля 2026
**Версия:** 6.9

---

## 📋 Что это

Сервис отправки постов в темы групп. Простая отправка: HTML текст + превью + кнопка.

---

## 🎯 Ключевые файлы

| Файл | Назначение |
|------|------------|
| `core/services/monitoring/post_sender.py` | **Основной класс** `PostSender` (~310 строк) |
| `core/utils/html_sanitizer.py` | HTML санитизация |
| `core/services/monitoring/telegram_monitor.py` | Вызывает `send_to_assignment()` |

---

## ⚙️ Как работает (v6.9)

### Простой flow
```
send_to_assignment()
  ↓
HTML текст + кнопка + превью
  ↓
bot.send_message()
```

### Превью
```python
_get_link_preview_options(post, source):
  Есть медиа? → LinkPreviewOptions(url="t.me/...", prefer_large_media=True, show_above_text=True)
  Нет медиа?  → LinkPreviewOptions(is_disabled=True)
```

---

## ⚠️ Важные решения

| Версия | Решение | Причина |
|--------|---------|---------|
| **6.9** | Удалено скачивание медиа | Не нужно — превью работает через LinkPreviewOptions |
| **6.9** | Удалены fallback приоритеты | Упрощение — один метод вместо трёх |
| **6.9** | Удалены альбомы | Не поддерживаются в Bot API без file_id |
| **6.9** | LinkPreviewOptions | Умное превью постов с медиа |
| **6.9** | Кнопка с названием канала | "📢 TechCrunch" вместо "Открыть оригинал" |
| **6.7** | HTML вместо plain text | Сохранение форматирования |
| **6.7** | Inline кнопка | Вместо ссылки в тексте |

---

## 🔗 Связанные документы

- [`../../docs/09-versions/v6.7.md`](../../docs/09-versions/v6.7.md) — версия 6.7
- [`../../docs/09-versions/v6.9.md`](../../docs/09-versions/v6.9.md) — версия 6.9

# Блокировка источников — Контекст

**Последнее обновление:** 2026-04-08
**Версия:** 6.9.1+

---

## 📋 Что это

Механизм блокировки источников по просьбе автора контента (Telegram/YouTube)
с верификацией авторства через публикацию кода в канале.

---

## 🎯 Ключевые файлы

- `core/models/sources.py` — поля `is_blocked`, `blocked_reason`, `verification_code`
- `core/services/monitoring/base.py` — проверка в `_check_single_source()`
- `bot/handlers/sources/add_channel.py` — проверка при добавлении
- `scripts/block_source.py` — скрипт блокировки (показывает код для сверки)
- `scripts/generate_verification_code.py` — генерация кода верификации

---

## 🔄 Flow верификации и блокировки

```
Автор пишет @: "Заблокируйте мой канал"
  ↓
Разработчик генерирует код:
  python scripts/generate_verification_code.py username
  → VRF-A3KX9P
  ↓
Разработчик отправляет код автору с инструкцией:
  "Разместите код в описании канала (bio) или постом"
  ↓
Автор размещает код одним из способов:
  1. В описании канала (bio) — временно, на 5 минут ✅
  2. Или публикует постом в канале ✅
  ↓
Разработчик видит код → запускает:
  python scripts/block_source.py username
  → Скрипт показывает ожидаемый код
  ↓
Разработчик сверяет код → подтверждает (y/N)
  ↓
is_blocked=True, подписки удалены (CASCADE)
  ↓
Автор убирает код из bio/поста
```

### ⚡ Два способа верификации:

| Способ | Плюсы | Минусы |
|--------|-------|--------|
| **Описание канала (bio)** | Быстро, не спамит подписчикам | Нужно зайти в настройки |
| **Пост в канале** | Привычнее, виден всем | Спамит подписчикам |

---

## 🗄️ БД

```python
ContentSource.is_blocked: bool           # default=False
ContentSource.blocked_reason: str|None   # 'author_request', 'dmca', 'tos_violation'
ContentSource.verification_code: str|None  # 'VRF-XXXXXX'
```

**Миграции:**
- `2026_04_07_add_blocked_fields.py` — is_blocked, blocked_reason
- `2026_04_08_add_verification_code.py` — verification_code

---

## ⚠️ Важные решения

- **Только разработчик** — нет команды `/block` в боте
- **Верификация кодом** — автор публикует код (доказательство авторства)
- **Сохраняем запись** — `ContentSource` не удаляется (для учёта)
- **Каскадное удаление** — подписки и назначения удаляются автоматически
- **Локализация** — сообщение на 4 языках (ru, en, uk, be)

---

## 🔗 Связанные документы

- `docs/09-versions/v6.9.1.md` — версия
- `docs/legal/terms-privacy.md` — пункт о блокировке
- `scripts/block_source.py` — скрипт блокировки
- `scripts/generate_verification_code.py` — генерация кода

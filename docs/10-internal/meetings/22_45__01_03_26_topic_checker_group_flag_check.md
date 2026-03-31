# Промпт для Qwen Code: Проверка флага группы в topic_checker

**Время:** 22:45  
**Дата:** 01.03.2026  
**Проект:** MyAggryBot v5.4  
**Файл для изменения:** `core/utils/topic_checker.py`

---

## 🎯 Задача (ОДНА)

Добавить проверку `is_bot_active_in_group` перед проверкой топика, чтобы не проверять топики в группах, из которых бот удалён.

---

## 📋 Контекст

**Проблема:**
- Пользователь удалил группу в Telegram
- `topic_checker` при вызове (`/list`, `/add`, `/mytopics`) пытается проверить топик
- Получает ошибку: `Forbidden: bot was kicked from the supergroup chat`
- Ошибка логируется, но проверка продолжается при следующем вызове

**Решение:**
1. Перед проверкой топика → проверить `ManagedGroup.is_bot_active_in_group`
2. Если `False` → пропустить проверку, залогировать INFO
3. При ошибке "bot was kicked" → немедленно обновить флаг в БД

**Без кэша. Только БД.**

---

## 🔧 Что изменить в `verify_user_topics()`

### Шаг 1: Получить группы с флагом активности

```python
# Вместо простого get_user_topics_for_verification
# Добавить JOIN с ManagedGroup и фильтр is_bot_active_in_group == True
```

### Шаг 2: Пропускать неактивные группы

```python
# Перед check_topic_live:
if not group.is_bot_active_in_group:
    logger.info(f"⏭️ Пропущена тема {topic.topic_identifier}: группа {chat_id} неактивна")
    continue
```

### Шаг 3: Обновлять флаг при ошибке "bot kicked"

```python
# В check_topic_live, при обработке TelegramBadRequest:
if "bot was kicked" in str(e).lower():
    # Пометить группу неактивной в БД
    await session.execute(
        update(ManagedGroup)
        .where(ManagedGroup.telegram_chat_id == chat_id)
        .values(is_bot_active_in_group=False, last_seen_at=func.now())
    )
    await session.commit()
    logger.info(f"🚫 Группа {chat_id} помечена неактивной: bot kicked")
    return False
```

---

## 📁 Импорт, который может понадобиться

```python
from sqlalchemy import update, func
from core.models import ManagedGroup
```

---

## ✅ Критерии приёмки

- [ ] Топики в неактивных группах (`is_bot_active_in_group=False`) не проверяются
- [ ] Топики, помеченные удалёнными (`is_exists_in_tg=False`), не проверяются
- [ ] При ошибке "bot was kicked" → флаг `is_bot_active_in_group` ставится в `False` в БД
- [ ] Логирование: INFO для пропуска, INFO для обновления флага
- [ ] Нет изменений в других файлах (только `topic_checker.py`)
- [ ] Нет JSON-кэша, только БД

---

## 🧪 Тестирование (ручное)

1. Удалить группу с ботом в Telegram
2. Нажать `/list` у пользователя-создателя
3. Ожидать: лог "⏭️ Пропущена тема..." или "🚫 Группа... помечена неактивной"
4. Повторный `/list` → без ошибок "bot was kicked"

---

## ⚠️ Важно

- Не менять сигнатуры функций
- Не добавлять новые зависимости
- Сохранить асинхронную проверку через `asyncio.gather()`
- Коммитить изменения в БД только при необходимости (если флаг изменился)

---

## 📝 Имя файла для сохранения промпта

`22_45__01_03_26_topic_checker_group_flag_check.md`

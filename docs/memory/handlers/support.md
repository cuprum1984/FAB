# 💎 Support (Donations) — Хендлеры пожертвований

**Последнее обновление:** 2 апреля 2026
**Версия:** 6.5
**Статус:** ✅ Актуальная

---

## 📋 Что это

Система добровольных пожертвований автору через **Telegram Stars**.

**Путь пользователя:**
```
Настройки → 💎 Поддержать автора → Выбор суммы → Invoice → Оплата → Спасибо
```

---

## 🎯 Ключевые файлы

| Файл | Назначение |
|------|------------|
| `bot/handlers/support.py` | Хендлеры обработки донатов |
| `bot/keyboards/support.py` | Inline-клавиатуры для меню поддержки |

---

## ⚙️ Как работает

### 1. Вход в меню поддержки

**Callback:** `settings_support`

**Хендлер:** `on_support_menu()`

**Логика:**
- Обновляет текущее сообщение меню (тот же `message_id`)
- Показывает кнопки сумм (100, 250, 500, 2500 ⭐)
- Кнопки навигации: "⚙️ В настройки", "◀️ В главное меню"

---

### 2. Выбор суммы → Invoice

**Callback:** `support_100`, `support_250`, `support_500`, `support_2500`

**Хендлер:** `on_support_select()`

**Логика:**
1. Сохраняет сумму в состоянии (`donate_amount`)
2. Сохраняет `message_id` меню для удаления (`donate_message_id`)
3. Выставляет Invoice через `bot.send_invoice()`:
   - `provider_token=""` (пусто для Stars)
   - `currency="XTR"` (валюта Stars)
   - `prices=[LabeledPrice(label="Stars", amount=star_count)]`

---

### 3. Pre-checkout

**Событие:** `pre_checkout_query`

**Хендлер:** `on_pre_checkout()`

**Логика:**
- Всегда подтверждает (`query.answer(ok=True)`)
- Нет причин для отказа

---

### 4. Успешная оплата ⭐

**Событие:** `message.successful_payment`

**Хендлер:** `on_success_payment()`

**Логика:**
1. Получает `donate_message_id` из состояния
2. **Удаляет** старое сообщение меню донатов
3. Отправляет сообщение с благодарностью
4. Через 2 секунды → **новое главное меню** (новый `message_id`)
5. Сохраняет новый `message_id` в состоянии
6. Очищает состояние

---

### 5. Навигация

#### Возврат в настройки

**Callback:** `support_settings`

**Хендлер:** `on_support_settings()`

**Логика:**
1. Сохраняет `message_id` перед изменением состояния
2. Получает язык пользователя из БД
3. Обновляет сообщение → меню настроек
4. Восстанавливает `message_id` в состоянии

---

#### Возврат в главное меню

**Callback:** `support_back`

**Хендлер:** `on_support_back()`

**Логика:**
1. Сохраняет `message_id` перед очисткой
2. Обновляет сообщение → главное меню
3. Очищает состояние
4. Восстанавливает `message_id` в состоянии

**Важно:** `message_id` сохраняется для последующей навигации!

---

## 💰 Суммы донатов

| Кнопка | Stars | ~USD | Callback |
|--------|-------|------|----------|
| 💎 100 ⭐ | 100 | $2 | `support_100` |
| 💎💎 250 ⭐ | 250 | $5 | `support_250` |
| 💎💎💎 500 ⭐ | 500 | $10 | `support_500` |
| 👑 2500 ⭐ | 2500 | $50 | `support_2500` |

---

## ⚠️ Важные решения

### v6.5 (2 апреля 2026)

**Проблема:** При выходе из меню поддержки сбрасывался `message_id`, создавались новые сообщения.

**Решение:** Сохранять `message_id` перед `state.clear()` и восстанавливать после:

```python
# Сохраняем
data = await state.get_data()
menu_message_id = data.get(MENU_MESSAGE_ID_KEY)

# ... update_or_send_menu ...

# Восстанавливаем
await state.clear()
if menu_message_id:
    await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})
```

---

**Проблема:** `support.router` перехватывался `debug_callbacks` из `settings_handler`.

**Решение:** 
1. Подключить `support.router` **раньше** `settings_handler.router`
2. Добавить `settings_support` в исключения `debug_callbacks`

---

**Проблема:** Хендлер `F.data.startswith("support_")` перехватывал `support_settings` и `support_back`.

**Решение:** Использовать точный фильтр:
```python
@router.callback_query(F.data.in_({"support_100", "support_250", "support_500", "support_2500"}))
```

---

## 🔗 Связанные документы

- [`bot/handlers/support.py`](../../bot/handlers/support.py) — исходный код
- [`bot/keyboards/support.py`](../../bot/keyboards/support.py) — клавиатуры
- [`bot/utils/menu_message.py`](../../bot/utils/menu_message.py) — управление сообщениями
- [`docs/memory/keyboards/menu_system.md`](../keyboards/menu_system.md) — система меню
- [Telegram Stars Docs](https://core.telegram.org/bots/payments-stars) — официальная документация

---

## 📋 Запланировано (v6.6)

| Файл | Назначение |
|------|------------|
| `bot/handlers/payment_info.py` | Команды `/terms`, `/support`, `/donate` |

**Причина:** Требование Telegram — боты с платежами должны иметь условия использования и контакты поддержки.

---

## 📊 Статистика

| Метрика | Значение |
|---------|----------|
| Хендлеров | 6 |
| Callback'ов | 7 |
| Сумм донатов | 4 |
| Строк кода | ~230 |

---

**Версия:** 6.5 (2 апреля 2026)

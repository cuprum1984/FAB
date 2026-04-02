# 📞 Payment Info — Команды платежей

**Последнее обновление:** 2 апреля 2026
**Версия:** 6.5
**Статус:** ✅ Актуальная

---

## 📋 Что это

Обязательная информация о платежах (требование Telegram).

**Требование:** Все боты с платежами должны иметь:
1. Условия использования (`/terms`)
2. Контакты поддержки (`/support`)

---

## 🎯 Ключевые файлы

| Файл | Назначение |
|------|------------|
| `bot/handlers/payment_info.py` | Хендлеры команд /terms, /support, /donate |

---

## ⚙️ Команды

### 1. `/terms` — Условия использования

**Хендлер:** `cmd_terms()`

**Содержание:**
1. Добровольные пожертвования
2. Возврат средств (14 дней)
3. Комиссии (Telegram 30%)
4. Вывод средств (21 день в TON)
5. Поддержка: `/support`

**Формат:** HTML

---

### 2. `/support` — Контакты поддержки

**Хендлер:** `cmd_support()`

**Контакт:** `@m84show`

**Содержание:**
- Контакт для связи
- Время ответа: 24-48 часов
- Примечание: поддержка Telegram не помогает с покупками в боте

---

### 3. `/paysupport` — Альтернатива `/support`

**Хендлер:** `cmd_paysupport()`

**Назначение:** Дополнительная команда (требование Telegram)

**Логика:** Перенаправляет на `cmd_support()`

---

### 4. `/donate` — Прямой переход к донатам

**Хендлер:** Перенаправляет в `support.on_support_menu()`

**Назначение:** Быстрый доступ к меню донатов без навигации через настройки

---

## 🔗 Команды в меню бота

**Добавлены в `bot/main.py`:**

### Русский язык:
```python
BotCommand(command="donate", description="💎 Поддержать автора"),
BotCommand(command="support", description="📞 Поддержка"),
BotCommand(command="terms", description="📄 Условия"),
```

### English:
```python
BotCommand(command="donate", description="💎 Support author"),
BotCommand(command="support", description="📞 Support"),
BotCommand(command="terms", description="📄 Terms"),
```

---

## ⚠️ Важные решения

### v6.5 (2 апреля 2026)

**Решение:** Создать отдельный роутер `payment_info.py` для команд.

**Почему:**
- Требование Telegram для ботов с платежами
- Логическое разделение: донаты vs информация
- Упрощение тестирования и поддержки

---

## 🔗 Связанные документы

- [`bot/handlers/payment_info.py`](../../bot/handlers/payment_info.py) — исходный код
- [`bot/handlers/support.py`](../../bot/handlers/support.py) — хендлеры донатов
- [`docs/memory/handlers/support.md`](support.md) — донаты
- [Telegram Stars Docs](https://core.telegram.org/bots/payments-stars) — официальная документация

---

## 📊 Статистика

| Метрика | Значение |
|---------|----------|
| Команд | 4 (/terms, /support, /paysupport, /donate) |
| Хендлеров | 3 |
| Строк кода | ~80 |

---

**Версия:** 6.5 (2 апреля 2026)

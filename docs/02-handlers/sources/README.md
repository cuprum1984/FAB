# 📡 Добавление источников

**Папка:** `bot/handlers/sources/`

---

## 📋 Обзор

Модуль для добавления источников (Telegram каналы, YouTube каналы).

**Команда:** `/add`

---

## 📁 Структура

| Файл | Описание |
|------|----------|
| [`add_channel.md`](add_channel.md) | `/add` — начало процесса |
| [`telegram.md`](telegram.md) | Добавление Telegram каналов |
| [`youtube.md`](youtube.md) | Добавление YouTube каналов |
| [`destination.md`](destination.md) | Выбор назначения (группа/тема) |
| [`group_select.md`](group_select.md) | Выбор группы |
| [`finalize.md`](finalize.md) | Завершение добавления |
| [`cancel.md`](cancel.md) | Отмена процесса |
| [`list.md`](list.md) | Просмотр списка источников |

---

## 🔄 Процесс добавления

```
/add
  ↓
[Выбор типа источника]
  ├─→ Telegram → Ввод username → Проверка → Подтверждение
  └─→ YouTube → Ввод URL/канала → Проверка → Подтверждение
  ↓
[Выбор группы]
  ↓
[Выбор темы]
  ↓
[Подтверждение]
  ↓
[Сохранение в БД]
```

---

## 🎯 FSM состояния

Состояния определены в `bot/states.py`:

```python
class AddChannel(StatesGroup):
    waiting_for_username = State()  # Ожидание username/ссылки
    confirm_channel = State()       # Подтверждение добавления
    choose_group = State()          # Выбор группы
    choose_destination = State()    # Выбор темы в группе
    edit_title = State()            # Редактирование названия
```

---

## 🔁 Callback-префиксы

| Префикс | Файл | Назначение |
|---------|------|------------|
| `add_` | `add_channel.py` | Начало добавления |
| `tg_` | `telegram_handlers.py` | Telegram каналы |
| `yt_` | `youtube_handlers.py` | YouTube каналы |
| `dest_` | `destination_handlers.py` | Выбор назначения |
| `group_` | `group_select_handlers.py` | Выбор группы |
| `final_` | `finalize_handlers.py` | Завершение |
| `cancel_` | `cancel_handlers.py` | Отмена |

---

## 🗂️ Общие зависимости

| Модуль | Назначение |
|--------|------------|
| `bot.keyboards.*` | Клавиатуры для каждого этапа |
| `bot.utils.menu_message.update_or_send_menu` | Управление сообщением |
| `core.models.*` | Модели БД |
| `core.services.destination_service` | Сервис назначений |

---

## ⚠️ Особенности

1. **Пошаговый процесс:** FSM для каждого этапа
2. **Валидация:** Проверка корректности username/URL
3. **Inline-only:** Только inline-клавиатуры (с v5.7)
4. **Отмена:** Возможность отмены на любом этапе

---

## 🔗 Связанные документы

- [`../README.md`](../README.md) — Обзор хендлеров
- [`../../03-keyboards/sources.py`](../../03-keyboards/sources.py) — Клавиатуры источников
- [`../../04-services/destinations.md`](../../04-services/destinations.md) — Destination Service

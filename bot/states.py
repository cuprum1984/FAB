# bot/states.py
from aiogram.fsm.state import State, StatesGroup

class AddChannel(StatesGroup):
    """Состояния для добавления канала"""
    waiting_for_username = State()  # Ожидание ввода username/ссылки
    confirm_channel = State()       # Подтверждение добавления
    choose_destination = State()    # Выбор группы/темы
    edit_title = State()            # Редактирование названия (опционально)


class SetOutput(StatesGroup):
    waiting_for_forwarded_message = State()  # ожидание пересланного сообщения из группы


class AdminPanel(StatesGroup):
    main          = State()               # основное меню админ-панели
    add_group     = State()               # добавление/выбор группы
    manage_groups = State()                # Управление группами
    manage_topics = State()                # управление темами в выбранной группе
    group_selected = State()               # Выбрана конкретная группа
    topic_selected = State()               # Выбрана конкретная тема
    waiting_for_topic_name = State()       # Ожидание названия темы
    confirm_action = State()               # Подтверждение действия


# ⚠️ Класс больше НЕ ИСПОЛЬЗУЕТСЯ, но оставляем для обратной совместимости
class TopicRegistration(StatesGroup):
    waiting_for_name = State()  # УСТАРЕЛО - не используется


class AddRSS(StatesGroup):
    """Состояния для добавления RSS ленты"""
    waiting_for_url = State()        # Ожидание ввода URL
    confirm_feed = State()           # Подтверждение
    choose_destination = State()     # Выбор группы/темы


class Settings(StatesGroup):
    """Состояния для настроек пользователя"""
    main = State()                     # Главное меню настроек
    language = State()                  # Выбор языка
    icons = State()                     # Выбор стиля иконок
    notifications = State()              # Настройки уведомлений
    confirm_delete = State()             # Подтверждение удаления данных
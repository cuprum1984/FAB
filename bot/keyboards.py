# bot/keyboards.py
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
)


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню - 3 ряда для iPhone"""
    builder = ReplyKeyboardBuilder()
    
    # Первый ряд: Добавить канал и Мои источники
    builder.row(
        KeyboardButton(text="📥 Добавить канал"),
        KeyboardButton(text="📚 Мои источники"),
        width=2
    )
    
    # Второй ряд: Моя лента и Настройки
    builder.row(
        KeyboardButton(text="📰 Моя лента"),
        KeyboardButton(text="⚙️ Настройки"),
        width=2
    )
    
    # Третий ряд: Админ-панель, Помощь и Обновить
    builder.row(
        KeyboardButton(text="👨‍💼 Админ-панель"),
        KeyboardButton(text="❓ Помощь"),
        KeyboardButton(text="🔄 Обновить"),
        width=3
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
        is_persistent=True,
    )



def get_admin_panel_menu() -> ReplyKeyboardMarkup:
    """Клавиатура админ-панели - 3 ряда"""
    builder = ReplyKeyboardBuilder()
    
    # Первый ряд: Управление группами
    builder.row(
        KeyboardButton(text="👥 Управление группами"),
        width=1
    )
    
    # Второй ряд: Управление темами и Статистика
    builder.row(
        KeyboardButton(text="🗂️ Управление темами"),
        KeyboardButton(text="📊 Статистика"),
        width=2
    )
    
    # Третий ряд: Мониторинг и Назад
    builder.row(
        KeyboardButton(text="🔍 Мониторинг"),
        KeyboardButton(text="← Назад"),
        width=2
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Админ действия...",
        is_persistent=True,
    )


def get_groups_menu(groups: list[dict]) -> ReplyKeyboardMarkup:
    """Меню выбора групп"""
    builder = ReplyKeyboardBuilder()
    
    for i, group in enumerate(groups, 1):
        emoji = "✅" if group.get("is_active", True) else "❌"
        display = f"{emoji} {i}. {group['chat_title']}"
        builder.add(KeyboardButton(text=display))
    
    builder.row(KeyboardButton(text="➕ Добавить группу"), width=1)
    builder.row(
        KeyboardButton(text="← Назад"),
        KeyboardButton(text="🏠 Главное меню"),
        width=2
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите группу...",
        is_persistent=False,
    )

def get_destinations_menu(destinations: list[dict]) -> ReplyKeyboardMarkup:
    """Меню выбора назначений (групп/тем)"""
    if not destinations:
        return get_cancel_kb_reply()
    
    print("🔥 Создаю кнопки для выбора темы:")
    
    builder = ReplyKeyboardBuilder()
    
    for dest in destinations:
        # Определяем эмодзи
        if dest.get("is_general", False):
            emoji = "💬"  # General тема
        elif dest.get("thread_id") is not None:
            emoji = "🗨️"  # Обычная тема
        else:
            emoji = "👥"  # Группа без темы
        
        # БЕРЁМ display_name КАК ЕСТЬ, БЕЗ ИЗМЕНЕНИЙ
        display_name = dest['display_name']
        
        # Сохраняем оба варианта в данных для отладки
        print(f"  dest: {dest}")
        print(f"  display_name: '{display_name}'")
        
        # Создаём кнопку с эмодзи + название
        button_text = f"{emoji} {display_name}"
        print(f"  button_text: '{button_text}'")
        
        builder.add(KeyboardButton(text=button_text))
    
    # Кнопки действий
    builder.row(KeyboardButton(text="────────────"))
    builder.row(
        KeyboardButton(text="❌ Отмена"),
        KeyboardButton(text="🔄 Обновить список")
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Куда отправлять посты?...",
        is_persistent=False,
        row_width=1
    )


def get_cancel_kb_reply() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с кнопкой отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_back_to_main_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для возврата в главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_confirm_channel_kb() -> InlineKeyboardMarkup:
    """Подтверждение добавления канала (инлайн)"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, добавить", callback_data="confirm_add_channel"),
        InlineKeyboardButton(text="✏️ Изменить название", callback_data="edit_channel_title")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_add_channel")
    )
    return builder.as_markup()


def get_cancel_kb() -> InlineKeyboardMarkup:
    """Инлайн кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add_channel"))
    return builder.as_markup()


##########################

def get_settings_menu() -> ReplyKeyboardMarkup:
    """Меню настроек"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="🌐 Язык / Language"),
        width=1
    )
    builder.row(
        KeyboardButton(text="🗑️ Удалить мои данные"),
        width=1
    )
    builder.row(
        KeyboardButton(text="← Назад"),
        width=1
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Настройки...",
        is_persistent=True,
    )


def get_language_menu() -> InlineKeyboardMarkup:
    """Инлайн клавиатура для выбора языка"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="404", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="back_to_settings"),
        width=1
    )
    
    return builder.as_markup()


def get_back_to_settings_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в настройки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="← Назад в настройки", callback_data="back_to_settings")
    )
    return builder.as_markup()


def get_confirm_delete_kb() -> InlineKeyboardMarkup:
    """Подтверждение удаления данных"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ ДА, удалить всё", callback_data="confirm_delete"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="❌ НЕТ, отмена", callback_data="cancel_delete"),
        width=1
    )
    return builder.as_markup()

######################


def get_source_list_kb(sources: list[dict], page: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    """Инлайн клавиатура для списка источников с навигацией"""
    builder = InlineKeyboardBuilder()
    
    total_pages = (len(sources) + page_size - 1) // page_size
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_sources = sources[start_idx:end_idx]
    
    # Кнопки источников
    for source in page_sources:
        source_name = source.get('name', source.get('source_global_id', 'Без названия'))
        if len(source_name) > 20:
            source_name = source_name[:17] + "..."
        
        # Создаем РЯД из двух кнопок: источник и удалить
        builder.row(
            InlineKeyboardButton(
                text=f"📰 {source_name}",
                callback_data=f"view_source:{source['source_global_id']}"
            ),
            InlineKeyboardButton(
                text="❌ Удалить",
                callback_data=f"del_source:{source['source_global_id']}"
            )
        )
    
    # Навигационные кнопки
    nav_buttons = []
    
    # Кнопка "Назад"
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"src_page:{page-1}")
        )
    else:
        nav_buttons.append(
            InlineKeyboardButton(text="⏺️", callback_data="noop")  # пустышка
        )
    
    # Счетчик страниц
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )
    
    # Кнопка "Вперед"
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперед ▶️", callback_data=f"src_page:{page+1}")
        )
    else:
        nav_buttons.append(
            InlineKeyboardButton(text="⏺️", callback_data="noop")  # пустышка
        )
    
    builder.row(*nav_buttons)
    
    # Кнопка закрытия
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_sources"))
    
    return builder.as_markup()
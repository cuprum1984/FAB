# bot/keyboards.py
from typing import Callable, Dict, Any, List, Optional
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
)

# Определяем тип для функции перевода
GetTextFunc = Callable[[List[str], Dict[str, Any]], str]


# bot/keyboards.py (добавь в начало get_main_menu)

def get_main_menu(get_text: GetTextFunc) -> ReplyKeyboardMarkup:
    """Главное меню - полностью исправленная версия"""
    import logging
    logger = logging.getLogger(__name__)
    builder = ReplyKeyboardBuilder()
    
    try:
        # Получаем тексты из локализации
        btn_add = get_text(['keyboards', 'main_menu', 'add_channel'])
        btn_sources = get_text(['keyboards', 'main_menu', 'my_sources'])
        btn_feed = get_text(['keyboards', 'main_menu', 'my_feed'])
        btn_settings = get_text(['keyboards', 'main_menu', 'settings'])
        btn_help = get_text(['keyboards', 'main_menu', 'help'])
        btn_refresh = get_text(['keyboards', 'main_menu', 'refresh'])
        #btn_admin_panel = get_text(['keyboards', 'main_menu', 'admin_panel'])
        placeholder = get_text(['keyboards', 'main_menu', 'placeholder'])
    except Exception as e:
        logger.error(f"Ошибка локализации меню: {e}")
        # Запасной вариант (Fallback)
        btn_add, btn_sources = "✚ Добавить", "📚 Источники"
        btn_feed = "📰 Лента"
        btn_settings, btn_help = "⚙️ Настройки", "❓ Помощь"
        #btn_admin_panel = "👨‍💼 Админ-панель"
        btn_refresh = "🔄 Обновить"
        placeholder = "Выберите действие..."

    # Строим сетку кнопок
    builder.row(KeyboardButton(text=btn_add), KeyboardButton(text=btn_sources))
    builder.row(KeyboardButton(text=btn_feed), KeyboardButton(text=btn_help))
    builder.row(KeyboardButton(text=btn_settings), KeyboardButton(text=btn_refresh)) #KeyboardButton(text=btn_admin_panel)

    # .as_markup() ОБЯЗАТЕЛЬНО должен быть с resize_keyboard=True
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder=placeholder,
        selective=True
    )

def get_admin_panel_menu(get_text: GetTextFunc) -> ReplyKeyboardMarkup:
    """Клавиатура админ-панели - 3 ряда"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(KeyboardButton(text=get_text(['keyboards', 'admin_menu', 'manage_groups'])))
    builder.row(
        KeyboardButton(text=get_text(['keyboards', 'admin_menu', 'manage_topics'])),
        KeyboardButton(text=get_text(['keyboards', 'admin_menu', 'statistics']))
    )
    builder.row(
        KeyboardButton(text=get_text(['keyboards', 'admin_menu', 'monitoring'])),
        KeyboardButton(text=get_text(['keyboards', 'admin_menu', 'back']))
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder=get_text(['keyboards', 'admin_menu', 'placeholder']),
        is_persistent=True,
    )


def get_groups_menu(groups: List[dict], get_text: GetTextFunc) -> ReplyKeyboardMarkup:
    """Меню выбора групп"""
    builder = ReplyKeyboardBuilder()
    
    active_prefix = get_text(['keyboards', 'groups_menu', 'active_prefix'])
    inactive_prefix = get_text(['keyboards', 'groups_menu', 'inactive_prefix'])
    
    # Добавляем кнопки групп
    for i, group in enumerate(groups, 1):
        emoji = active_prefix if group.get("is_active", True) else inactive_prefix
        display = f"{emoji} {i}. {group['chat_title']}"
        builder.add(KeyboardButton(text=display))
    
    # Добавляем кнопки управления
    builder.row(KeyboardButton(text=get_text(['keyboards', 'groups_menu', 'add_group'])))
    builder.row(
        KeyboardButton(text=get_text(['keyboards', 'groups_menu', 'back'])),
        KeyboardButton(text=get_text(['keyboards', 'main_menu_title']))
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder=get_text(['keyboards', 'groups_menu', 'placeholder']),
        is_persistent=False,
    )


def get_destinations_menu(destinations: List[dict], get_text: GetTextFunc) -> ReplyKeyboardMarkup:
    """Меню выбора назначений (групп/тем) - Reply клавиатура с одной кнопкой 'Отмена'"""
    builder = ReplyKeyboardBuilder()

    # Оставляем только кнопку отмены
    builder.row(KeyboardButton(text=get_text(['keyboards', 'destinations', 'cancel'])))

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder=get_text(['keyboards', 'destinations', 'placeholder']),
        is_persistent=False,
    )


def get_destinations_inline_kb(
    destinations: List[dict],
    page: int = 0,
    page_size: int = 10,
    get_text: Optional[GetTextFunc] = None
) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для выбора destinations с пагинацией и группировкой по группам.
    
    Структура:
    - Группы сортируются по названию
    - Внутри каждой группы сначала General, потом топики
    - Пагинация по количеству групп (не destinations)
    """
    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            fallback_text = {
                'dest_select': '📍 {name}',
                'prev': '◀️ Назад',
                'next': 'Вперед ▶️',
                'cancel': '❌ Отмена',
                'noop': '⏺️'
            }.get(keys[-1], keys[-1])
            return fallback_text

    # Группируем destinations по chat_id
    grouped: Dict[int, Dict] = {}
    for dest in destinations:
        chat_id = dest["chat_id"]
        if chat_id not in grouped:
            grouped[chat_id] = {
                "chat_title": dest["chat_title"],
                "items": []
            }
        grouped[chat_id]["items"].append(dest)

    # Сортируем группы по названию
    sorted_groups = sorted(grouped.items(), key=lambda x: x[1]["chat_title"] or "")

    # Сортируем внутри каждой группы: сначала General, потом топики по названию
    for chat_id, group_data in sorted_groups:
        group_data["items"].sort(key=lambda x: (
            0 if x.get("is_general", False) else 1,  # General первым
            x["thread_name"] or ""
        ))

    # Пагинация по группам
    total_pages = max(1, len(sorted_groups))
    page = max(0, min(page, total_pages - 1))
    
    # Получаем группы для текущей страницы
    page_groups = [sorted_groups[page]] if sorted_groups else []

    builder = InlineKeyboardBuilder()

    # Кнопки для каждой группы и её топов
    for chat_id, group_data in page_groups:
        # Заголовок группы (не кликабельный)
        chat_title = group_data["chat_title"] or f"Группа {chat_id}"
        
        # Добавляем кнопки для каждого destination в группе
        for dest in group_data["items"]:
            # Формируем отображаемое имя
            if dest.get("is_general", False):
                display_name = f"💬 {chat_title} → General"
            else:
                display_name = f"🗨️ {chat_title} → {dest['thread_name']}"
            
            # Ограничиваем длину
            if len(display_name) > 40:
                display_name = display_name[:37] + "..."
            
            topic_identifier = dest["topic_identifier"]
            builder.row(
                InlineKeyboardButton(
                    text=display_name,
                    callback_data=f"dest_select:{topic_identifier}"
                )
            )

    # Навигационные кнопки
    nav_buttons = []
    
    prev_text = get_text(['keyboards', 'destinations_inline', 'prev'])
    next_text = get_text(['keyboards', 'destinations_inline', 'next'])
    cancel_text = get_text(['keyboards', 'destinations', 'cancel'])
    noop_text = get_text(['keyboards', 'destinations_inline', 'noop'])
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=prev_text, callback_data=f"dest_page:{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=noop_text, callback_data="noop"))
    
    page_indicator = f"{page + 1}/{total_pages}"
    nav_buttons.append(InlineKeyboardButton(text=page_indicator, callback_data="noop"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=next_text, callback_data=f"dest_page:{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=noop_text, callback_data="noop"))
    
    builder.row(*nav_buttons)
    
    # Кнопка отмены в конце
    builder.row(
        InlineKeyboardButton(text=cancel_text, callback_data="cancel_add_channel")
    )

    return builder.as_markup()


def get_cancel_kb_reply(get_text: GetTextFunc) -> ReplyKeyboardMarkup:
    """Reply-клавиатура с кнопкой отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text(['keyboards', 'cancel']))]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_back_to_main_kb(get_text: GetTextFunc) -> ReplyKeyboardMarkup:
    """Клавиатура для возврата в главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text(['keyboards', 'main_menu_title']))]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_settings_menu(get_text: GetTextFunc) -> ReplyKeyboardMarkup:
    """Меню настроек"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(KeyboardButton(text=get_text(['keyboards', 'settings_menu', 'language'])))
    builder.row(KeyboardButton(text=get_text(['keyboards', 'settings_menu', 'delete_data'])))
    builder.row(KeyboardButton(text=get_text(['keyboards', 'settings_menu', 'back'])))
    
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder=get_text(['keyboards', 'settings_menu', 'placeholder']),
        is_persistent=True,
    )


# ========== INLINE KEYBOARDS ==========

def get_confirm_channel_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Подтверждение добавления канала (инлайн)"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=get_text(['keyboards', 'confirm_add']), callback_data="confirm_add_channel"),
        InlineKeyboardButton(text=get_text(['keyboards', 'edit_title']), callback_data="edit_channel_title")
    )
    builder.row(
        InlineKeyboardButton(text=get_text(['keyboards', 'cancel_add']), callback_data="cancel_add_channel")
    )
    return builder.as_markup()


def get_cancel_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Инлайн кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'cancel']), 
            callback_data="cancel_add_channel"
        )
    )
    return builder.as_markup()


def get_language_menu(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Инлайн клавиатура для выбора языка"""
    builder = InlineKeyboardBuilder()

    # Используем локализацию для текстов кнопок
    ru_text = get_text(['keyboards', 'language_menu', 'ru'])
    en_text = get_text(['keyboards', 'language_menu', 'en'])
    uk_text = get_text(['keyboards', 'language_menu', 'uk'])
    be_text = get_text(['keyboards', 'language_menu', 'be'])
    back_text = get_text(['keyboards', 'language_menu', 'back'])

    builder.row(
        InlineKeyboardButton(text=ru_text, callback_data="set_lang:ru"),
        InlineKeyboardButton(text=en_text, callback_data="set_lang:en")
    )
    builder.row(
        InlineKeyboardButton(text=uk_text, callback_data="set_lang:uk"),
        InlineKeyboardButton(text=be_text, callback_data="set_lang:be")
    )

    builder.row(
        InlineKeyboardButton(
            text=back_text,
            callback_data="back_to_settings"
        )
    )

    return builder.as_markup()


def get_back_to_settings_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Кнопка возврата в настройки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'back_to_settings']), 
            callback_data="back_to_settings"
        )
    )
    return builder.as_markup()


def get_confirm_delete_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Подтверждение удаления данных"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'confirm_delete']), 
            callback_data="confirm_delete"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'cancel_delete']), 
            callback_data="cancel_delete"
        )
    )
    return builder.as_markup()


def get_source_list_kb(
    sources: List[dict], 
    page: int = 0, 
    page_size: int = 5, 
    get_text: Optional[GetTextFunc] = None
) -> InlineKeyboardMarkup:
    """Инлайн клавиатура для списка источников с навигацией"""
    builder = InlineKeyboardBuilder()
    
    # Если get_text не передан, используем заглушку с правильной сигнатурой
    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            # Пытаемся получить последний ключ как текст
            fallback_text = {
                'view_source': '📰 {name}',
                'delete': '❌ Удалить',
                'prev': '◀️ Назад',
                'next': 'Вперед ▶️',
                'close': '❌ Закрыть',
                'noop': '⏺️'
            }.get(keys[-1], keys[-1])
            return fallback_text
    
    view = get_text(['keyboards', 'sources_list', 'view_source'])
    delete = get_text(['keyboards', 'sources_list', 'delete'])
    prev = get_text(['keyboards', 'sources_list', 'prev'])
    next = get_text(['keyboards', 'sources_list', 'next'])
    close = get_text(['keyboards', 'sources_list', 'close'])
    noop = get_text(['keyboards', 'sources_list', 'noop'])
    
    total_pages = max(1, (len(sources) + page_size - 1) // page_size)
    page = min(page, total_pages - 1)
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(sources))
    page_sources = sources[start_idx:end_idx]
    
    # Кнопки источников
    for source in page_sources:
        source_name = source.get('name', source.get('source_global_id', 'Без названия'))
        if len(source_name) > 20:
            source_name = source_name[:17] + "..."
        
        builder.row(
            InlineKeyboardButton(
                text=view.format(name=source_name),
                callback_data=f"view_source:{source['source_global_id']}"
            ),
            InlineKeyboardButton(
                text=delete,
                callback_data=f"del_source:{source['source_global_id']}"
            )
        )
    
    # Навигационные кнопки
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=prev, callback_data=f"src_page:{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=noop, callback_data="noop"))
    
    page_text = f"{page+1}/{total_pages}"
    nav_buttons.append(InlineKeyboardButton(text=page_text, callback_data="noop"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=next, callback_data=f"src_page:{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=noop, callback_data="noop"))
    
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text=close, callback_data="close_sources"))
    
    return builder.as_markup()


# В конце файла bot/keyboards.py
__all__ = [
    'get_main_menu',
    'get_admin_panel_menu',
    'get_groups_menu',
    'get_destinations_menu',
    'get_destinations_inline_kb',
    'get_cancel_kb_reply',
    'get_back_to_main_kb',
    'get_settings_menu',
    'get_confirm_channel_kb',
    'get_cancel_kb',
    'get_language_menu',
    'get_back_to_settings_kb',
    'get_confirm_delete_kb',
    'get_source_list_kb',
    'GetTextFunc',
]
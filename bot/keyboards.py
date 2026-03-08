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
        btn_overview = get_text(['keyboards', 'main_menu', 'overview'])
        btn_settings = get_text(['keyboards', 'main_menu', 'settings'])
        btn_help = get_text(['keyboards', 'main_menu', 'help'])
        btn_refresh = get_text(['keyboards', 'main_menu', 'refresh'])
        #btn_admin_panel = get_text(['keyboards', 'main_menu', 'admin_panel'])
        placeholder = get_text(['keyboards', 'main_menu', 'placeholder'])
    except Exception as e:
        logger.error(f"Ошибка локализации меню: {e}")
        # Запасной вариант (Fallback)
        btn_add, btn_sources = "✚ Добавить", "📚 Источники"
        btn_overview = "📰 Обзор"
        btn_settings, btn_help = "⚙️ Настройки", "❓ Помощь"
        #btn_admin_panel = "👨‍💼 Админ-панель"
        btn_refresh = "🔄 Обновить"
        placeholder = "Выберите действие..."

    # Строим сетку кнопок
    builder.row(KeyboardButton(text=btn_add), KeyboardButton(text=btn_sources))
    builder.row(KeyboardButton(text=btn_overview), KeyboardButton(text=btn_help))
    builder.row(KeyboardButton(text=btn_settings), KeyboardButton(text=btn_refresh)) #KeyboardButton(text=btn_admin_panel)

    # .as_markup() ОБЯЗАТЕЛЬНО должен быть с resize_keyboard=True
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder=placeholder,
        selective=True
    )


def get_main_menu_inline(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Главное меню - InlineKeyboardMarkup"""
    import logging
    logger = logging.getLogger(__name__)
    builder = InlineKeyboardBuilder()

    try:
        # Получаем тексты из локализации
        btn_add = get_text(['keyboards', 'main_menu', 'add_channel'])
        btn_sources = get_text(['keyboards', 'main_menu', 'my_sources'])
        btn_overview = get_text(['keyboards', 'main_menu', 'overview'])
        btn_settings = get_text(['keyboards', 'main_menu', 'settings'])
        btn_help = get_text(['keyboards', 'main_menu', 'help'])
        btn_refresh = get_text(['keyboards', 'main_menu', 'refresh'])
    except Exception as e:
        logger.error(f"Ошибка локализации меню: {e}")
        # Запасной вариант (Fallback)
        btn_add, btn_sources = "✚ Добавить", "📚 Источники"
        btn_overview = "📰 Обзор"
        btn_settings, btn_help = "⚙️ Настройки", "❓ Помощь"
        btn_refresh = "🔄 Обновить"

    # Строим сетку кнопок 2x3
    builder.row(
        InlineKeyboardButton(text=btn_add, callback_data="menu_add"),
        InlineKeyboardButton(text=btn_sources, callback_data="menu_sources")
    )
    builder.row(
        InlineKeyboardButton(text=btn_overview, callback_data="menu_overview"),
        InlineKeyboardButton(text=btn_help, callback_data="menu_help")
    )
    builder.row(
        InlineKeyboardButton(text=btn_settings, callback_data="menu_settings"),
        InlineKeyboardButton(text=btn_refresh, callback_data="menu_refresh")
    )

    return builder.as_markup()


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


def get_admin_panel_menu_inline(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Админ-панель - InlineKeyboardMarkup"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'admin_menu', 'manage_groups']),
            callback_data="admin_groups"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'admin_menu', 'manage_topics']),
            callback_data="admin_topics"
        ),
        InlineKeyboardButton(
            text=get_text(['keyboards', 'admin_menu', 'statistics']),
            callback_data="admin_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'admin_menu', 'monitoring']),
            callback_data="admin_monitoring"
        ),
        InlineKeyboardButton(
            text=get_text(['keyboards', 'admin_menu', 'back']),
            callback_data="admin_back"
        )
    )

    return builder.as_markup()


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
    - ВСЕГДА показываются навигационные кнопки (с заглушками если нет prev/next)
    """
    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            fallback_text = {
                'dest_select': '📍 {name}',
                'prev': '◀️ Назад',
                'next': 'Вперед ▶️',
                'cancel': '❌ Отмена',
                'noop': '⏺️',
                'dot': '.'
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

    # ===== НАВИГАЦИОННЫЕ КНОПКИ - ВСЕГДА =====
    nav_buttons = []
    
    prev_text = get_text(['keyboards', 'destinations_inline', 'prev'])
    next_text = get_text(['keyboards', 'destinations_inline', 'next'])
    cancel_text = get_text(['keyboards', 'destinations', 'cancel'])
    dot_text = get_text(['keyboards', 'destinations_inline', 'dot'])
    
    # Кнопка "Назад" или заглушка
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=prev_text, callback_data=f"dest_page:{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot_text, callback_data="noop"))
    
    # Счетчик страниц (всегда)
    page_indicator = f"{page + 1}/{total_pages}"
    nav_buttons.append(InlineKeyboardButton(text=page_indicator, callback_data="noop"))
    
    # Кнопка "Вперед" или заглушка
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=next_text, callback_data=f"dest_page:{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot_text, callback_data="noop"))
    
    builder.row(*nav_buttons)
    
    # Кнопка отмены в конце
    builder.row(
        InlineKeyboardButton(text=cancel_text, callback_data="cancel_add_channel")
    )

    return builder.as_markup()


def get_groups_inline_kb(
    groups: List[dict],
    page: int = 0,
    page_size: int = 5,
    get_text: Optional[GetTextFunc] = None,
    back_callback: str = "back_to_main",
    mode: str = "list"  # "list" для просмотра, "add" для добавления канала
) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для выбора групп с пагинацией.

    Структура:
    - Группы сортируются по названию
    - ВСЕГДА показываются навигационные кнопки (с заглушками если нет prev/next)
    - Кнопка назад: "back_to_main" по умолчанию

    Args:
        groups: Список групп с полями chat_id, chat_title
        page: Текущая страница (0-based)
        page_size: Количество групп на странице
        get_text: Функция локализации
        back_callback: Callback_data для кнопки "Назад" (по умолчанию "back_to_main")
        mode: "list" для просмотра источников, "add" для добавления канала
    """
    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            fallback_text = {
                'group_select': '👥 {name}',
                'prev': '◀️ Назад',
                'next': 'Вперед ▶️',
                'cancel': '❌ Отмена',
                'noop': '⏺️',
                'dot': '.'
            }.get(keys[-1], keys[-1])
            return fallback_text

    # Сортируем группы по названию
    sorted_groups = sorted(groups, key=lambda x: x.get('chat_title', '') or '')

    # Пагинация
    total_pages = (len(sorted_groups) + page_size - 1) // page_size if sorted_groups else 1
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(sorted_groups))
    page_groups = sorted_groups[start_idx:end_idx]

    builder = InlineKeyboardBuilder()

    # Кнопки для каждой группы
    for group in page_groups:
        chat_id = group["chat_id"]
        chat_title = (group.get("chat_title") or f"Группа {chat_id}")[:30]
        
        # Разный callback_data для режима просмотра и добавления
        if mode == "add":
            callback_data = f"dest_group:{chat_id}"
        else:
            callback_data = f"list_group:{chat_id}"

        builder.row(
            InlineKeyboardButton(
                text=f"👥 {chat_title}",
                callback_data=callback_data
            )
        )

    # ===== НАВИГАЦИОННЫЕ КНОПКИ - ВСЕГДА =====
    nav_buttons = []

    prev_text = get_text(['keyboards', 'groups_menu', 'prev']) if get_text else '◀️ Назад'
    next_text = get_text(['keyboards', 'groups_menu', 'next']) if get_text else 'Вперед ▶️'
    cancel_text = get_text(['keyboards', 'groups_menu', 'cancel']) if get_text else '❌ Отмена'
    dot_text = get_text(['keyboards', 'groups_menu', 'dot']) if get_text else '.'

    # Кнопка "Назад" или заглушка
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=prev_text, callback_data=f"groups_page:{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot_text, callback_data="noop"))

    # Счетчик страниц (всегда)
    page_indicator = f"{page + 1}/{total_pages}"
    nav_buttons.append(InlineKeyboardButton(text=page_indicator, callback_data="noop"))

    # Кнопка "Вперед" или заглушка
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=next_text, callback_data=f"groups_page:{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot_text, callback_data="noop"))

    builder.row(*nav_buttons)

    # Кнопка назад в конце
    builder.row(
        InlineKeyboardButton(text=cancel_text, callback_data=back_callback)
    )

    return builder.as_markup()


def get_topics_inline_kb(
    topics: List[dict],
    group_title: str,
    page: int = 0,
    page_size: int = 5,
    get_text: Optional[GetTextFunc] = None,
    back_callback: str = "list_back:groups",
    mode: str = "list"  # "list" для просмотра, "add" для добавления канала
) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для выбора топиков с пагинацией.

    Структура:
    - Топики сортируются по названию (сначала General)
    - ВСЕГДА показываются навигационные кнопки (с заглушками если нет prev/next)
    - Две кнопки назад: "к группам" и "в главное меню"

    Args:
        topics: Список топиков с полями topic_name, topic_identifier, telegram_thread_id
        group_title: Название группы для отображения в заголовке
        page: Текущая страница (0-based)
        page_size: Количество топиков на странице
        get_text: Функция локализации
        back_callback: Callback_data для кнопки "Назад к группам"
        mode: "list" для просмотра источников, "add" для добавления канала
    """
    import hashlib

    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            fallback_text = {
                'topic_select': '🗨️ {name}',
                'prev': '◀️ Назад',
                'next': 'Вперед ▶️',
                'back': '← Назад',
                'back_to_main': '🔙 В главное меню',
                'noop': '⏺️',
                'dot': '.'
            }.get(keys[-1], keys[-1])
            return fallback_text

    # Сортируем топики: сначала General, потом остальные по названию
    sorted_topics = sorted(topics, key=lambda x: (
        0 if x.get('telegram_thread_id') is None else 1,  # General первым
        x.get('topic_name', '') or ''
    ))

    # Пагинация
    total_pages = (len(sorted_topics) + page_size - 1) // page_size if sorted_topics else 1
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(sorted_topics))
    page_topics = sorted_topics[start_idx:end_idx]

    builder = InlineKeyboardBuilder()

    # Заголовок с названием группы (не кликабельный)
    header_text = f"👥 Группа: {group_title[:30]}"

    # Кнопки для каждого топика
    for topic in page_topics:
        topic_name = (topic.get("topic_name") or "Без названия")[:30]
        # Короткий хеш (8 символов) для callback_data
        topic_hash = hashlib.md5(topic.get('topic_identifier', '').encode()).hexdigest()[:8]
        
        # Разный callback_data для режима просмотра и добавления
        if mode == "add":
            callback_data = f"dest_topic:{topic_hash}"
        else:
            callback_data = f"list_topic:{topic_hash}"

        builder.row(
            InlineKeyboardButton(
                text=f"🗨️ {topic_name}",
                callback_data=callback_data
            )
        )

    # ===== НАВИГАЦИОННЫЕ КНОПКИ - ВСЕГДА =====
    nav_buttons = []

    prev_text = get_text(['keyboards', 'topics_menu', 'prev']) if get_text else '◀️ Назад'
    next_text = get_text(['keyboards', 'topics_menu', 'next']) if get_text else 'Вперед ▶️'
    dot_text = get_text(['keyboards', 'topics_menu', 'dot']) if get_text else '.'

    # Разный callback_data для режима просмотра и добавления
    if mode == "add":
        page_prefix = "dest_topics_page"
    else:
        page_prefix = "topics_page"

    # Кнопка "Назад" или заглушка
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=prev_text, callback_data=f"{page_prefix}:{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot_text, callback_data="noop"))

    # Счетчик страниц (всегда)
    page_indicator = f"{page + 1}/{total_pages}"
    nav_buttons.append(InlineKeyboardButton(text=page_indicator, callback_data="noop"))

    # Кнопка "Вперед" или заглушка
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=next_text, callback_data=f"{page_prefix}:{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot_text, callback_data="noop"))

    builder.row(*nav_buttons)

    # ===== ДВЕ КНОПКИ НАЗАД =====
    back_groups_text = get_text(['keyboards', 'topics_menu', 'back']) if get_text else '🔙 К группам'
    back_main_text = get_text(['keyboards', 'back_to_main']) if get_text else '🔙 В главное меню'

    builder.row(
        InlineKeyboardButton(text=back_groups_text, callback_data=back_callback),
        InlineKeyboardButton(text=back_main_text, callback_data="back_to_main")
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


def get_settings_menu_inline(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Настройки - InlineKeyboardMarkup"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'settings_menu', 'language']),
            callback_data="settings_lang"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'settings_menu', 'delete_data']),
            callback_data="settings_delete"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'settings_menu', 'back']),
            callback_data="settings_back"
        )
    )

    return builder.as_markup()


def get_confirm_delete_source_kb(source_name: str, subscription_id: int, get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """Подтверждение удаления источника"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"del_sub_confirm:{subscription_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет, отмена",
            callback_data="del_sub_cancel"
        )
    )

    return builder.as_markup()


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
    back_text = get_text(['keyboards', 'back_to_settings'])

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
    topic_title: str,
    page: int = 0,
    page_size: int = 5,
    get_text: Optional[GetTextFunc] = None,
    use_subscription_id: bool = False,
    back_callback: str = "list_back:topics"
) -> InlineKeyboardMarkup:
    """Инлайн клавиатура для списка источников с навигацией.

    Структура:
    - КАЖДЫЙ ИСТОЧНИК = ДВЕ КНОПКИ В ОДНОЙ СТРОКЕ: [📰 Имя] [❌]
    - Навигационные кнопки всегда видны (с заглушками-точками если нет prev/next)
    - Две кнопки назад: "к темам" и "в главное меню"

    Args:
        sources: Список источников с полями source_global_id, name, (опционально subscription_id)
        topic_title: Название темы для отображения в заголовке
        page: Текущая страница (0-based)
        page_size: Количество источников на странице
        get_text: Функция локализации
        use_subscription_id: Если True, использовать subscription_id для callback_data удаления
        back_callback: Callback_data для кнопки "Назад к темам" (по умолчанию "list_back:topics")
    """
    builder = InlineKeyboardBuilder()

    # Если get_text не передан, используем заглушку с правильной сигнатурой
    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            fallback_text = {
                'view_source': '📰 {name}',
                'delete': '❌',
                'prev': '◀️ Назад',
                'next': 'Вперед ▶️',
                'close': '❌ Закрыть',
                'back_to_main': '🔙 В главное меню',
                'noop': '⏺️',
                'dot': '.'
            }.get(keys[-1], keys[-1])
            return fallback_text

    view = get_text(['keyboards', 'sources_list', 'view_source'])
    delete = get_text(['keyboards', 'sources_list', 'delete'])
    prev = get_text(['keyboards', 'sources_list', 'prev'])
    next = get_text(['keyboards', 'sources_list', 'next'])
    back_to_topics = get_text(['keyboards', 'back_to_topics']) if get_text else '🔙 К темам'
    back_to_main = get_text(['keyboards', 'back_to_main']) if get_text else '🔙 В главное меню'
    dot = get_text(['keyboards', 'sources_list', 'dot'])

    total_pages = max(1, (len(sources) + page_size - 1) // page_size)
    page = min(page, total_pages - 1)
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(sources))
    page_sources = sources[start_idx:end_idx]

    # ===== КАЖДЫЙ ИСТОЧНИК = ДВЕ КНОПКИ В ОДНОЙ СТРОКЕ =====
    for source in page_sources:
        source_name = source.get('name', source.get('source_global_id', 'Без названия'))
        if len(source_name) > 20:
            source_name = source_name[:17] + "..."

        # Определяем callback_data для удаления
        if use_subscription_id and 'subscription_id' in source:
            delete_callback = f"del_sub:{source['subscription_id']}"
        else:
            delete_callback = f"del_source:{source['source_global_id']}"

        # Формируем строку с ДВУМЯ кнопками: [📰 Имя] [❌]
        builder.row(
            InlineKeyboardButton(
                text=view.format(name=source_name),
                callback_data=f"view_source:{source['source_global_id']}"
            ),
            InlineKeyboardButton(
                text=delete,
                callback_data=delete_callback
            )
        )

    # ===== НАВИГАЦИОННЫЕ КНОПКИ - ВСЕГДА =====
    nav_buttons = []

    # Кнопка "Назад" или заглушка
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=prev, callback_data=f"sources_page:{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot, callback_data="noop"))

    # Счетчик страниц (всегда)
    page_text = f"{page+1}/{total_pages}"
    nav_buttons.append(InlineKeyboardButton(text=page_text, callback_data="noop"))

    # Кнопка "Вперед" или заглушка
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=next, callback_data=f"sources_page:{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot, callback_data="noop"))

    builder.row(*nav_buttons)

    # ===== ДВЕ КНОПКИ НАЗАД =====
    builder.row(
        InlineKeyboardButton(text=back_to_topics, callback_data=back_callback),
        InlineKeyboardButton(text=back_to_main, callback_data="back_to_main")
    )

    return builder.as_markup()


# В конце файла bot/keyboards.py
__all__ = [
    'get_main_menu',
    'get_main_menu_inline',
    'get_admin_panel_menu',
    'get_admin_panel_menu_inline',
    'get_groups_menu',
    'get_destinations_menu',
    'get_destinations_inline_kb',
    'get_groups_inline_kb',
    'get_topics_inline_kb',
    'get_cancel_kb_reply',
    'get_back_to_main_kb',
    'get_settings_menu',
    'get_settings_menu_inline',
    'get_confirm_channel_kb',
    'get_cancel_kb',
    'get_language_menu',
    'get_back_to_settings_kb',
    'get_confirm_delete_kb',
    'get_source_list_kb',
    'get_confirm_delete_source_kb',
    'get_overview_kb',
    'GetTextFunc',
]


def get_overview_kb(
    overview_data: List[dict],
    page: int = 0,
    get_text: Optional[GetTextFunc] = None
) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для обзора источников с пагинацией по группам.
    
    Структура:
    - Кнопки навигации между страницами (5 групп на странице)
    - Кнопка "Обновить" для обновления обзора
    - Кнопка "В главное меню"
    """
    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            fallback_text = {
                'prev': '◀️ Назад',
                'next': 'Вперед ▶️',
                'refresh': '🔄 Обновить',
                'back_to_main': '🔙 В главное меню',
                'noop': '⏺️',
                'dot': '.'
            }.get(keys[-1], keys[-1])
            return fallback_text
    
    builder = InlineKeyboardBuilder()
    
    # Пагинация: 5 групп на страницу
    groups_per_page = 5
    total_pages = (len(overview_data) + groups_per_page - 1) // groups_per_page if overview_data else 1
    page = max(0, min(page, total_pages - 1))
    
    # ===== НАВИГАЦИОННЫЕ КНОПКИ =====
    nav_buttons = []
    
    prev_text = get_text(['keyboards', 'overview', 'prev']) if get_text else '◀️ Назад'
    next_text = get_text(['keyboards', 'overview', 'next']) if get_text else 'Вперед ▶️'
    refresh_text = get_text(['keyboards', 'main_menu', 'refresh']) if get_text else '🔄 Обновить'
    back_text = get_text(['keyboards', 'back_to_main']) if get_text else '🔙 В главное меню'
    dot_text = get_text(['keyboards', 'overview', 'dot']) if get_text else '.'
    
    # Кнопка "Назад" или заглушка
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=prev_text, callback_data=f"overview_page:{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot_text, callback_data="noop"))
    
    # Счетчик страниц
    page_indicator = f"{page + 1}/{total_pages}"
    nav_buttons.append(InlineKeyboardButton(text=page_indicator, callback_data="noop"))
    
    # Кнопка "Вперед" или заглушка
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=next_text, callback_data=f"overview_page:{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=dot_text, callback_data="noop"))
    
    builder.row(*nav_buttons)
    
    # ===== КНОПКИ ДЕЙСТВИЙ =====
    builder.row(
        InlineKeyboardButton(text=refresh_text, callback_data="menu_overview"),
        InlineKeyboardButton(text=back_text, callback_data="back_to_main")
    )
    
    return builder.as_markup()
# bot/keyboards/admin.py
"""Клавиатуры для админ-панели."""
from typing import Callable, Dict, Any, List, Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

GetTextFunc = Callable[[List[str], Dict[str, Any]], str]


def get_admin_panel_menu_inline(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Админ-панель - InlineKeyboardMarkup.
    
    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопками админ-панели
    """
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
        back_callback: Callback_data для кнопки "Назад"
        mode: "list" для просмотра источников, "add" для добавления канала

    Returns:
        InlineKeyboardMarkup для выбора групп
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

    Returns:
        InlineKeyboardMarkup для выбора топиков
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

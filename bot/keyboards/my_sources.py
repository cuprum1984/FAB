# bot/keyboards/my_sources.py
"""Клавиатуры для 'Мои источники'."""
from typing import Callable, Dict, Any, List, Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

GetTextFunc = Callable[[List[str], Dict[str, Any]], str]


def get_overview_kb(
    overview_data: List[dict],
    page: int = 0,
    get_text: Optional[GetTextFunc] = None
) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для обзора источников с пагинацией по группам.
    
    Структура:
    - Кнопки выбора групп (5 групп на странице)
    - Кнопки навигации между страницами
    - Кнопка "Обновить" для обновления обзора
    - Кнопка "В главное меню"
    
    Args:
        overview_data: Список групп с топиками и источниками
        page: Текущая страница (0-based)
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup для навигации по обзору
    """
    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            fallback_text = {
                'prev': '◀️ Назад',
                'next': 'Вперед ▶️',
                'refresh': '🔄 Обновить',
                'back_to_main': '🔙 В главное меню',
                'noop': '⏺️',
                'dot': '.',
                'group_select': '👥 {name}'
            }.get(keys[-1], keys[-1])
            return fallback_text

    builder = InlineKeyboardBuilder()

    # Пагинация: 5 групп на страницу
    groups_per_page = 5
    total_pages = (len(overview_data) + groups_per_page - 1) // groups_per_page if overview_data else 1
    page = max(0, min(page, total_pages - 1))

    start_idx = page * groups_per_page
    end_idx = min(start_idx + groups_per_page, len(overview_data))
    page_groups = overview_data[start_idx:end_idx]

    # ===== КНОПКИ ВЫБОРА ГРУПП =====
    for group in page_groups:
        chat_id = group["chat_id"]
        chat_title = group["chat_title"]
        topics_count = len(group["topics"])
        sources_count = sum(t["sources_count"] for t in group["topics"])

        # Формируем текст кнопки: Название группы (топики/источники)
        display_name = f"{chat_title[:30]} ({topics_count}/{sources_count})"

        builder.row(
            InlineKeyboardButton(
                text=f"👥 {display_name}",
                callback_data=f"list_group:{chat_id}"
            )
        )

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


def get_topics_tree_kb(
    topics_data: List[dict],
    get_text: Optional[GetTextFunc] = None,
    back_callback: str = "back_to_main"
) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для дерева топиков группы.
    
    Структура:
    - Кнопки для каждого топика (для перехода к редактированию)
    - Кнопка "Назад к группам"
    - Кнопка "В главное меню"
    
    Args:
        topics_data: Список топиков с источниками
        get_text: Функция локализации
        back_callback: Callback для кнопки "Назад к группам"

    Returns:
        InlineKeyboardMarkup для навигации по топикам
    """
    if not get_text:
        def get_text(keys: List[str], **kwargs) -> str:
            fallback_text = {
                'topic_select': '🗨️ {name}',
                'back_to_groups': '← К группам',
                'back_to_main': '🔙 В главное меню',
                'noop': '⏺️',
                'dot': '.'
            }.get(keys[-1], keys[-1])
            return fallback_text

    builder = InlineKeyboardBuilder()

    # Кнопки для каждого топика
    for topic in topics_data:
        topic_name = topic["topic_name"]
        if topic["is_general"]:
            display_name = "💬 General"
        else:
            display_name = f"🗨️ {topic_name[:30]}"

        # Используем topic_identifier для callback_data
        topic_identifier = topic["topic_identifier"]
        # Кодируем в base64 для безопасной передачи
        import base64
        topic_id_encoded = base64.urlsafe_b64encode(topic_identifier.encode()).decode().rstrip('=')

        builder.row(
            InlineKeyboardButton(
                text=display_name,
                callback_data=f"list_topic:{topic_id_encoded}"
            )
        )

    # ===== КНОПКИ НАВИГАЦИИ =====
    back_groups_text = get_text(['keyboards', 'topics_menu', 'back']) if get_text else '← К группам'
    back_main_text = get_text(['keyboards', 'back_to_main']) if get_text else '🔙 В главное меню'

    builder.row(
        InlineKeyboardButton(text=back_groups_text, callback_data="list_back:groups"),
        InlineKeyboardButton(text=back_main_text, callback_data=back_callback)
    )

    return builder.as_markup()

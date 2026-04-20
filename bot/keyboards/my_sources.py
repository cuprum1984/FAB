# bot/keyboards/my_sources.py
"""Клавиатуры для 'Мои источники'."""
from typing import Callable, Dict, Any, List, Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

GetTextFunc = Callable[[List[str], Dict[str, Any]], str]



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

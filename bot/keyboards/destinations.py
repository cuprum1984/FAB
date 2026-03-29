# bot/keyboards/destinations.py
"""Клавиатуры для выбора назначений."""
from typing import Callable, Dict, Any, List, Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

GetTextFunc = Callable[[List[str], Dict[str, Any]], str]


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
    
    Args:
        destinations: Список назначений с полями chat_id, chat_title, topic_identifier, is_general, thread_name
        page: Текущая страница (0-based)
        page_size: Количество групп на странице
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup для выбора назначений
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

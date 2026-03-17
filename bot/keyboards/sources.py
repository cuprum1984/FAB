# bot/keyboards/sources.py
"""Клавиатуры для добавления источников."""
from typing import Callable, Dict, Any, List, Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

GetTextFunc = Callable[[List[str], Dict[str, Any]], str]


def get_confirm_channel_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Подтверждение добавления канала (инлайн).
    
    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопками подтверждения
    """
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
    """
    Инлайн кнопка отмены.
    
    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопкой отмены
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'cancel']),
            callback_data="cancel_add_channel"
        )
    )
    return builder.as_markup()


def get_confirm_delete_source_kb(source_name: str, subscription_id: int, get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Подтверждение удаления источника.
    
    Args:
        source_name: Название источника
        subscription_id: ID подписки
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопками подтверждения/отмены
    """
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


def get_source_list_kb(
    sources: List[dict],
    topic_title: str,
    page: int = 0,
    page_size: int = 5,
    get_text: Optional[GetTextFunc] = None,
    use_subscription_id: bool = False,
    back_callback: str = "list_back:topics"
) -> InlineKeyboardMarkup:
    """
    Инлайн клавиатура для списка источников с навигацией.
    
    Структура:
    - КАЖДЫЙ ИСТОЧНИК = ДВЕ КНОПКИ В ОДНОЙ СТРОКЕ: [📰 Имя] [❌]
    - Навигационные кнопки всегда видны (с заглушками если нет prev/next)
    - Две кнопки назад: "к темам" и "в главное меню"
    
    Args:
        sources: Список источников с полями source_global_id, name, (опционально subscription_id)
        topic_title: Название темы для отображения в заголовке
        page: Текущая страница (0-based)
        page_size: Количество источников на странице
        get_text: Функция локализации
        use_subscription_id: Если True, использовать subscription_id для callback_data удаления
        back_callback: Callback_data для кнопки "Назад к темам"

    Returns:
        InlineKeyboardMarkup для навигации по источникам
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

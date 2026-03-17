# bot/keyboards/main_menu.py
"""Главное меню."""
from typing import Callable, Dict, Any, List
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Определяем тип для функции перевода
GetTextFunc = Callable[[List[str], Dict[str, Any]], str]


def get_main_menu_inline(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Главное меню - InlineKeyboardMarkup.
    
    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопками главного меню
    """
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

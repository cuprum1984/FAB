# bot/keyboards/settings.py
"""Клавиатуры для настроек."""
from typing import Callable, Dict, Any, List
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

GetTextFunc = Callable[[List[str], Dict[str, Any]], str]


def get_settings_menu_inline(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Настройки - InlineKeyboardMarkup.

    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup меню настроек
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'settings_menu', 'language']),
            callback_data="settings_lang"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💎 Поддержать автора",
            callback_data="settings_support"
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


def get_language_menu(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Инлайн клавиатура для выбора языка.
    
    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопками языков
    """
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
    """
    Кнопка возврата в настройки.
    
    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопкой "Назад"
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text(['keyboards', 'back_to_settings']),
            callback_data="back_to_settings"
        )
    )
    return builder.as_markup()


def get_confirm_delete_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Подтверждение удаления данных.
    
    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопками подтверждения/отмены
    """
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

"""Клавиатуры для GDPR согласия и legal-документов."""
from typing import Callable, Dict, Any
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

GetTextFunc = Callable[[list, Dict[str, Any]], str]


def get_consent_request_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Клавиатура запроса согласия (при первом /start).
    
    Args:
        get_text: Функция локализации
        
    Returns:
        InlineKeyboardMarkup с кнопками "Читать условия" и "✅ Понятно"
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка "📄 Полные условия"
    builder.row(
        InlineKeyboardButton(
            text=get_text(['legal', 'read_terms']),
            callback_data="legal_read_terms"
        )
    )
    
    # Кнопка "✅ Понятно, принимаю"
    builder.row(
        InlineKeyboardButton(
            text=get_text(['legal', 'consent_accept']),
            callback_data="consent_accept"
        )
    )
    
    return builder.as_markup()


def get_legal_read_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Клавиатура после прочтения документов.
    
    Args:
        get_text: Функция локализации
        
    Returns:
        InlineKeyboardMarkup с кнопкой "✅ Понятно, принимаю"
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=get_text(['legal', 'consent_accept']),
            callback_data="consent_accept"
        )
    )
    
    return builder.as_markup()


def get_legal_terms_kb(get_text: GetTextFunc) -> InlineKeyboardMarkup:
    """
    Клавиатура для просмотра документов из настроек.

    Args:
        get_text: Функция локализации

    Returns:
        InlineKeyboardMarkup с кнопкой "Назад в настройки"
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=get_text(['legal', 'back_to_settings']),
            callback_data="legal_back_to_settings"
        )
    )

    return builder.as_markup()

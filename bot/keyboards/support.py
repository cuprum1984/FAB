# bot/keyboards/support.py
"""Клавиатуры для меню поддержки."""
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from typing import Callable


def get_support_menu_kb(get_text: Callable) -> InlineKeyboardMarkup:
    """
    Меню поддержки: кнопки сумм + навигация.
    
    Args:
        get_text: Функция локализации из i18n

    Кнопки:
    - 💎 100 ⭐ (~$2)
    - 💎💎 250 ⭐ (~$5)
    - 💎💎💎 500 ⭐ (~$10)
    - 👑 2500 ⭐ (~$50)
    - ⚙️ В настройки (локализовано)
    - ◀️ В главное меню (локализовано)
    """
    builder = InlineKeyboardBuilder()

    # Кнопки сумм (2 в ряд) — суммы универсальны, не требуют локализации текста кнопки,
    # но можно добавить подсказку в description при необходимости
    builder.button(text="💎 100 ⭐", callback_data="support_100")
    builder.button(text="💎💎 250 ⭐", callback_data="support_250")
    builder.button(text="💎💎💎 500 ⭐", callback_data="support_500")
    builder.button(text="👑 2500 ⭐", callback_data="support_2500")

    # Навигация (2 в ряд) — используем локализованные строки
    builder.button(text=get_text(['keyboards', 'back_to_settings']), callback_data="support_settings")
    builder.button(text=get_text(['keyboards', 'back_to_main']), callback_data="support_back")

    builder.adjust(2, 2, 2)
    return builder.as_markup()

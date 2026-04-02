# bot/keyboards/support.py
"""Клавиатуры для меню поддержки."""
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def get_support_menu_kb() -> InlineKeyboardMarkup:
    """
    Меню поддержки: кнопки сумм + навигация.

    Кнопки:
    - 💎 100 ⭐ (~$2)
    - 💎💎 250 ⭐ (~$5)
    - 💎💎💎 500 ⭐ (~$10)
    - 👑 2500 ⭐ (~$50)
    - ⚙️ В настройки
    - ◀️ В главное меню
    """
    builder = InlineKeyboardBuilder()

    # Кнопки сумм (2 в ряд)
    builder.button(text="💎 100 ⭐", callback_data="support_100")
    builder.button(text="💎💎 250 ⭐", callback_data="support_250")
    builder.button(text="💎💎💎 500 ⭐", callback_data="support_500")
    builder.button(text="👑 2500 ⭐", callback_data="support_2500")

    # Навигация (2 в ряд)
    builder.button(text="⚙️ В настройки", callback_data="support_settings")
    builder.button(text="◀️ В главное меню", callback_data="support_back")

    builder.adjust(2, 2, 2)
    return builder.as_markup()

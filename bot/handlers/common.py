# bot/handlers/common.py
"""
Общие хендлеры: /start, /help, главное меню.
Версия: 3.3 (20 февраля 2026)
Изменения:
- Убран конфликтующий дебаг-хендлер
- Чистая структура
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import TelegramAccount, UserPreferences
from bot.keyboards import get_main_menu
from aiogram import Bot

logger = logging.getLogger(__name__)
router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    
    await state.clear()
    
    # Проверяем пользователя
    stmt = select(TelegramAccount).where(TelegramAccount.telegram_account_id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Регистрация нового
        new_account = TelegramAccount(
            telegram_account_id=user_id,
            telegram_username=message.from_user.username,
            telegram_first_name=first_name,
            language_code=message.from_user.language_code or 'en'
        )
        session.add(new_account)
        
        prefs = UserPreferences(user_id=user_id, language=new_account.language_code)
        session.add(prefs)
        await session.commit()
        
        text = get_text(['common', 'start_new'], first_name=first_name)
    else:
        text = get_text(['common', 'start_return'], first_name=first_name)

    # Отправляем ответ С КЛАВИАТУРОЙ
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


# Константы для кнопок главного меню
HELP_BUTTONS = ["❓ Помощь", "❓ Help", "❓ Довідка", "❓ Даведка"]
MAIN_MENU_BUTTONS = ["🏠 Главное меню", "🏠 Main menu", "🏠 Головне меню", "🏠 Галоўнае меню"]
CANCEL_BUTTONS = ["❌ Отмена", "❌ Cancel", "❌ Скасування", "❌ Скасаванне"]
REFRESH_BUTTONS = ["🔄 Обновить", "🔄 Refresh", "🔄 Оновити", "🔄 Абнавіць"]


@router.message(Command("help"))
@router.message(F.text.in_(HELP_BUTTONS))
async def cmd_help(message: Message, get_text: callable):
    """Обработчик команды /help"""
    await message.answer(
        get_text(['common', 'help']),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


@router.message(F.text.in_(MAIN_MENU_BUTTONS))
async def cmd_menu(message: Message, state: FSMContext, get_text: callable):
    """Возврат в меню"""
    await state.clear()
    await message.answer(
        get_text(['common', 'menu']),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


@router.message(Command("cancel"))
@router.message(F.text.in_(CANCEL_BUTTONS))
async def cmd_cancel(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            get_text(['common', 'no_active_action']),
            parse_mode="HTML",
            reply_markup=get_main_menu(get_text)
        )
        return

    await state.clear()
    await message.answer(
        get_text(['common', 'cancel']),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


@router.message(Command("refresh"))
@router.message(F.text.in_(REFRESH_BUTTONS))
async def cmd_refresh(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обновить интерфейс (как /start, но мягче)"""
    
    # Сбрасываем состояние
    await state.clear()
    
    # Показываем приветствие
    user = message.from_user
    first_name = user.first_name or "User"
    
    await message.answer(
        get_text(['refresh', 'success'], first_name=first_name),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Вернуться в главное меню (по callback)"""
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        get_text(['common', 'menu']),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


@router.message(Command("apiversion"))
async def cmd_api_version(message: Message, bot: Bot, get_text: callable):
    """Паказаць версію Bot API"""
    try:
        # Спрабуем атрымаць версію API
        if hasattr(bot, 'api_version'):
            version = bot.api_version
            await message.answer(f"🤖 **Bot API версія:** `{version}`")
        else:
            # Калі няма api_version, спрабуем праз bot.get_me()
            me = await bot.get_me()
            await message.answer(
                f"🤖 **Інфармацыя пра бота:**\n"
                f"• Імя: {me.full_name}\n"
                f"• Юзернейм: @{me.username}\n"
                f"• ID: `{me.id}`\n\n"
                f"⚠️ Версію API не атрымалася вызначыць.\n"
                f"Хутчэй за ўсё, выкарыстоўваецца версія **ніжэйшая за 9.4**."
            )
    except Exception as e:
        await message.answer(f"❌ Памылка: {e}")
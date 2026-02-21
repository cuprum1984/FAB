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
        
        if not user:
            # Создаём нового пользователя
            user = TelegramAccount(
                telegram_account_id=user_id,
                telegram_username=username,
                telegram_first_name=first_name,
                telegram_last_name=last_name,
                language_code=message.from_user.language_code
            )
            session.add(user)
            await session.commit()
            logger.info(f"✅ Новый пользователь сохранён в БД: {user_id}")

            welcome_text = (
                f"👋 <b>Добро пожаловать, {first_name}!</b>\n\n"
                f"🤖 <b>MyAggryBot</b> - автоматическая доставка контента из Telegram и YouTube каналов в ваши группы.\n\n"
                f"<b>📌 Что умеет бот:</b>\n"
                f"• Добавлять Telegram каналы (@username)\n"
                f"• Добавлять YouTube каналы (по ссылке)\n"
                f"• Отправлять новые посты в темы групп\n"
                f"• Работать с несколькими группами\n\n"
                f"<b>🔧 Для начала:</b>\n"
                f"1. Добавьте бота в группу и сделайте администратором\n"
                f"2. В группе введите команду /activ\n"
                f"3. Возвращайтесь сюда и нажмите '📥 Добавить канал'"
            )
        else:
            # Обновляем информацию о пользователе
            user.telegram_username = username
            user.telegram_first_name = first_name
            user.telegram_last_name = last_name
            user.last_activity = None
            if not user.is_active:
                user.is_active = True
            await session.commit()

            welcome_text = f"👋 <b>С возвращением, {first_name}!</b>\n\n🤖 Бот готов к работе."
        
        text = get_text(['common', 'start_new'], first_name=first_name)
    else:
        text = get_text(['common', 'start_return'], first_name=first_name)

    # Отправляем ответ С КЛАВИАТУРОЙ
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


@router.message(Command("help"))
@router.message(F.text.in_({"❓ Помощь", "❓ Help"}))
async def cmd_help(message: Message, get_text: callable):
    """Обработчик команды /help"""
    await message.answer(
        get_text(['common', 'help']),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


@router.message(F.text.in_({"🏠 Главное меню", "🏠 Main menu"}))
async def cmd_menu(message: Message, state: FSMContext, get_text: callable):
    """Возврат в меню"""
    await state.clear()
    await message.answer(
        get_text(['common', 'menu']),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
@router.message(F.text == "❌ Cancel")
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
@router.message(F.text.in_({"🔄 Обновить", "🔄 Refresh"}))
async def cmd_refresh(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обновить интерфейс (как /start, но мягче)"""

    # 1. Сбрасываем состояние (если пользователь где-то застрял)
    await state.clear()

    # 2. Проверяем, есть ли пользователь в БД
    stmt = select(TelegramAccount).where(TelegramAccount.telegram_account_id == message.from_user.id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user and not user.is_active:
        user.is_active = True
        await session.commit()

    # 3. Показываем приветствие (как /start)
    user = message.from_user
    first_name = user.first_name or "Пользователь"

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
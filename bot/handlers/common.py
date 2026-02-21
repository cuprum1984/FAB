# bot/handlers/common.py
"""
Общие хендлеры: /start, /help, главное меню.
Версия: 2.3 (14 февраля 2026)
Изменения:
- Убран unknown_message, который перехватывал все сообщения
- Добавлен только минимальный набор хендлеров
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import TelegramAccount
from bot.keyboards import get_main_menu

logger = logging.getLogger(__name__)

router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Пользователь"
    last_name = message.from_user.last_name
    
    logger.info(f"👋 Пользователь: @{username} ({user_id}) запустил бота")
    
    try:
        # Проверяем, есть ли пользователь в БД
        stmt = select(TelegramAccount).where(TelegramAccount.telegram_account_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
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
        
        await state.clear()
        await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu())
        
    except Exception as e:
        logger.error(f"❌ Ошибка в start: {e}", exc_info=True)
        await session.rollback()
        await message.answer("❌ Произошла ошибка. Попробуйте позже.", parse_mode="HTML")


@router.message(Command("help"))
@router.message(F.text.in_({"❓ Помощь", "Помощь"}))
async def cmd_help(message: Message, session: AsyncSession):
    """Обработчик команды /help"""
    help_text = (
        "<b>📖 Справка по MyAggryBot</b>\n\n"
        "<b>🔧 Основные команды:</b>\n"
        "• /start - запуск бота\n"
        "• /activ - активирует группу\n"
        "• /plus - активирует топик (тему) в группе\n"
        "• /help - эта справка\n"
        "• /add - добавить канал\n"
        "• /list - мои источники\n"
        "• /mytopics - мои темы\n\n"
        "• Информационный канал: <a href=\"https://t.me/MyAggryBot_Info\">@MyAggryBot_Info</a>\n\n"
        "• Задать вопрос: <a href=\"https://t.me/test_mab_q\">@MyAggryBot_Q</a>\n\n"
        "•<b>📺 YouTube каналы:</b>\n"
        "• Только по полной ссылке\n"
        "• Пример: https://youtube.com/@TheBrainDit\n\n"
        "<b>📱 Telegram каналы:</b>\n"
        "• По @username или ссылке\n"
        "• Пример: @durov\n\n"
        "<b>👥 Работа с группами:</b>\n"
        "• Добавьте бота в группу\n"
        "• Сделайте администратором\n"
        "• Введите /activ в группе\n\n"
        "<b>📚 Работа с темами (топиками):</b>\n"
        "• Создав группу, включите темы в настройках группы, создайте тему.\n"
        "• Для регистрации темы (топика) введите команду /plus\n\n"
        "<b>❓ Частые вопросы:</b>\n"
        "• Почему не добавляется YouTube? - нужна полная ссылка\n"
        "• Как часто проверяются каналы ТГ? - каждые 5 минут (тестовый режим)\n"
        "• Как часто проверяются каналы Youtube? - каждые 30 минут (тестовый режим)\n"
        "<b>❓ Что работает:</b>\n"
        "• Только кнопка - Добавить канал.\n"
        "• Ну и сам парсинг.\n"
    )
    
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_menu())


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext, session: AsyncSession):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Нет активного действия.", parse_mode="HTML", reply_markup=get_main_menu())
        return
    
    await state.clear()
    await message.answer("❌ Действие отменено.", parse_mode="HTML", reply_markup=get_main_menu())


@router.message(Command("menu"))
@router.message(F.text == "🏠 Главное меню")
async def cmd_menu(message: Message, state: FSMContext, session: AsyncSession):
    """Показать главное меню"""
    await state.clear()
    await message.answer("🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=get_main_menu())


@router.message(Command("refresh"))
@router.message(F.text == "🔄 Обновить")
async def cmd_refresh(message: Message, state: FSMContext, session: AsyncSession):
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
        f"🔄 <b>Интерфейс обновлён, {first_name}!</b>\n\n"
        f"🤖 <b>MyAggryBot</b> готов к работе.\n\n"
        f"<b>📌 Быстрые команды:</b>\n"
        f"• /add — добавить канал\n"
        f"• /list — мои источники\n"
        f"• /help — помощь",
        parse_mode="HTML",
        reply_markup=get_main_menu()  # показываем главное меню
    )

@router.message(F.text == "🔄 Обновить")
async def refresh_button(message: Message, session: AsyncSession):
    """Кнопка Обновить - вызывает ту же команду"""
    await cmd_refresh(message, session)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Вернуться в главное меню (по callback)"""
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=get_main_menu())




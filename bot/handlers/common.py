# bot/handlers/common.py
"""
Общие хендлеры: /start, /help, главное меню.
Версия: 3.3 (20 февраля 2026)
Изменения:
- Убран конфликтующий дебаг-хендлер
- Чистая структура
"""
import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import TelegramAccount, UserPreferences
from bot.keyboards import get_main_menu_inline
from bot.keyboards.legal import get_consent_request_kb, get_legal_read_kb
from bot.states import LegalStates
from bot.utils.menu_message import (
    update_or_send_menu,
    clear_menu_message,
    MENU_MESSAGE_ID_KEY,
    send_menu_message,
    delete_after_delay,
    DEFAULT_DELETE_DELAY
)
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

        # Новый пользователь - показываем запрос согласия
        await show_consent_request(
            bot=message.bot,
            user_id=user_id,
            first_name=first_name,
            state=state,
            get_text=get_text
        )
        return

    # Существующий пользователь - проверяем согласие
    if user.consent_given_at is None:
        # Согласие не дано - показываем запрос
        await show_consent_request(
            bot=message.bot,
            user_id=user_id,
            first_name=first_name,
            state=state,
            get_text=get_text
        )
        return

    # Согласие дано - показываем главное меню
    text = get_text(['common', 'start_return'], first_name=first_name)

    # Отправляем/обновляем сообщение с INLINE-КЛАВИАТУРОЙ
    await update_or_send_menu(
        bot=message.bot,
        chat_id=user_id,
        text=text,
        keyboard=get_main_menu_inline(get_text),
        state=state,
        fallback_message=message
    )


async def show_consent_request(
    bot,
    user_id: int,
    first_name: str,
    state: FSMContext,
    get_text: callable
):
    """Показать запрос согласия (при первом запуске)"""
    # Устанавливаем состояние ожидания согласия
    await state.set_state(LegalStates.waiting_consent)

    # Формируем текст запроса согласия
    text = (
        f"📋 <b>Добро пожаловать, {first_name}!</b>\n\n"
        f"{get_text(['legal', 'welcome_text'])}"
    )

    # Отправляем сообщение с клавиатурой запроса согласия
    await update_or_send_menu(
        bot=bot,
        chat_id=user_id,
        text=text,
        keyboard=get_consent_request_kb(get_text),
        state=state
    )


# Обработчики команд


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext, get_text: callable):
    """Обработчик команды /help"""
    await update_or_send_menu(
        bot=message.bot,
        chat_id=message.from_user.id,
        text=get_text(['common', 'help']),
        keyboard=get_main_menu_inline(get_text),
        state=state,
        fallback_message=message
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await update_or_send_menu(
            bot=message.bot,
            chat_id=message.from_user.id,
            text=get_text(['common', 'no_active_action']),
            keyboard=get_main_menu_inline(get_text),
            state=state,
            fallback_message=message
        )
        return

    await state.clear()
    await update_or_send_menu(
        bot=message.bot,
        chat_id=message.from_user.id,
        text=get_text(['common', 'cancel']),
        keyboard=get_main_menu_inline(get_text),
        state=state,
        fallback_message=message
    )


@router.message(Command("refresh"))
async def cmd_refresh(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обновить интерфейс (как /start, но мягче)"""

    # Сбрасываем состояние
    await state.clear()

    # Показываем приветствие
    user = message.from_user
    first_name = user.first_name or "User"

    await update_or_send_menu(
        bot=message.bot,
        chat_id=message.from_user.id,
        text=get_text(['refresh', 'success'], first_name=first_name),
        keyboard=get_main_menu_inline(get_text),
        state=state,
        fallback_message=message
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Вернуться в главное меню (по callback)"""
    await callback.answer()
    await state.clear()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Вернуться в главное меню из любого состояния (универсальный)"""
    await callback.answer()
    
    # Сохраняем message_id перед очисткой состояния!
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)
    
    # Очищаем состояние, КРОМЕ message_id
    await state.clear()
    
    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})
    
    # Обновляем текущее сообщение на главное меню
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
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


# ========== ОБРАБОТЧИКИ CALLBACK_QUERY ДЛЯ ГЛАВНОГО МЕНЮ ==========
@router.callback_query(F.data == "menu_add")
async def on_menu_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обработчик кнопки "Добавить канал" — запускает процесс добавления"""
    await callback.answer()

    # Импортируем хендлер добавления канала
    from bot.handlers.sources.add_channel import cmd_add_channel
    from aiogram.types import Message
    
    # Создаём фейковый Message объект с правильным from_user
    # Используем model_construct для обхода валидации
    fake_message = Message.model_construct(
        message_id=callback.message.message_id,
        date=callback.message.date,
        chat=callback.message.chat,
        from_user=callback.from_user,  # ✅ Реальный пользователь!
    )

    # Вызываем обработку напрямую с явной передачей bot
    await cmd_add_channel(fake_message, state, session, get_text, bot=callback.bot)


@router.callback_query(F.data == "menu_sources")
async def on_menu_sources(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обработчик кнопки "Источники" - вызывает /list"""
    await callback.answer()
    
    # Логируем информацию о пользователе
    user_id = callback.from_user.id
    is_bot = callback.from_user.is_bot
    username = callback.from_user.username
    full_name = callback.from_user.full_name
    
    logger.info(f"🔘 Кнопка 'Мои источники' нажата:")
    logger.info(f"   - from_user.id: {user_id}")
    logger.info(f"   - from_user.is_bot: {is_bot}")
    logger.info(f"   - from_user.username: @{username}")
    logger.info(f"   - from_user.full_name: {full_name}")
    
    # Сохраняем message_id перед очисткой состояния!
    data = await state.get_data()
    menu_message_id = data.get('_menu_message_id')
    logger.info(f"💾 Сохранён menu_message_id: {menu_message_id}")
    
    # Очищаем состояние, КРОМЕ message_id
    await state.clear()
    
    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({'_menu_message_id': menu_message_id})
        logger.info(f"💾 Восстановлен menu_message_id: {menu_message_id}")
    
    # Импортируем функцию обработки из my_sources_interactive
    from bot.handlers.my_sources_interactive import _process_my_sources_from_callback
    
    # Вызываем обработку напрямую — ПЕРЕДАЁМ callback.from_user.id
    await _process_my_sources_from_callback(
        callback=callback,
        session=session,
        state=state,
        get_text=get_text
    )


@router.callback_query(F.data == "menu_overview")
async def on_menu_overview(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обработчик кнопки "Обзор" — показывает все группы, топики и источники """
    await callback.answer()
    
    # Запускаем процесс обзора (обновляет текущее message_id)
    from bot.handlers.my_overview import start_overview
    await start_overview(callback.bot, callback.from_user.id, session, state, get_text)


@router.callback_query(F.data == "menu_help")
async def on_menu_help(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Обработчик кнопки "Помощь" """
    await callback.answer()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'help']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )


@router.callback_query(F.data == "menu_settings")
async def on_menu_settings(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Обработчик кнопки "Настройки" """
    from bot.keyboards import get_settings_menu_inline
    
    await callback.answer()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text="⚙️ <b>Настройки</b>\n\nИспользуйте команду /settings для изменения настроек.",
        keyboard=get_settings_menu_inline(get_text),
        state=state
    )


@router.callback_query(F.data == "menu_refresh")
async def on_menu_refresh(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обработчик кнопки "Обновить" — создаёт новое сообщение вместо старого"""
    await callback.answer()

    # Получаем текущий message_id перед очисткой состояния
    data = await state.get_data()
    old_message_id = data.get("_menu_message_id")

    # Очищаем состояние
    await state.clear()

    user = callback.from_user
    first_name = user.first_name or "User"

    # Отправляем НОВОЕ сообщение (не редактируем!)
    new_message_id = await send_menu_message(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['refresh', 'success'], first_name=first_name),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )

    # Удаляем старое сообщение (задержка из menu_message.py)
    if old_message_id:
        asyncio.create_task(delete_after_delay(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            message_id=old_message_id,
            delay=DEFAULT_DELETE_DELAY
        ))

    logger.info(f"🔄 Обновление меню: старое {old_message_id} → новое {new_message_id}")


# ========== LEGAL HANDLERS (GDPR consent) ==========

@router.callback_query(F.data == "legal_read_terms")
async def on_legal_read_terms(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Обработчик кнопки "📄 Полные условия" - показывает документы"""
    await callback.answer()

    # Читаем файл terms-privacy.md
    try:
        with open("docs/legal/terms-privacy.md", 'r', encoding='utf-8') as f:
            doc_text = f.read()
    except FileNotFoundError:
        doc_text = get_text(['legal', 'legal_title']) + "\n\n⚠️ Документ временно недоступен."

    # Отправляем НОВОЕ сообщение с полным текстом (Markdown)
    await callback.message.answer(
        text=doc_text,
        parse_mode="Markdown",
        reply_markup=get_legal_read_kb(get_text)
    )


@router.callback_query(F.data == "consent_accept")
async def on_consent_accept(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    get_text: callable
):
    """Обработчик кнопки "✅ Понятно, принимаю" - запись согласия"""
    user_id = callback.from_user.id

    # Обновляем БД - записываем факт согласия
    from sqlalchemy import update, func
    stmt = update(TelegramAccount).where(
        TelegramAccount.telegram_account_id == user_id
    ).values(
        consent_given_at=func.now()
    )
    await session.execute(stmt)
    await session.commit()

    # Очищаем состояние
    await state.clear()

    # Показываем главное меню
    first_name = callback.from_user.first_name or "User"
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=user_id,
        text=get_text(['common', 'start_return'], first_name=first_name),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )

    await callback.answer(get_text(['legal', 'consent_success']))


@router.callback_query(F.data == "settings_legal_terms")
async def on_settings_legal_terms(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Обработчик кнопки "📋 Условия и конфиденциальность" в настройках"""
    await callback.answer()

    # Читаем файл terms-privacy.md
    try:
        with open("docs/legal/terms-privacy.md", 'r', encoding='utf-8') as f:
            doc_text = f.read()
    except FileNotFoundError:
        doc_text = get_text(['legal', 'legal_title']) + "\n\n⚠️ Документ временно недоступен."

    # Обновляем существующее сообщение (как кнопка "Помощь")
    from bot.keyboards.legal import get_legal_terms_kb

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=doc_text,
        keyboard=get_legal_terms_kb(get_text),
        state=state
    )


@router.callback_query(F.data == "legal_back_to_settings")
async def on_legal_back_to_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Обработчик кнопки "Назад в настройки" из legal-документов"""
    await callback.answer()

    # Сохраняем message_id перед очисткой состояния!
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)

    # Очищаем состояние, КРОМЕ message_id
    await state.clear()

    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})

    # Возвращаем в настройки
    from bot.keyboards.settings import get_settings_menu_inline

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['settings', 'title']),
        keyboard=get_settings_menu_inline(get_text),
        state=state
    )
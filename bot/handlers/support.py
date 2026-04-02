# bot/handlers/support.py
"""
Хендлеры для системы добровольных пожертвований через Telegram Stars.
"""
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.utils.menu_message import update_or_send_menu, delete_menu_message_with_delay, save_menu_message_id, MENU_MESSAGE_ID_KEY
from bot.keyboards.support import get_support_menu_kb
from bot.keyboards.main_menu import get_main_menu_inline
from bot.keyboards.settings import get_settings_menu_inline
from bot.states import Settings
from core.models import UserPreferences
from core.utils.i18n import create_i18n

logger = logging.getLogger(__name__)

router = Router(name="support")

# Суммы поддержки
SUPPORT_AMOUNTS = {
    "support_100": 100,
    "support_250": 250,
    "support_500": 500,
    "support_2500": 2500,
}


@router.callback_query(F.data == "settings_support")
async def on_support_menu(callback: CallbackQuery, state: FSMContext, get_text):
    """
    Показать меню поддержки (в том же message_id).

    Args:
        callback: CallbackQuery объект
        state: FSM состояние
        get_text: Функция локализации
    """
    text = (
        "💎 <b>Поддержать автора</b>\n\n"
        "Если бот приносит вам пользу, вы можете отблагодарить разработчика.\n\n"
        "Все средства пойдут на оплату серверов и развитие проекта.\n\n"
        "Выберите сумму:"
    )

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=get_support_menu_kb(),
        state=state
    )
    await callback.answer()


@router.callback_query(F.data == "support_settings")
async def on_support_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text):
    """
    Вернуться в настройки.

    Args:
        callback: CallbackQuery объект
        state: FSM состояние
        session: Сессия БД
        get_text: Функция локализации
    """
    # Сохраняем message_id перед изменением состояния
    from bot.utils.menu_message import MENU_MESSAGE_ID_KEY
    
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)
    
    # Получаем язык пользователя
    stmt = select(UserPreferences).where(UserPreferences.user_id == callback.from_user.id)
    result = await session.execute(stmt)
    prefs = result.scalar_one_or_none()

    current_lang = prefs.language if prefs else 'ru'
    i18n = create_i18n(current_lang)
    get_text = i18n.get

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['settings', 'title']),
        keyboard=get_settings_menu_inline(get_text),
        state=state
    )
    await state.set_state(Settings.main)
    
    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})
    
    await callback.answer()


@router.callback_query(F.data == "support_back")
async def on_support_back(callback: CallbackQuery, state: FSMContext, get_text):
    """
    Вернуться в главное меню.

    Args:
        callback: CallbackQuery объект
        state: FSM состояние
        get_text: Функция локализации
    """
    # Сохраняем message_id перед очисткой состояния
    from bot.utils.menu_message import MENU_MESSAGE_ID_KEY
    
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )
    
    # Очищаем состояние, но сохраняем message_id
    await state.clear()
    
    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})
    
    await callback.answer()


@router.callback_query(
    F.data.in_({"support_100", "support_250", "support_500", "support_2500"})
)
async def on_support_select(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """
    Выставление счёта в Stars.

    Args:
        callback: CallbackQuery объект
        bot: Объект бота
        state: FSM состояние
    """
    star_count = SUPPORT_AMOUNTS.get(callback.data)
    if not star_count:
        logger.warning(f"⚠️ Неизвестная сумма поддержки: {callback.data}")
        return

    # Сохраняем сумму в состоянии для использования после оплаты
    await state.update_data({
        "donate_amount": star_count,
        "donate_message_id": callback.message.message_id  # Для удаления
    })

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="💎 Поддержка автора",
            description="Благодарность за разработку MyAggryBot",
            payload=f"donate_{star_count}",
            provider_token="",  # ⭐ ПУСТОЙ для Stars!
            currency="XTR",     # ⭐ Валюта Stars
            prices=[LabeledPrice(label="Stars", amount=star_count)],
        )
        logger.info(f"📤 Invoice выставлен: {star_count} ⭐ для @{callback.from_user.username or callback.from_user.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при выставлении invoice: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)
        return

    await callback.answer()


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery):
    """
    Всегда подтверждаем — нет причин для отказа.

    Args:
        query: PreCheckoutQuery объект
    """
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_success_payment(message: Message, bot: Bot, state: FSMContext, get_text):
    """
    Успешная оплата Stars.

    Логика:
    1. Удаляем старое сообщение меню донатов
    2. Отправляем сообщение с благодарностью
    3. Сразу — новое главное меню (новый message_id)

    Args:
        message: Сообщение об успешной оплате
        bot: Объект бота
        state: FSM состояние
        get_text: Функция локализации
    """
    # Получаем данные из состояния
    data = await state.get_data()
    donate_message_id = data.get("donate_message_id")
    star_count = data.get("donate_amount") or message.successful_payment.total_amount

    # 1. Удаляем старое сообщение меню донатов
    if donate_message_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=donate_message_id)
            logger.debug(f"🗑️ Удалено сообщение меню донатов: {donate_message_id}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить старое сообщение: {e}")

    # 2. Сообщение с благодарностью
    thank_text = (
        f"🙏 <b>Огромное спасибо за поддержку!</b>\n\n"
        f"Вы отправили <b>{star_count} ⭐</b>\n\n"
        f"Ваша помощь очень ценна для развития MyAggryBot! 💙"
    )

    thank_msg = await message.answer(thank_text)
    logger.info(f"✅ Отправлено сообщение с благодарностью: {thank_msg.message_id}")

    # 3. Сразу — новое главное меню (новый message_id)
    await asyncio.sleep(2)

    main_menu_msg = await message.answer(
        text=get_text(['common', 'menu']),
        reply_markup=get_main_menu_inline(get_text)
    )

    # 4. Сохраняем НОВЫЙ message_id в состоянии
    await save_menu_message_id(state, main_menu_msg.message_id)
    await state.clear()

    logger.info(f"✅ Успешная оплата: {star_count} ⭐ от @{message.from_user.username or message.from_user.id}")

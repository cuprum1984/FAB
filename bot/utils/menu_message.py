# bot/utils/menu_message.py
"""
Утилиты для управления единым сообщением меню.
Обновляет одно сообщение вместо отправки новых.

Концепция: ОДНО СООБЩЕНИЕ ДЛЯ ВСЕЙ НАВИГАЦИИ
- Все экраны обновляют одно сообщение через edit_message_text
- Первое сообщение может использовать sendMessageDraft (Bot API 9.4+)
- message_id сохраняется в FSM состоянии
- При успешном действии (удаление/добавление) — старое удаляется через 2с, создаётся новое
"""
import asyncio
import logging
from typing import Optional, Union
from aiogram.types import Message, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

# Ключ для хранения message_id в состоянии
MENU_MESSAGE_ID_KEY = "_menu_message_id"

# Глобальная задержка удаления сообщений (в секундах)
# Используется во всех хендлерах при удалении/добавлении источников
DEFAULT_DELETE_DELAY = 0


async def send_menu_message(
    bot: Bot,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
    state: FSMContext,
    parse_mode: str = "HTML",
    use_draft: bool = False,
    fallback_message: Optional[Message] = None
) -> int:
    """
    Отправить новое сообщение меню и сохранить message_id в состоянии.
    
    Args:
        bot: Объект бота
        chat_id: ID чата
        text: Текст сообщения
        keyboard: Inline-клавиатура
        state: FSM состояние
        parse_mode: Режим парсинга (HTML/Markdown)
        use_draft: Если True, использовать sendMessageDraft (Bot API 9.4+)
        fallback_message: Сообщение для fallback (если edit не сработал)

    Returns:
        message_id: ID отправленного сообщения
    """
    try:
        if use_draft and hasattr(bot, 'send_message_draft'):
            # Используем sendMessageDraft для анимации "черновика"
            sent = await bot.send_message_draft(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
        else:
            # Обычная отправка
            sent = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
        
        await state.update_data({MENU_MESSAGE_ID_KEY: sent.message_id})
        logger.debug(f"📤 Отправлено сообщение меню: {sent.message_id}")
        return sent.message_id
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки сообщения меню: {e}")
        # Fallback без клавиатуры
        try:
            sent = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            await state.update_data({MENU_MESSAGE_ID_KEY: sent.message_id})
            return sent.message_id
        except Exception as e2:
            logger.error(f"❌ Fallback тоже не сработал: {e2}")
            return -1


async def edit_menu_message(
    bot: Bot,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
    state: FSMContext,
    parse_mode: str = "HTML",
    message_id: Optional[int] = None
) -> bool:
    """
    Обновить существующее сообщение меню.
    
    Args:
        bot: Объект бота
        chat_id: ID чата
        text: Новый текст
        keyboard: Новая клавиатура
        state: FSM состояние
        parse_mode: Режим парсинга
        message_id: ID сообщения (если не указан, берётся из состояния)

    Returns:
        True если успешно обновлено
    """
    if message_id is None:
        data = await state.get_data()
        message_id = data.get(MENU_MESSAGE_ID_KEY)

    if not message_id:
        logger.warning(f"⚠️ message_id не найден в состоянии")
        return False

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=keyboard
        )
        logger.debug(f"✏️ Обновлено сообщение {message_id}")
        return True
        
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            # Сообщение не изменилось — это нормально
            logger.debug(f"ℹ️ Сообщение {message_id} не изменилось")
            return True
        logger.warning(f"⚠️ Не удалось обновить сообщение {message_id}: {e}")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Не удалось обновить сообщение {message_id}: {e}")
        return False


async def update_or_send_menu(
    bot: Bot,
    chat_id: int,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    state: FSMContext = None,
    parse_mode: str = "HTML",
    fallback_message: Optional[Message] = None,
    use_draft: bool = False
) -> int:
    """
    Универсальная функция: пытается обновить существующее сообщение,
    если не получается — отправляет новое.

    Это ОСНОВНАЯ функция для всей навигации бота.

    Args:
        bot: Объект бота
        chat_id: ID чата
        text: Текст сообщения
        keyboard: Inline-клавиатура (может быть None)
        state: FSM состояние
        parse_mode: Режим парсинга
        fallback_message: Сообщение для fallback (команда пользователя или callback.message)
        use_draft: Использовать sendMessageDraft для первой отправки

    Returns:
        message_id: ID актуального сообщения
    """
    # Проверка state
    if state is None:
        logger.warning("⚠️ update_or_send_menu вызван без state")
        # Пытаемся отправить без сохранения message_id
        sent = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=keyboard
        )
        return sent.message_id
    
    data = await state.get_data()
    message_id = data.get(MENU_MESSAGE_ID_KEY)

    # Пытаемся обновить существующее сообщение
    if message_id and keyboard is not None:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
            logger.debug(f"✏️ Обновлено сообщение {message_id}")
            # Сохраняем message_id в состоянии (на случай если был очищен)
            await state.update_data({MENU_MESSAGE_ID_KEY: message_id})
            return message_id

        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                # Сообщение не изменилось
                logger.debug(f"ℹ️ Сообщение {message_id} не изменилось")
                return message_id
            logger.debug(f"⚠️ Не удалось обновить сообщение {message_id}: {e}")
        except Exception as e:
            logger.debug(f"⚠️ Не удалось обновить сообщение {message_id}: {e}")

    # Если не удалось обновить — отправляем новое
    if keyboard is not None:
        # Используем fallback_message.message_id если есть, для сохранения единого сообщения
        if fallback_message and not message_id:
            # Первое сообщение — сохраняем его ID для будущих обновлений
            try:
                # Для callback query — используем edit, для message — answer
                if hasattr(fallback_message, 'answer') and callable(getattr(fallback_message, 'answer')):
                    sent = await fallback_message.answer(
                        text,
                        parse_mode=parse_mode,
                        reply_markup=keyboard
                    )
                else:
                    sent = await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode,
                        reply_markup=keyboard
                    )
                await state.update_data({MENU_MESSAGE_ID_KEY: sent.message_id})
                logger.info(f"📤 Отправлено ПЕРВОЕ сообщение меню: {sent.message_id}, сохранено в состоянии")
                return sent.message_id
            except Exception as e:
                logger.error(f"❌ Ошибка отправки fallback: {e}")

        # Обычная отправка через send_menu_message
        return await send_menu_message(
            bot=bot,
            chat_id=chat_id,
            text=text,
            keyboard=keyboard,
            state=state,
            parse_mode=parse_mode,
            use_draft=use_draft,
            fallback_message=fallback_message
        )
    
    # Если keyboard=None — просто отправляем сообщение без клавиатуры
    sent = await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode
    )
    if state:
        await state.update_data({MENU_MESSAGE_ID_KEY: sent.message_id})
    return sent.message_id


async def update_or_send_from_callback(
    callback: CallbackQuery,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup],
    state: FSMContext,
    parse_mode: str = "HTML"
) -> int:
    """
    Обновить сообщение из callback query.
    Удобная обёртка для обработки callback.
    
    Args:
        callback: CallbackQuery объект
        text: Текст сообщения
        keyboard: Inline-клавиатура
        state: FSM состояние
        parse_mode: Режим парсинга

    Returns:
        message_id: ID актуального сообщения
    """
    return await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=keyboard,
        state=state,
        parse_mode=parse_mode
    )


async def clear_menu_message(bot: Bot, chat_id: int, state: FSMContext) -> None:
    """
    Удалить сообщение меню и очистить message_id из состояния.
    """
    data = await state.get_data()
    message_id = data.get(MENU_MESSAGE_ID_KEY)

    if message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.debug(f"🗑️ Удалено сообщение {message_id}")
        except Exception as e:
            logger.debug(f"⚠️ Не удалось удалить сообщение {message_id}: {e}")

    # Очищаем message_id из состояния
    data = await state.get_data()
    if MENU_MESSAGE_ID_KEY in data:
        del data[MENU_MESSAGE_ID_KEY]
        await state.set_data(data)


async def get_menu_message_id(state: FSMContext) -> Optional[int]:
    """Получить текущий message_id из состояния."""
    data = await state.get_data()
    return data.get(MENU_MESSAGE_ID_KEY)


async def save_menu_message_id(state: FSMContext, message_id: int) -> None:
    """Сохранить message_id в состоянии."""
    await state.update_data({MENU_MESSAGE_ID_KEY: message_id})
    logger.debug(f"💾 Сохранён message_id: {message_id}")


async def delete_after_delay(bot: Bot, chat_id: int, message_id: int, delay: int = 2) -> None:
    """Удалить сообщение через указанную задержку"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug(f"🗑️ Удалено сообщение {message_id} через {delay}с")
    except Exception as e:
        logger.debug(f"⚠️ Не удалось удалить сообщение {message_id}: {e}")


async def delete_menu_message_with_delay(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    delay: Optional[int] = None
) -> None:
    """
    Удалить текущее сообщение меню через задержку.

    Используется при успешном завершении действия (удаление/добавление),
    чтобы показать результат в НОВОМ сообщении.

    Args:
        bot: Объект бота
        chat_id: ID чата
        state: FSM состояние
        delay: Задержка в секундах перед удалением (по умолчанию DEFAULT_DELETE_DELAY)
    """
    # Используем глобальную задержку, если не указана явно
    if delay is None:
        delay = DEFAULT_DELETE_DELAY
    
    data = await state.get_data()
    message_id = data.get(MENU_MESSAGE_ID_KEY)

    if message_id:
        # Очищаем из состояния СРАЗУ
        data.pop(MENU_MESSAGE_ID_KEY, None)
        await state.set_data(data)

        # Запускаем удаление с задержкой
        asyncio.create_task(delete_after_delay(bot, chat_id, message_id, delay))
        logger.info(f"⏳ Сообщение {message_id} будет удалено через {delay}с")
    else:
        logger.warning("⚠️ message_id не найден в состоянии, нечего удалять")

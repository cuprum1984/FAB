"""Отмена добавления канала на всех этапах."""
import logging
from aiogram import Router, F
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource
from bot.states import AddChannel
from bot.keyboards import get_main_menu_inline
from bot.utils.menu_message import update_or_send_menu, MENU_MESSAGE_ID_KEY

logger = logging.getLogger(__name__)
router = Router(name="sources_cancel")


async def cancel_add_channel_flow(callback, bot: Bot, chat_id: int, state: FSMContext, session: AsyncSession, get_text: callable):
    """Отмена добавления канала — возврат в главное меню."""
    data = await state.get_data()
    source_global_id = data.get("source_global_id")
    source_created_now = data.get("source_created_now", False)

    if source_created_now and source_global_id:
        try:
            stmt = delete(ContentSource).where(ContentSource.source_global_id == source_global_id)
            await session.execute(stmt)
            await session.commit()
            logger.info(f"🗑️ Удалён источник {source_global_id} после отмены")
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка удаления источника: {e}")

    # Сохраняем текущий message_id перед очисткой
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)

    # Просто обновляем текущее сообщение на главное меню
    await update_or_send_menu(
        bot=bot,
        chat_id=chat_id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )

    # Очищаем состояние, КРОМЕ message_id
    await state.clear()

    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})


@router.callback_query(AddChannel.waiting_for_username, F.data == "cancel_add_channel")
async def cancel_channel_username(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Отмена добавления канала по Inline-кнопке — возврат в главное меню."""
    await callback.answer()

    # Сохраняем текущий message_id перед очисткой
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)

    # Просто обновляем текущее сообщение на главное меню
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )

    # Очищаем состояние, КРОМЕ message_id
    await state.clear()

    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})


@router.callback_query(AddChannel.choose_group, F.data == "cancel_add_channel")
async def cancel_channel_group(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Отмена выбора группы — удаляем источник и возвращаемся в главное меню."""
    await callback.answer()

    # Получаем данные о созданном источнике
    data = await state.get_data()
    source_global_id = data.get("source_global_id")
    source_created_now = data.get("source_created_now", False)

    # Если источник был создан в этом сеансе — удаляем его
    if source_created_now and source_global_id:
        try:
            stmt = delete(ContentSource).where(ContentSource.source_global_id == source_global_id)
            await session.execute(stmt)
            await session.commit()
            logger.info(f"🗑️ Удалён источник {source_global_id} после отмены выбора группы")
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка удаления источника {source_global_id}: {e}")

    # Сохраняем текущий message_id перед очисткой
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)

    # Обновляем текущее сообщение на главное меню
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )

    # Очищаем состояние, КРОМЕ message_id
    await state.clear()

    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})

    logger.info(f"✅ Отмена добавления канала на этапе выбора группы")


@router.callback_query(AddChannel.choose_destination, F.data == "cancel_add_channel")
async def cancel_channel_destination(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Отмена выбора темы/группы — удаляем источник и возвращаемся в главное меню."""
    await callback.answer()
    
    # Получаем данные о созданном источнике
    data = await state.get_data()
    source_global_id = data.get("source_global_id")
    source_created_now = data.get("source_created_now", False)
    
    # Если источник был создан в этом сеансе — удаляем его
    if source_created_now and source_global_id:
        try:
            stmt = delete(ContentSource).where(ContentSource.source_global_id == source_global_id)
            await session.execute(stmt)
            await session.commit()
            logger.info(f"🗑️ Удалён источник {source_global_id} после отмены выбора темы")
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка удаления источника {source_global_id}: {e}")
    
    # Сохраняем текущий message_id перед очисткой
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)
    
    # Обновляем текущее сообщение на главное меню
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )
    
    # Очищаем состояние, КРОМЕ message_id
    await state.clear()
    
    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})
    
    logger.info(f"✅ Отмена добавления канала на этапе выбора темы")


@router.message(AddChannel.choose_destination)
async def process_destination_choice(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """
    Обработать выбор группы/темы.
    ⚠️ ТЕПЕРЬ РАБОТАЕТ ТОЛЬКО ДЛЯ ОТМЕНЫ (текстовое сообщение)
    """
    data = await state.get_data()
    source_type = data.get("source_type", "telegram")
    source_global_id = data.get("source_global_id")
    source_created_now = data.get("source_created_now", False)

    # Проверяем, не является ли это сообщение об ошибке или другое
    if message.text and message.text.strip() == "❌ Отмена":
        # Если источник был создан в этом сеансе — удаляем его
        if source_created_now and source_global_id:
            try:
                stmt = delete(ContentSource).where(ContentSource.source_global_id == source_global_id)
                await session.execute(stmt)
                await session.commit()
                logger.info(f"🗑️ Удалён источник {source_global_id} после отмены пользователем")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка удаления источника {source_global_id}: {e}")

        await update_or_send_menu(
            bot=message.bot,
            chat_id=message.from_user.id,
            text=get_text(['sources', 'add_cancelled']),
            keyboard=get_main_menu_inline(get_text),
            state=state,
            fallback_message=message
        )
        await state.clear()
        # Удаляем предыдущее сообщение с inline клавиатурой
        try:
            await message.delete()
        except:
            pass
        return

    # Игнорируем другие сообщения — напоминаем использовать inline-кнопки
    await update_or_send_menu(
        bot=message.bot,
        chat_id=message.from_user.id,
        text=get_text(['sources', 'destination_use_inline']),
        keyboard=get_main_menu_inline(get_text),
        state=state,
        fallback_message=message
    )

"""Обработчики выбора группы при добавлении канала."""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states import AddChannel
from bot.keyboards import get_groups_inline_kb, get_topics_inline_kb
from bot.utils.menu_message import delete_menu_message_with_delay, send_menu_message, MENU_MESSAGE_ID_KEY
from core.services.destination_service import get_user_groups, get_group_topics
from core.utils.topic_checker import verify_user_topics

logger = logging.getLogger(__name__)
router = Router(name="sources_group_select")


@router.callback_query(AddChannel.choose_group, F.data.startswith("dest_group:"))
@router.callback_query(AddChannel.choose_group, F.data.startswith("list_group:"))
async def on_group_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Пользователь выбрал группу — показываем темы в этой группе."""
    await callback.answer()
    
    # Извлекаем chat_id группы
    chat_id = callback.data.split(":", 1)[1]
    try:
        chat_id = int(chat_id)
    except ValueError:
        await callback.answer("❌ Ошибка: неверный ID группы", show_alert=True)
        return
    
    # Получаем данные состояния
    data = await state.get_data()
    alive_topic_identifiers = data.get("alive_topic_identifiers", set())
    
    # Получаем топики в выбранной группе
    topics = await get_group_topics(chat_id, session)

    # Фильтруем только живые топики
    filtered_topics = [
        t for t in topics
        if t["topic_identifier"] in alive_topic_identifiers
    ]

    if not filtered_topics:
        await callback.answer(get_text(['sources', 'no_topics_in_group']), show_alert=True)
        return

    # Получаем название группы для отображения
    groups = await get_user_groups(callback.from_user.id, session)
    group = next((g for g in groups if g["chat_id"] == chat_id), None)
    group_title = group["chat_title"] if group else f"Группа {chat_id}"

    # Сохраняем выбранную группу в состояние
    await state.update_data(
        selected_group_chat_id=chat_id,
        selected_group_title=group_title
    )

    # 1. Удаляем старое сообщение (задержка из menu_message.py)
    await delete_menu_message_with_delay(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        state=state
    )

    # 2. Отправляем НОВОЕ сообщение с выбором ТЕМЫ
    inline_kb = get_topics_inline_kb(
        filtered_topics,
        group_title=group_title,
        page=0,
        get_text=get_text,
        back_callback="cancel_add_channel",
        mode="add"
    )
    
    new_msg = await send_menu_message(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['sources', 'add_select_topic'], group_title=group_title),
        keyboard=inline_kb,
        state=state
    )
    
    # 3. Переходим в состояние выбора темы
    await state.set_state(AddChannel.choose_destination)
    
    logger.info(f"✅ Пользователь {callback.from_user.id} выбрал группу {group_title}, показываем топики")


@router.callback_query(AddChannel.choose_group, F.data.startswith("groups_page:"))
async def on_groups_page_change(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Навигация по страницам списка групп."""
    await callback.answer()
    
    # Получаем номер страницы
    page = int(callback.data.split(":", 1)[1])
    
    # Получаем группы
    groups = await get_user_groups(callback.from_user.id, session)
    
    # 1. Удаляем старое сообщение (задержка из menu_message.py)
    await delete_menu_message_with_delay(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        state=state
    )
    
    # 2. Отправляем НОВОЕ сообщение с новым списком групп
    inline_kb = get_groups_inline_kb(groups, page=page, get_text=get_text, back_callback="cancel_add_channel", mode="add")
    
    new_msg = await send_menu_message(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['sources', 'add_select_group']),
        keyboard=inline_kb,
        state=state
    )
    
    logger.debug(f"📄 Страница групп изменена на {page + 1}")

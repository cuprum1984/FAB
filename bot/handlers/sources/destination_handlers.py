"""Выбор темы при добавлении канала."""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states import AddChannel
from bot.keyboards import get_destinations_inline_kb, get_topics_inline_kb, get_main_menu_inline
from bot.utils.menu_message import update_or_send_menu, delete_menu_message_with_delay, send_menu_message, MENU_MESSAGE_ID_KEY
from core.services.destination_service import get_group_topics
from core.utils.topic_checker import verify_user_topics

from .finalize_handlers import finalize_destination_choice

logger = logging.getLogger(__name__)
router = Router(name="sources_destinations")


@router.callback_query(AddChannel.choose_destination, F.data.startswith("dest_topic:"))
@router.callback_query(AddChannel.choose_destination, F.data.startswith("list_topic:"))
async def process_topic_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Пользователь выбрал тему — финализируем выбор."""
    await callback.answer()
    
    # Получаем данные
    data = await state.get_data()
    selected_group_chat_id = data.get("selected_group_chat_id")
    selected_group_title = data.get("selected_group_title")
    alive_topic_identifiers = data.get("alive_topic_identifiers", set())
    
    # Получаем топики группы для поиска выбранного
    topics = await get_group_topics(selected_group_chat_id, session)
    
    # Фильтруем по hash (т.к. callback_data содержит хеш)
    import hashlib
    callback_hash = callback.data.split(":", 1)[1]
    
    chosen = None
    for topic in topics:
        topic_hash = hashlib.md5(topic["topic_identifier"].encode()).hexdigest()[:8]
        if topic_hash == callback_hash and topic["topic_identifier"] in alive_topic_identifiers:
            chosen = topic
            break

    if not chosen:
        await callback.answer(get_text(['sources', 'topic_not_found']), show_alert=True)
        return

    # Создаём destination в формате, ожидаемом finalize_destination_choice
    destination = {
        "topic_identifier": chosen["topic_identifier"],
        "chat_id": selected_group_chat_id,
        "chat_title": selected_group_title,
        "thread_id": chosen["telegram_thread_id"],
        "thread_name": chosen["topic_name"],
        "is_general": chosen["telegram_thread_id"] is None
    }
    
    # Финализируем выбор
    await finalize_destination_choice(callback, destination, data, state, session, get_text)


@router.callback_query(AddChannel.choose_destination, F.data.startswith("topics_page:"))
@router.callback_query(AddChannel.choose_destination, F.data.startswith("dest_topics_page:"))
async def on_topics_page_change(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Навигация по страницам списка тем."""
    await callback.answer()
    
    # Получаем номер страницы
    page = int(callback.data.split(":", 1)[1])
    
    # Получаем данные
    data = await state.get_data()
    selected_group_chat_id = data.get("selected_group_chat_id")
    selected_group_title = data.get("selected_group_title")
    alive_topic_identifiers = data.get("alive_topic_identifiers", set())
    
    # Получаем топики
    topics = await get_group_topics(selected_group_chat_id, session)
    filtered_topics = [t for t in topics if t["topic_identifier"] in alive_topic_identifiers]
    
    # 1. Удаляем старое сообщение (задержка из menu_message.py)
    await delete_menu_message_with_delay(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        state=state
    )
    
    # 2. Отправляем НОВОЕ сообщение с новым списком тем
    inline_kb = get_topics_inline_kb(
        filtered_topics,
        group_title=selected_group_title,
        page=page,
        get_text=get_text,
        back_callback="cancel_add_channel",
        mode="add"
    )
    
    new_msg = await send_menu_message(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['sources', 'add_select_topic'], group_title=selected_group_title),
        keyboard=inline_kb,
        state=state
    )
    
    logger.debug(f"📄 Страница тем изменена на {page + 1} в группе {selected_group_title}")

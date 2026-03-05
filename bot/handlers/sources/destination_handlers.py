"""Выбор темы при добавлении канала."""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.states import AddChannel
from bot.keyboards import get_destinations_inline_kb, get_main_menu_inline
from bot.utils.menu_message import update_or_send_menu

from .finalize_handlers import finalize_destination_choice

logger = logging.getLogger(__name__)
router = Router(name="sources_destinations")


@router.callback_query(AddChannel.choose_destination, F.data.startswith("dest_select:"))
async def process_destination_inline(callback: CallbackQuery, state: FSMContext, session, get_text: callable):
    """Обработать выбор destination через inline кнопку"""

    await callback.answer()

    topic_identifier = callback.data.split(":", 1)[1]

    data = await state.get_data()
    destinations = data.get("destinations", [])
    source_global_id = data.get("source_global_id")
    source_type = data.get("source_type", "telegram")

    # Ищем выбранный destination по topic_identifier
    chosen = None
    for d in destinations:
        if d["topic_identifier"] == topic_identifier:
            chosen = d
            break

    if not chosen:
        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=get_text(['sources', 'destination_not_found']),
            keyboard=get_main_menu_inline(get_text),
            state=state
        )
        await state.clear()
        return

    # Обрабатываем выбор (без удаления сообщения — используем update_or_send_menu)
    await finalize_destination_choice(callback, chosen, data, state, session, get_text)


@router.callback_query(AddChannel.choose_destination, F.data.startswith("dest_page:"))
async def navigate_destinations(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Навигация по страницам destinations"""

    page = int(callback.data.split(":", 1)[1])

    data = await state.get_data()
    destinations = data.get("destinations", [])

    # Обновляем inline клавиатуру с новой страницей
    inline_kb = get_destinations_inline_kb(destinations, page=page, get_text=get_text)

    # Обновляем текущее сообщение через update_or_send_menu
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['sources', 'add_saved']),
        keyboard=inline_kb,
        state=state
    )

    await callback.answer()

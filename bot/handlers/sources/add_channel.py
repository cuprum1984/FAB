"""Хендлеры для начала добавления канала и ввода username."""
import logging
import urllib.parse
import asyncio
import re
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states import AddChannel
from bot.keyboards import get_cancel_kb, get_main_menu_inline, get_destinations_inline_kb, get_groups_inline_kb
from bot.utils.menu_message import update_or_send_menu, delete_menu_message_with_delay, MENU_MESSAGE_ID_KEY
from core.services.destination_service import get_user_groups, get_user_destinations
from core.parser.telegram import check_channel_exists, get_channel_title
from core.parser.telegram_posts import get_new_posts as get_telegram_posts
from core.parser.youtube_simple import get_parser
from core.security import URLSecurity
from core.utils.topic_checker import verify_user_topics

from .youtube_handlers import process_youtube_channel
from .telegram_handlers import process_telegram_channel
from .cancel_handlers import cancel_add_channel_flow

logger = logging.getLogger(__name__)
router = Router(name="sources_add")

USERNAME_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$")


@router.message(Command("add"))
async def cmd_add_channel(message: Message, state: FSMContext, session: AsyncSession, get_text: callable, bot=None):
    """Начать процесс добавления канала — обновляем текущее сообщение."""

    logger.info(f"📥 Пользователь {message.from_user.id} начал добавление канала")

    if bot is None:
        bot = message.bot

    groups = await get_user_groups(message.from_user.id, session)
    if not groups:
        await update_or_send_menu(
            bot=bot,
            chat_id=message.from_user.id,
            text=get_text(['sources', 'add_no_groups']),
            keyboard=get_main_menu_inline(get_text),
            state=state
        )
        return

    # Обновляем текущее сообщение — просим ввести username
    await update_or_send_menu(
        bot=bot,
        chat_id=message.from_user.id,
        text=get_text(['sources', 'add_prompt']),
        keyboard=get_cancel_kb(get_text),
        state=state
    )
    await state.set_state(AddChannel.waiting_for_username)


@router.message(AddChannel.waiting_for_username)
async def process_channel_username(message: Message, state: FSMContext, session: AsyncSession, get_text: callable, bot=None):
    """Обработать ввод username канала или ссылки — сразу проверяем и добавляем."""
    if bot is None:
        bot = message.bot

    raw_input = URLSecurity.sanitize_input(message.text.strip())

    # Декодируем URL-encoded символы (для кириллицы)
    try:
        raw_input = urllib.parse.unquote(raw_input)
        logger.debug(f"🔤 Декодировано: {raw_input}")
    except:
        pass

    if raw_input in ("❌ Отмена", "❌ Cancel"):
        await cancel_add_channel_flow(callback=None, bot=bot, chat_id=message.from_user.id, state=state, session=session, get_text=get_text)
        return

    # ========== 🔍 ПРОВЕРЯЕМ, НЕ YOUTUBE ЛИ ЭТО ==========
    is_youtube = False

    # Проверяем наличие youtube.com или youtu.be в ссылке
    if 'youtube.com/' in raw_input or 'youtu.be/' in raw_input:
        is_youtube = True
        logger.info(f"📺 Обнаружен YouTube по ссылке: {raw_input}")
    elif raw_input.startswith('@'):
        # Если это просто @username - это Telegram!
        logger.info(f"📱 Обнаружен Telegram username: {raw_input}")

    if is_youtube:
        # Проверяем безопасность URL
        is_safe, reason = URLSecurity.validate_url(raw_input, 'youtube')
        if not is_safe:
            await update_or_send_menu(
                bot=bot,
                chat_id=message.from_user.id,
                text=get_text(['sources', 'youtube_blocked'], reason=reason),
                keyboard=get_cancel_kb(get_text),
                state=state,
                fallback_message=message
            )
            return

        # Извлекаем username из ссылки
        username = raw_input.strip()
        if 'youtube.com/@' in username:
            username = username.split('youtube.com/@')[-1].split('/')[0]
        elif 'youtube.com/c/' in username:
            username = username.split('youtube.com/c/')[-1].split('/')[0]
        elif 'youtu.be/' in username:
            await update_or_send_menu(
                bot=bot,
                chat_id=message.from_user.id,
                text=get_text(['sources', 'youtube_invalid_link']),
                keyboard=get_cancel_kb(get_text),
                state=state,
                fallback_message=message
            )
            return

        # Используем простой парсер
        youtube_parser = get_parser()

        channel_data = await youtube_parser.get_channel_data(username)
        if not channel_data:
            await asyncio.sleep(3)
            channel_data = await youtube_parser.get_channel_data(username)

        if not channel_data:
            await update_or_send_menu(
                bot=bot,
                chat_id=message.from_user.id,
                text=get_text(['sources', 'youtube_failed']),
                keyboard=get_cancel_kb(get_text),
                state=state,
                fallback_message=message
            )
            return

        channel_id = channel_data['channel_id']
        channel_title = channel_data['channel_title']
        video_id = channel_data['video_id']

        # Сохраняем все данные
        source_global_id = f"yt_channel_{channel_id}"
        await state.update_data(
            source_type="youtube",
            source_global_id=source_global_id,
            channel_id=channel_id,
            source_title=channel_title,
            youtube_username=username,
            feed_url=f"https://youtube.com/@{username}",
            last_video_id=video_id,
        )

    # ========== ТЕЛЕГРАМ КАНАЛ ==========
    if not is_youtube:
        # Проверяем, не пытаются ли ввести что-то опасное
        if 'http://' in raw_input or 'https://' in raw_input:
            if 't.me' not in raw_input.lower() and 'telegram.org' not in raw_input.lower():
                await update_or_send_menu(
                    bot=bot,
                    chat_id=message.from_user.id,
                    text=get_text(['sources', 'telegram_invalid_domain']),
                    keyboard=get_cancel_kb(get_text),
                    state=state,
                    fallback_message=message
                )
                return

        username = raw_input.strip('@').strip('/').split('/')[-1].lower()

        if not USERNAME_REGEX.match(username):
            if len(username) == 4 and re.match(r"^[a-zA-Z][a-zA-Z0-9_]{3}$", username):
                logger.info(f"⚠️ Обнаружен короткий username (4 символа): @{username}")
            else:
                await update_or_send_menu(
                    bot=bot,
                    chat_id=message.from_user.id,
                    text=get_text(['sources', 'telegram_invalid_username']),
                    keyboard=get_cancel_kb(get_text),
                    state=state,
                    fallback_message=message
                )
                return

        exists, error = await check_channel_exists(username)
        if not exists:
            await update_or_send_menu(
                bot=bot,
                chat_id=message.from_user.id,
                text=get_text(['sources', 'telegram_not_found'], error=error),
                keyboard=get_cancel_kb(get_text),
                state=state,
                fallback_message=message
            )
            return

        posts = await get_telegram_posts(username, first_only=True)
        if not posts:
            await update_or_send_menu(
                bot=bot,
                chat_id=message.from_user.id,
                text=get_text(['sources', 'telegram_no_posts'], username=username),
                keyboard=get_cancel_kb(get_text),
                state=state,
                fallback_message=message
            )
            return

        first_post = posts[0]
        first_post_id = int(first_post['post_id'])
        title = await get_channel_title(username) or f"Канал @{username}"

        # Сохраняем все данные
        source_global_id = f"tg_channel_{username}"
        await state.update_data(
            source_type="telegram",
            source_global_id=source_global_id,
            source_username=username,
            source_title=title,
            first_post=first_post,
            first_post_id=first_post_id
        )

    # ========== ПРОВЕРКА ГРУПП И ОТПРАВКА ВЫБОРА ГРУППЫ ==========
    await process_channel_after_check(message, state, session, get_text, bot, is_youtube)


async def process_channel_after_check(message: Message, state: FSMContext, session: AsyncSession, get_text: callable, bot, is_youtube: bool):
    """Проверить группы и отправить выбор ГРУППЫ (сначала), потом тем."""
    data = await state.get_data()
    source_type = data.get("source_type")
    source_global_id = data.get("source_global_id")

    # Получаем все группы пользователя
    groups = await get_user_groups(message.from_user.id, session)
    if not groups:
        await update_or_send_menu(
            bot=bot,
            chat_id=message.from_user.id,
            text=get_text(['sources', 'error_no_groups']),
            keyboard=get_main_menu_inline(get_text),
            state=state,
            fallback_message=message
        )
        await state.clear()
        return

    # Проверяем темы
    check_text = get_text(['topic_check', 'message'])
    alive_topics, deleted_topics, total = await verify_user_topics(
        message.from_user.id,
        bot,
        session,
        check_text
    )

    # Сохраняем данные источника
    if source_type == "telegram":
        username = data.get("source_username")
        source_global_id = f"tg_channel_{username}"
        await state.update_data(
            source_global_id=source_global_id,
            first_post=data.get("first_post"),
            first_post_id=data.get("first_post_id"),
            source_title=data.get("source_title"),
            source_username=username,
            source_type="telegram",
            source_created_now=True,
            alive_topic_identifiers={t.topic_identifier for t in alive_topics}
        )
    elif source_type == "youtube":
        channel_id = data.get("channel_id")
        source_global_id = f"yt_channel_{channel_id}"
        await state.update_data(
            source_global_id=source_global_id,
            first_video=data.get("last_video"),
            first_video_id=data.get("last_video_id"),
            source_title=data.get("source_title"),
            channel_id=channel_id,
            youtube_username=data.get("youtube_username"),
            source_type="youtube",
            source_created_now=True,
            alive_topic_identifiers={t.topic_identifier for t in alive_topics}
        )

    # 1. Удаляем старое сообщение (задержка из menu_message.py)
    await delete_menu_message_with_delay(
        bot=bot,
        chat_id=message.from_user.id,
        state=state
    )

    # 2. Отправляем НОВОЕ сообщение с выбором ГРУППЫ
    inline_kb = get_groups_inline_kb(groups, page=0, get_text=get_text, back_callback="cancel_add_channel", mode="add")
    
    new_msg = await bot.send_message(
        chat_id=message.from_user.id,
        text=get_text(['sources', 'add_select_group']),
        parse_mode="HTML",
        reply_markup=inline_kb
    )

    # 3. Сохраняем новый message_id и переходим в состояние выбора группы
    await state.update_data({MENU_MESSAGE_ID_KEY: new_msg.message_id})
    await state.set_state(AddChannel.choose_group)

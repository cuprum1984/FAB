# bot/handlers/sources.py
"""
Хендлеры для управления источниками контента (каналами).
Версия: 7.0 (20 февраля 2026)
Изменения:
- Добавлена локализация (i18n)
- Все тексты вынесены в locales/
"""

import urllib.parse
import asyncio
import re
import html
import logging
import hashlib
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    ContentSource, 
    SourceSubscription, 
    TopicSourceAssignment,
    ManagedGroup,
    GroupTopic
)
from core.parser.telegram import check_channel_exists, get_channel_title
from core.parser.telegram_posts import get_new_posts as get_telegram_posts
from core.parser.youtube_simple import get_parser
from core.services.destination_service import (
    get_user_destinations,
    get_user_groups,
    get_source_subscription,
    create_source_subscription,
    create_topic_assignment,
    get_or_create_content_source,
    create_user_channel_subscription
)
from core.utils.topic_checker import verify_user_topics
from core.redis_client import set_cached_last_post
from core.security import URLSecurity
from bot.states import AddChannel, MySources
from bot.keyboards import (
    get_main_menu_inline,
    get_source_list_kb,
    get_destinations_menu,
    get_destinations_inline_kb,
    get_confirm_channel_kb,
    get_cancel_kb
)
from bot.utils.menu_message import update_or_send_menu, delete_menu_message_with_delay, MENU_MESSAGE_ID_KEY


# Настройка логгера
logger = logging.getLogger(__name__)

router = Router(name="sources")


USERNAME_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$")

# Константы для кнопок источников
ADD_CHANNEL_BUTTONS = ["✚ Добавить канал", "✚ Add channel", "✚ Додати канал", "✚ Дадаць канал"]
MY_SOURCES_BUTTONS = ["📚 Мои источники", "📚 My sources", "📚 Мої джерела", "📚 Маё крыніцы"]


@router.message(Command("add"))
@router.message(F.text.in_(ADD_CHANNEL_BUTTONS))
async def cmd_add_channel(message: Message, state: FSMContext, session: AsyncSession, get_text: callable, bot: Bot = None):
    """Начать процесс добавления канала — обновляем текущее сообщение."""

    logger.info(f"📥 Пользователь {message.from_user.id} начал добавление канала")

    # Если bot не передан, используем message.bot
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
async def process_channel_username(message: Message, state: FSMContext, session: AsyncSession, get_text: callable, bot: Bot = None):
    """Обработать ввод username канала или ссылки — сразу проверяем и добавляем."""
    # Если bot не передан, используем message.bot
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
        from core.parser.youtube_simple import get_parser
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
                text=get_text(['sources', 'telegram_not_found'], error=html.escape(error)),
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

    # ========== ПРОВЕРКА ГРУПП И ОТПРАВКА ВЫБОРА ТЕМЫ ==========
    await process_channel_after_check(message, state, session, get_text, bot, is_youtube)


async def process_channel_after_check(message: Message, state: FSMContext, session: AsyncSession, get_text: callable, bot: Bot, is_youtube: bool):
    """Проверить группы и отправить выбор темы."""
    data = await state.get_data()
    source_type = data.get("source_type")
    source_global_id = data.get("source_global_id")
    
    # Получаем все назначения
    destinations = await get_user_destinations(message.from_user.id, session, only_existing_topics=False)
    if not destinations:
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

    # Фильтруем destinations
    alive_topic_identifiers = {t.topic_identifier for t in alive_topics}
    filtered_destinations = [
        d for d in destinations
        if d.get("topic_identifier") in alive_topic_identifiers
    ]

    # Сохраняем данные
    if source_type == "telegram":
        username = data.get("source_username")
        source_global_id = f"tg_channel_{username}"
        await state.update_data(
            source_global_id=source_global_id,
            destinations=filtered_destinations,
            first_post=data.get("first_post"),
            first_post_id=data.get("first_post_id"),
            source_title=data.get("source_title"),
            source_username=username,
            source_type="telegram",
            source_created_now=True
        )
    elif source_type == "youtube":
        channel_id = data.get("channel_id")
        source_global_id = f"yt_channel_{channel_id}"
        await state.update_data(
            source_global_id=source_global_id,
            destinations=filtered_destinations,
            first_video=data.get("last_video"),
            first_video_id=data.get("last_video_id"),
            source_title=data.get("source_title"),
            channel_id=channel_id,
            youtube_username=data.get("youtube_username"),
            source_type="youtube",
            source_created_now=True
        )

    # Отправляем выбор темы
    inline_kb = get_destinations_inline_kb(filtered_destinations, page=0, get_text=get_text)

    # 1. Удаляем старое сообщение через 2с
    await delete_menu_message_with_delay(
        bot=bot,
        chat_id=message.from_user.id,
        state=state,
        delay=2
    )

    # 2. Отправляем НОВОЕ сообщение с выбором темы
    new_msg = await bot.send_message(
        chat_id=message.from_user.id,
        text=get_text(['sources', 'add_saved']),
        parse_mode="HTML",
        reply_markup=inline_kb
    )

    # 3. Сохраняем новый message_id
    await state.update_data({MENU_MESSAGE_ID_KEY: new_msg.message_id})
    await state.set_state(AddChannel.choose_destination)


async def cancel_add_channel_flow(callback, bot: Bot, chat_id: int, state: FSMContext, session: AsyncSession, get_text: callable):
    """Отмена добавления канала — возврат в главное меню."""
    from core.models import ContentSource
    from sqlalchemy import delete

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


# ========== CALLBACK HANDLERS ДЛЯ WAITING_FOR_USERNAME ==========
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


# ========== СТАРЫЕ ХЕНДЛЕРЫ БОЛЬШЕ НЕ ИСПОЛЬЗУЮТСЯ ==========
# confirm_add_channel и cancel_add_channel удалены, т.к. теперь используется
# process_channel_after_check и cancel_add_channel_flow
# =======================================================================


# ========== INLINE CALLBACK HANDLERS FOR DESTINATIONS ==========

@router.callback_query(AddChannel.choose_destination, F.data.startswith("dest_select:"))
async def process_destination_inline(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
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


async def finalize_destination_choice(
    callback: CallbackQuery,
    chosen: dict,
    data: dict,
    state: FSMContext,
    session: AsyncSession,
    get_text: callable
):
    """Финальная обработка выбора destination - отправка поста"""
    
    source_global_id = data.get("source_global_id")
    source_type = data.get("source_type", "telegram")
    
    try:
        chat_id = chosen["chat_id"]
        topic_identifier = chosen["topic_identifier"]
        
        logger.info(f"🔄 Добавление {source_type} канала в {chosen['display_name']}")
        
        # ========== 1. ПРОВЕРЯЕМ ИСТОЧНИК ==========
        source_stmt = select(ContentSource).where(ContentSource.source_global_id == source_global_id)
        source_result = await session.execute(source_stmt)
        source = source_result.scalar_one_or_none()
        
        if not source:
            # Создаём, если вдруг не создался
            if source_type == "telegram":
                username = data.get("source_username")
                title = data.get("source_title")
                source, _ = await get_or_create_content_source(
                    session=session,
                    source_global_id=source_global_id,
                    source_type="telegram",
                    telegram_username=username,
                    channel_title=title
                )
            elif source_type == "youtube":
                channel_id = data.get("channel_id")
                username = data.get("youtube_username")
                title = data.get("source_title")
                feed_url = data.get("feed_url")
                channel_language = data.get("channel_language", 'en')
                
                source, _ = await get_or_create_content_source(
                    session=session,
                    source_global_id=source_global_id,
                    source_type="youtube",
                    feed_url=feed_url,
                    channel_title=title
                )
                # Добавляем специфичные поля
                source.youtube_username = username
                source.channel_language = channel_language
            
            logger.info(f"✅ Создан источник в процессе добавления: {source_global_id}")
        
        # ========== 2. ПОДПИСКА ГРУППЫ ==========
        subscription = await get_source_subscription(chat_id, source_global_id, session)
        if not subscription:
            subscription = await create_source_subscription(
                chat_id=chat_id,
                source_global_id=source_global_id,
                added_by_id=callback.from_user.id,
                session=session
            )
            logger.info(f"✅ Создана подписка ID: {subscription.subscription_id}")
        else:
            logger.info(f"✅ Подписка уже существует ID: {subscription.subscription_id}")
        
        # ========== 3. НАЗНАЧЕНИЕ В ТЕМУ ==========
        existing_stmt = select(TopicSourceAssignment).where(
            and_(
                TopicSourceAssignment.topic_identifier == topic_identifier,
                TopicSourceAssignment.subscription_id == subscription.subscription_id
            )
        )
        existing_result = await session.execute(existing_stmt)
        existing_assignment = existing_result.scalar_one_or_none()

        if existing_assignment:
            await update_or_send_menu(
                bot=callback.bot,
                chat_id=callback.from_user.id,
                text=get_text(['sources', 'destination_already_exists'], destination=chosen['display_name']),
                keyboard=get_main_menu_inline(get_text),
                state=state
            )
            await state.clear()
            return
        
        assignment = await create_topic_assignment(
            topic_identifier=topic_identifier,
            subscription_id=subscription.subscription_id,
            session=session
        )
        logger.info(f"✅ Создано назначение ID: {assignment.assignment_id}")

        # ========== 4. СОХРАНЯЕМ ВСЁ ==========
        await session.commit()

        # ========== 5. 🎯 ОТПРАВЛЯЕМ ТОЛЬКО 1 ПОСТ! ==========
        if source_type == "telegram":
            first_post = data.get("first_post")
            first_post_id = data.get("first_post_id")
            username = data.get("source_username")

            if first_post:
                try:
                    source_name = f"@{username}"
                    text = first_post.get('text', '').strip()
                    if not text:
                        text = "📎 [Медиа-сообщение]"

                    message_text = f"<b>{source_name}</b>\n\n{text}"

                    if first_post.get('post_id'):
                        message_text += f"\n\n<a href='https://t.me/{username}/{first_post_id}'>🔗 Оригинал</a>"

                    await callback.message.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=chosen.get('thread_id'),
                        text=message_text,
                        parse_mode="HTML",
                        disable_web_page_preview=False
                    )
                    logger.info(f"✅ Отправлен первый пост ID: {first_post_id}")

                    # ✅ ОБНОВЛЯЕМ last_seen_at ПОСЛЕ УСПЕШНОЙ ОТПРАВКИ
                    topic_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
                    topic_result = await session.execute(topic_stmt)
                    topic = topic_result.scalar_one_or_none()
                    if topic:
                        topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        await session.commit()
                        logger.debug(f"✅ last_seen_at обновлён для темы {topic.topic_name}")

                except Exception as send_error:
                    logger.error(f"❌ Ошибка отправки первого поста: {send_error}")

        elif source_type == "youtube":
            first_video_id = data.get("first_video_id")
            username = data.get("youtube_username") or data.get("channel_id", "")[:8]
            channel_title = data.get("source_title")

            if first_video_id:
                try:
                    if channel_title:
                        source_name = f"{channel_title} | @{username}"
                    else:
                        source_name = f"YouTube канал @{username}"

                    video_url = f"https://youtu.be/{first_video_id}"
                    message_text = f"{video_url}\n\n<b>{source_name}</b>"

                    await callback.message.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=chosen.get('thread_id'),
                        text=message_text,
                        parse_mode="HTML",
                        disable_web_page_preview=False
                    )

                    logger.info(f"✅ Отправлено первое видео: {first_video_id}")

                    # ✅ ОБНОВЛЯЕМ last_seen_at ПОСЛЕ УСПЕШНОЙ ОТПРАВКИ
                    topic_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
                    topic_result = await session.execute(topic_stmt)
                    topic = topic_result.scalar_one_or_none()
                    if topic:
                        topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        await session.commit()
                        logger.debug(f"✅ last_seen_at обновлён для темы {topic.topic_name}")

                except Exception as send_error:
                    logger.error(f"❌ Ошибка отправки первого видео: {send_error}")
        
        # ========== 6. УСПЕХ! ==========
        # 1. Удаляем старое навигационное сообщение ЧЕРЕЗ 2 СЕКУНДЫ
        await delete_menu_message_with_delay(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            state=state,
            delay=2
        )

        # 2. Отправляем НОВОЕ сообщение с результатом
        if source_type == "telegram":
            username = data.get("source_username")
            first_post_id = data.get("first_post_id")
            result_msg = await callback.bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text(['sources', 'destination_success_telegram'],
                        username=username,
                        post_id=first_post_id,
                        destination=chosen['display_name'])
            )
            logger.info(f"📤 Отправлено сообщение о результате: {result_msg.message_id}")
            logger.info(f"✅ Канал @{username} добавлен, отправлен 1 пост (ID: {first_post_id})")

        elif source_type == "youtube":
            username = data.get("youtube_username")
            first_video_id = data.get("first_video_id")
            result_msg = await callback.bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text(['sources', 'destination_success_youtube'],
                        username=username,
                        video_id=first_video_id,
                        destination=chosen['display_name'])
            )
            logger.info(f"📤 Отправлено сообщение о результате: {result_msg.message_id}")
            logger.info(f"✅ YouTube канал @{username} добавлен, отправлено 1 видео")

        # 3. Отправляем НОВОЕ главное меню
        main_menu_msg = await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text(['common', 'menu']),
            parse_mode="HTML",
            reply_markup=get_main_menu_inline(get_text)
        )
        logger.info(f"📤 Отправлено новое главное меню: {main_menu_msg.message_id}")

        # 4. Сохраняем новый message_id в состоянии
        await state.update_data({MENU_MESSAGE_ID_KEY: main_menu_msg.message_id})

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка в finalize_destination_choice: {e}", exc_info=True)
        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=get_text(['sources', 'destination_error'], error=str(e)[:200]),
            keyboard=get_main_menu_inline(get_text),
            state=state
        )

    finally:
        # Сохраняем message_id перед очисткой!
        data = await state.get_data()
        menu_message_id = data.get(MENU_MESSAGE_ID_KEY)
        
        await state.clear()
        
        # Восстанавливаем message_id
        if menu_message_id:
            await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})
        
        logger.info(f"✅ Состояние очищено, message_id={menu_message_id} сохранён")


@router.message(AddChannel.choose_destination)
async def process_destination_choice(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """
    Обработать выбор группы/темы.
    ⚠️ ТЕПЕРЬ РАБОТАЕТ ТОЛЬКО ДЛЯ ОТМЕНЫ (текстовое сообщение)
    """
    from core.models import ContentSource
    from sqlalchemy import delete
    
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


# ========== СТАРЫЙ ХЕНДЛЕР /list - ОТКЛЮЧЁН ==========
# Теперь используется my_sources_interactive.py с интерактивной навигацией через черновик
# Старый код удалён, функционал перенесён в bot/handlers/my_sources_interactive.py


# ========== ПРОЧИЕ ХЕНДЛЕРЫ ==========
@router.callback_query(F.data.startswith("src_page:"))
async def navigate_sources(callback: CallbackQuery, session: AsyncSession, get_text: callable, bot: Bot):
    """Навигация по страницам источников - обновляет ВСЁ сообщение"""
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Получаем текст проверки из локализации
    check_text = get_text(['topic_check', 'message'])

    # Проверяем темы пользователя
    from core.utils.topic_checker import verify_user_topics
    alive_topics, deleted_topics, total = await verify_user_topics(user_id, bot, session, check_text)

    # Получаем все источники пользователя (только с живыми темами)
    groups = await get_user_groups(user_id, session, only_existing_topics=True)

    if not groups:
        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=get_text(['sources', 'error_no_groups_short']),
            keyboard=get_main_menu_inline(get_text),
            state=state
        )
        await callback.answer()
        return

    group_ids = [group["chat_id"] for group in groups]

    # Получаем все подписки
    stmt = (
        select(
            ManagedGroup.telegram_chat_id,
            ManagedGroup.telegram_chat_title,
            ContentSource,
            SourceSubscription,
            GroupTopic,
            TopicSourceAssignment
        )
        .join(SourceSubscription, SourceSubscription.telegram_chat_id == ManagedGroup.telegram_chat_id)
        .join(ContentSource, ContentSource.source_global_id == SourceSubscription.source_global_id)
        .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
        .join(GroupTopic, GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier)
        .where(ManagedGroup.telegram_chat_id.in_(group_ids))
        .where(GroupTopic.is_exists_in_tg == True)  # Только живые темы
        .order_by(ManagedGroup.telegram_chat_title, GroupTopic.topic_name, ContentSource.source_global_id)
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    # Группируем по чатам и темам
    grouped_data = {}
    
    for row in rows:
        chat_id = row.telegram_chat_id
        chat_title = row.telegram_chat_title or f"Группа {chat_id}"
        source = row[2]
        topic = row[4]
        
        if chat_id not in grouped_data:
            grouped_data[chat_id] = {
                "title": chat_title,
                "topics": {}
            }
        
        if topic.topic_identifier not in grouped_data[chat_id]["topics"]:
            grouped_data[chat_id]["topics"][topic.topic_identifier] = {
                "name": topic.topic_name,
                "thread_id": topic.telegram_thread_id,
                "sources": []
            }
        
        source_icon = "📺" if source.source_type == "youtube" else "📰"
        
        # 🔥 ИСПРАВЛЕНО: используем display_name
        if source.channel_title:
            source_name = source.channel_title
        elif source.source_type == "telegram" and source.telegram_username:
            source_name = f"@{source.telegram_username}"
        elif source.source_type == "youtube" and source.youtube_username:
            source_name = source.youtube_username
        else:
            source_name = "Без названия"
        
        grouped_data[chat_id]["topics"][topic.topic_identifier]["sources"].append({
            "icon": source_icon,
            "name": source_name,
            "type": source.source_type,
            "url": source.public_url,
            "source_global_id": source.source_global_id
        })
    
    # ===== ФОРМИРУЕМ ТЕКСТ =====
    text = get_text(['sources', 'list_title'])
    total_sources = 0
    
    # Считаем общее количество
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            total_sources += len(topic_data["sources"])
    
    # Показываем с учётом страницы
    sources_per_page = 5
    sources_shown = 0
    start_source = page * sources_per_page
    end_source = start_source + sources_per_page
    shown_anything = False
    
    for chat_id, chat_data in grouped_data.items():
        if sources_shown >= end_source:
            break
            
        # Показываем группу только если в ней есть источники на этой странице
        group_has_sources = False
        group_text = get_text(['sources', 'list_group_header'], name=html.escape(chat_data['title']))
        
        for topic_id, topic_data in chat_data["topics"].items():
            if sources_shown >= end_source:
                break
                
            topic_has_sources = False
            topic_text = get_text(['sources', 'list_separator'])
            
            if topic_data["thread_id"] is None:
                topic_text += get_text(['sources', 'list_topic_general'], name=html.escape(topic_data['name']))
            else:
                topic_text += get_text(['sources', 'list_topic'], name=html.escape(topic_data['name']))
            
            for source in topic_data["sources"]:
                if sources_shown >= end_source:
                    break
                    
                if sources_shown >= start_source:
                    # Добавляем ссылку на источник
                    if source['type'] == 'telegram' and source.get('url'):
                        source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                    elif source['type'] == 'youtube' and source.get('url'):
                        source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                    else:
                        source_link = html.escape(source['name'])
                    
                    topic_text += get_text(['sources', 'list_source'], icon=source['icon'], link=source_link)
                    topic_has_sources = True
                    shown_anything = True
                
                sources_shown += 1
            
            if topic_has_sources:
                text += group_text if not group_has_sources else ""
                text += topic_text
                group_has_sources = True
        
        if group_has_sources:
            text += "\n"
    
    if not shown_anything:
        text += get_text(['sources', 'list_page_empty'])
    
    # Если показали не всё, добавляем сообщение
    if sources_shown < total_sources:
        text += get_text(['sources', 'list_more'], count=total_sources - sources_shown)
    
    text += get_text(['sources', 'list_total'], total=total_sources, groups=len(grouped_data))

    # Собираем плоский список для кнопок
    flat_sources = []
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            for source in topic_data["sources"]:
                flat_sources.append(source)

    # Обновляем ВСЁ сообщение через update_or_send_menu
    from bot.utils.menu_message import update_or_send_menu
    
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=get_source_list_kb(flat_sources, topic_title="Источники", page=page, get_text=get_text),
        state=state
    )
    await callback.answer()


@router.callback_query(F.data == "close_sources")
async def close_sources(callback: CallbackQuery, get_text: callable):
    """Закрыть список источников"""
    await callback.message.delete()
    await callback.answer(get_text(['sources', 'list_closed']))


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустышка для неактивных кнопок"""
    await callback.answer()


@router.callback_query(F.data.startswith("del_source:"))
async def delete_source_subscription(callback: CallbackQuery, session: AsyncSession, get_text: callable):
    """Удалить подписку на источник для пользователя/группы (но не из общей БД)"""
    source_global_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    try:
        # Находим подписки пользователя на этот источник
        # (только для его групп, не удаляем из глобального каталога)
        
        # Получаем группы пользователя
        groups = await get_user_groups(user_id, session)
        group_ids = [group["chat_id"] for group in groups]
        
        # Находим все подписки на этот источник в группах пользователя
        stmt = select(SourceSubscription).where(
            and_(
                SourceSubscription.source_global_id == source_global_id,
                SourceSubscription.telegram_chat_id.in_(group_ids)
            )
        )
        result = await session.execute(stmt)
        subscriptions = result.scalars().all()
        
        if not subscriptions:
            await callback.answer(get_text(['sources', 'delete_not_found']))
            return
        
        # Удаляем назначения в темах (TopicSourceAssignment)
        for sub in subscriptions:
            # Удаляем все назначения для этой подписки
            del_assignments = select(TopicSourceAssignment).where(
                TopicSourceAssignment.subscription_id == sub.subscription_id
            )
            assignments_result = await session.execute(del_assignments)
            for assignment in assignments_result.scalars().all():
                await session.delete(assignment)
            
            # Удаляем саму подписку
            await session.delete(sub)

        await session.commit()

        # Показываем обновленный список
        await callback.answer(get_text(['sources', 'delete_success']))
        
        # Обновляем список источников (переходим на первую страницу)
        await update_sources_list(callback.message, session, user_id, page=0, get_text=get_text)
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка удаления подписки: {e}")
        await callback.answer(get_text(['sources', 'delete_error']))


async def update_sources_list(message: Message, session: AsyncSession, user_id: int, page: int = 0, get_text: callable = None):
    """Вспомогательная функция для обновления списка источников"""

    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session)
    if not groups:
        # Для вспомогательной функции без state — используем простое сообщение
        await message.answer(
            get_text(['sources', 'error_no_groups_short']) if get_text else "❌ Нет активных групп"
        )
        return
    
    group_ids = [group["chat_id"] for group in groups]
    
    # Получаем все подписки
    stmt = (
        select(
            ManagedGroup.telegram_chat_id,
            ManagedGroup.telegram_chat_title,
            ContentSource,
            SourceSubscription,
            GroupTopic,
            TopicSourceAssignment
        )
        .join(SourceSubscription, SourceSubscription.telegram_chat_id == ManagedGroup.telegram_chat_id)
        .join(ContentSource, ContentSource.source_global_id == SourceSubscription.source_global_id)
        .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
        .join(GroupTopic, GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier)
        .where(ManagedGroup.telegram_chat_id.in_(group_ids))
        .order_by(ManagedGroup.telegram_chat_title, GroupTopic.topic_name, ContentSource.source_global_id)
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    # Группируем по чатам и темам
    grouped_data = {}
    
    for row in rows:
        chat_id = row.telegram_chat_id
        chat_title = row.telegram_chat_title or f"Группа {chat_id}"
        source = row[2]
        topic = row[4]
        
        if chat_id not in grouped_data:
            grouped_data[chat_id] = {
                "title": chat_title,
                "topics": {}
            }
        
        if topic.topic_identifier not in grouped_data[chat_id]["topics"]:
            grouped_data[chat_id]["topics"][topic.topic_identifier] = {
                "name": topic.topic_name,
                "thread_id": topic.telegram_thread_id,
                "sources": []
            }
        
        source_icon = "📺" if source.source_type == "youtube" else "📰"
        
        # 🔥 ИСПРАВЛЕНО: используем display_name
        if source.channel_title:
            source_name = source.channel_title
        elif source.source_type == "telegram" and source.telegram_username:
            source_name = f"@{source.telegram_username}"
        elif source.source_type == "youtube" and source.youtube_username:
            source_name = source.youtube_username
        else:
            source_name = "Без названия"
        
        grouped_data[chat_id]["topics"][topic.topic_identifier]["sources"].append({
            "icon": source_icon,
            "name": source_name,
            "type": source.source_type,
            "url": source.public_url,
            "source_global_id": source.source_global_id
        })
    
    # ===== ФОРМИРУЕМ ТЕКСТ =====
    text = get_text(['sources', 'list_title']) if get_text else "<b>📚 Ваши подписки по группам</b>\n\n"
    total_sources = 0
    
    # Считаем общее количество
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            total_sources += len(topic_data["sources"])
    
    # Показываем с учётом страницы
    sources_per_page = 5
    sources_shown = 0
    start_source = page * sources_per_page
    end_source = start_source + sources_per_page
    shown_anything = False
    
    for chat_id, chat_data in grouped_data.items():
        if sources_shown >= end_source:
            break
            
        group_has_sources = False
        group_text = f"👥Группа - <b>{html.escape(chat_data['title'])}</b>\n"
        
        for topic_id, topic_data in chat_data["topics"].items():
            if sources_shown >= end_source:
                break
                
            topic_has_sources = False
            topic_text = "    ──────────��──────\n"
            topic_icon = "💬Топик - " if topic_data["thread_id"] is None else "🗨️Топик - "
            topic_text += f"    {topic_icon} <b>{html.escape(topic_data['name'])}</b>\n"
            
            for source in topic_data["sources"]:
                if sources_shown >= end_source:
                    break
                    
                if sources_shown >= start_source:
                    # Добавляем ссылку на источник
                    if source['type'] == 'telegram' and source.get('url'):
                        source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                    elif source['type'] == 'youtube' and source.get('url'):
                        source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                    else:
                        source_link = html.escape(source['name'])
                    
                    topic_text += f"        {source['icon']} {source_link}\n"
                    topic_has_sources = True
                    shown_anything = True
                
                sources_shown += 1
            
            if topic_has_sources:
                text += group_text if not group_has_sources else ""
                text += topic_text
                group_has_sources = True
        
        if group_has_sources:
            text += "\n"
    
    if not shown_anything:
        text += "<i>Нет источников на этой странице</i>\n\n"
    
    # Если показали не всё, добавляем сообщение
    if sources_shown < total_sources:
        text += f"<i>... и ещё {total_sources - sources_shown} источников</i>\n\n"
    
    text += f"<b>📊 Всего подписок:</b> {total_sources}\n"
    text += f"<b>👥 Всего групп:</b> {len(grouped_data)}\n\n"
    text += "<b>🔧 Управление:</b> Выберите источник для управления"
    
    # ===== СОБИРАЕМ flat_sources =====
    flat_sources = []
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            for source in topic_data["sources"]:
                flat_sources.append(source)

    # Обновляем сообщение через update_or_send_menu
    from bot.utils.menu_message import update_or_send_menu
    
    await update_or_send_menu(
        bot=message.bot,
        chat_id=message.from_user.id,
        text=text,
        keyboard=get_source_list_kb(flat_sources, topic_title="Источники", page=page, get_text=get_text),
        state=state
    )

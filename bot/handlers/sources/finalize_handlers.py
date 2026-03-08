"""Финальное добавление канала в выбранную тему."""
import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource, SourceSubscription, TopicSourceAssignment, GroupTopic
from core.services.destination_service import (
    get_source_subscription,
    create_source_subscription,
    create_topic_assignment,
    get_or_create_content_source
)
from bot.keyboards import get_main_menu_inline
from bot.utils.menu_message import update_or_send_menu, delete_menu_message_with_delay, MENU_MESSAGE_ID_KEY

logger = logging.getLogger(__name__)
router = Router(name="sources_finalize")


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
        # Получаем chat_id из выбранной группы (сохранено в state)
        selected_group_chat_id = data.get("selected_group_chat_id")
        chat_id = selected_group_chat_id or chosen.get("chat_id")
        topic_identifier = chosen["topic_identifier"]
        display_name = f"{chosen.get('chat_title', 'Группа')} → {chosen.get('thread_name', 'General')}"

        logger.info(f"🔄 Добавление {source_type} канала в {display_name}")

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
                text=get_text(['sources', 'destination_already_exists'], destination=display_name),
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

            if first_post and first_post_id:
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

                    # ✅ СОХРАНЯЕМ last_successful_post_id В БД И REDIS
                    source.last_successful_post_id = int(first_post_id)
                    source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    # Обновляем Redis кеш
                    from core.redis_client import set_cached_last_post
                    await set_cached_last_post(username, int(first_post_id))
                    logger.info(f"💾 last_successful_post_id={first_post_id} сохранён в БД и Redis для @{username}")

                    # ✅ ОБНОВЛЯЕМ last_seen_at ПОСЛЕ УСПЕШНОЙ ОТПРАВКИ
                    topic_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
                    topic_result = await session.execute(topic_stmt)
                    topic = topic_result.scalar_one_or_none()
                    if topic:
                        topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    # Сохраняем все изменения (source + topic)
                    await session.commit()
                    logger.debug(f"✅ last_seen_at обновлён для темы {topic.topic_name if topic else 'N/A'}")

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

                    # ✅ СОХРАНЯЕМ last_video_id И last_successful_post_id В БД
                    source.last_video_id = first_video_id
                    source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    # Для обратной совместимости сохраняем числовой хеш
                    import hashlib
                    video_id_num = int(hashlib.md5(first_video_id.encode()).hexdigest()[:15], 16) % (10**15)
                    source.last_successful_post_id = video_id_num
                    
                    logger.info(f"💾 last_video_id={first_video_id} сохранён в БД для YouTube @{username}")

                    # ✅ ОБНОВЛЯЕМ last_seen_at ПОСЛЕ УСПЕШНОЙ ОТПРАВКИ
                    topic_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
                    topic_result = await session.execute(topic_stmt)
                    topic = topic_result.scalar_one_or_none()
                    if topic:
                        topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    # Сохраняем все изменения (source + topic)
                    await session.commit()
                    logger.debug(f"✅ last_seen_at обновлён для темы {topic.topic_name if topic else 'N/A'}")

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
                        destination=display_name)
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
                        destination=display_name)
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

# core/services/monitoring/post_sender.py
"""
Отправка постов в темы.
Версия: 6.9 — HTML форматирование + умное превью + кнопка на оригинал + проверка медиа
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set

import aiohttp
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.models import ContentSource, ManagedGroup, GroupTopic
from core.utils.html_sanitizer import html_to_plain_text

logger = logging.getLogger(__name__)


class PostSender:
    """Отправка постов в темы. HTML + превью + кнопка."""

    def __init__(self, bot):
        self.bot = bot

        # Кэш неактивных тем/групп (5 минут)
        self._topic_cache: Dict[str, datetime] = {}
        self._group_cache: Dict[int, datetime] = {}
        self._cache_ttl = 300

    def _is_topic_cached_inactive(self, topic_identifier: str) -> bool:
        """Проверить, есть ли тема в кэше неактивных."""
        if topic_identifier in self._topic_cache:
            last_check = self._topic_cache[topic_identifier]
            if (datetime.now(timezone.utc).replace(tzinfo=None) - last_check).total_seconds() < self._cache_ttl:
                return True
        return False

    def _is_group_cached_inactive(self, chat_id: int) -> bool:
        """Проверить, есть ли группа в кэше неактивных."""
        if chat_id in self._group_cache:
            last_check = self._group_cache[chat_id]
            if (datetime.now(timezone.utc).replace(tzinfo=None) - last_check).total_seconds() < self._cache_ttl:
                return True
        return False

    # ======================================================================
    # ОТПРАВКА ПОСТА
    # ======================================================================

    async def send_to_assignment(
        self,
        post: Dict,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ) -> bool:
        """Отправить пост с умным превью и кнопкой на оригинал."""
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта: {assignment.topic_identifier}")
                return False

            # 📎 Проверка готовности медиа (количество + доступность)
            await self._check_media_ready(post)

            # Форматируем HTML текст
            message_text = self._format_telegram_post_message(post, source)

            # Кнопка на оригинал
            keyboard = self._get_original_post_keyboard(post, source)

            # Отправляем с превью
            logger.info(f"📤 Отправляю пост в тему '{topic.topic_name}'")
            success = await self._send_message_with_retry(
                chat_id=topic.telegram_chat_id,
                text=message_text,
                thread_id=topic.telegram_thread_id,
                keyboard=keyboard,
                post=post,
                source=source
            )

            if success:
                topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                updated_topics.add(topic)
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка отправки поста: {e}", exc_info=False)
            return False

    async def _check_media_ready(self, post: Dict):
        """
        Проверяет готовность медиа перед отправкой.

        Логика:
        1. Логирует сколько медиа и какие типы
        2. Проверяет HEAD запросом первое медиа
        3. Если не доступно → ждёт 60 сек, проверяет снова (макс 2 попытки)
        """
        media_items = post.get('media', [])
        if not media_items:
            return

        # Логируем количество и типы
        types = [m.get('type', 'unknown') for m in media_items]
        type_counts = {}
        for t in types:
            type_counts[t] = type_counts.get(t, 0) + 1

        type_summary = ', '.join(f'{count}x{t}' for t, count in type_counts.items())
        logger.info(f"📎 Медиа в посте: {len(media_items)} шт ({type_summary})")

        # Проверяем доступность первого медиа
        first_media = media_items[0]
        media_url = first_media.get('url', '')
        media_type = first_media.get('type', 'photo')

        if not media_url:
            logger.warning(f"⚠️ Медиа {media_type} без URL, пропускаем проверку")
            return

        max_attempts = 2
        for attempt in range(max_attempts):
            available = await self._check_media_available(media_url)

            if available:
                logger.info(f"✅ Медиа {media_type} доступно (попытка {attempt + 1})")
                return

            if attempt < max_attempts - 1:
                wait_time = 60
                logger.info(f"⏳ Медиа {media_type} ещё не подгрузилось, жду {wait_time}с...")
                await asyncio.sleep(wait_time)
            else:
                logger.warning(f"⚠️ Медиа {media_type} не доступно после {max_attempts} попыток, отправляю как есть")

    async def _check_media_available(self, media_url: str) -> bool:
        """Проверить HEAD запросом что медиа доступно на серверах Telegram."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://t.me/',
            }
            async with aiohttp.ClientSession() as session:
                async with session.head(media_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status == 200
        except asyncio.TimeoutError:
            logger.debug(f"⏱️ Таймаут HEAD запроса к {media_url[:60]}...")
            return False
        except Exception as e:
            logger.debug(f"⚠️ Ошибка HEAD запроса к {media_url[:60]}: {e}")
            return False

    # ======================================================================
    # ОТПРАВКА С ПРЕВЬЮ
    # ======================================================================

    async def _send_message_with_retry(
        self,
        chat_id: int,
        text: str,
        thread_id: Optional[int] = None,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        post: Optional[Dict] = None,
        source: Optional[ContentSource] = None,
        max_retries: int = 3
    ) -> bool:
        """Отправить сообщение с умным превью."""

        # Определяем превью
        link_preview = LinkPreviewOptions(is_disabled=True)
        if post and source:
            link_preview = self._get_link_preview_options(post, source)

        for attempt in range(max_retries):
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=text,
                    parse_mode="HTML",
                    link_preview_options=link_preview,
                    reply_markup=keyboard
                )
                return True

            except Exception as e:
                error = str(e).lower()

                # Бота кикнули / запретили
                if "forbidden" in error or "bot was kicked" in error or "not enough rights" in error:
                    logger.error(f"👢 Бот потерял доступ к группе {chat_id}")
                    self._group_cache[chat_id] = datetime.now(timezone.utc).replace(tzinfo=None)
                    await self._mark_group_inactive(chat_id)
                    return False

                # Тема удалена
                elif "message thread not found" in error:
                    logger.error(f"❌ Тема {thread_id} не найдена в чате {chat_id}")
                    topic_key = f"{chat_id}:{thread_id}"
                    self._topic_cache[topic_key] = datetime.now(timezone.utc).replace(tzinfo=None)
                    await self._mark_topic_deleted(chat_id, thread_id)
                    return False

                # Flood control
                elif "too many requests" in error or "flood" in error:
                    wait = 5 * (attempt + 1)
                    logger.warning(f"⏳ Flood control, жду {wait}с...")
                    await asyncio.sleep(wait)

                # Чат не найден
                elif "chat not found" in error:
                    logger.error(f"❌ Чат {chat_id} не найден!")
                    self._group_cache[chat_id] = datetime.now(timezone.utc).replace(tzinfo=None)
                    return False

                # Ошибка парсинга HTML → plain text
                elif "can't parse entities" in error or "bad request" in error:
                    logger.warning(f"⚠️ Ошибка парсинга HTML, fallback на plain text")
                    safe_text = html_to_plain_text(text)
                    await self.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=thread_id,
                        text=safe_text,
                        link_preview_options=link_preview,
                        reply_markup=keyboard
                    )
                    return True

                # Слишком длинное сообщение
                elif "message is too long" in error:
                    text = text[:3000] + "...\n\n[сообщение обрезано]"
                    if attempt < max_retries - 1:
                        continue
                    return False

                # Остальные ошибки
                else:
                    if attempt < max_retries - 1:
                        wait = 2 * (attempt + 1)
                        logger.warning(f"⏳ Жду {wait}с...")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"❌ Все попытки исчерпаны: {e}")
                        return False

        return False

    # ======================================================================
    # LINK PREVIEW OPTIONS
    # ======================================================================

    def _get_link_preview_options(
        self,
        post: Dict,
        source: ContentSource
    ) -> Optional[LinkPreviewOptions]:
        """Всегда включаем превью — даже для текстовых постов."""
        username = source.telegram_username
        post_id = post.get('post_id')

        if not username or not post_id:
            return LinkPreviewOptions(is_disabled=True)

        # Обычная ссылка на пост — открывает в Telegram app
        url = f"https://t.me/{username}/{post_id}"

        return LinkPreviewOptions(
            is_disabled=False,
            url=url,
            prefer_small_media=False,
            prefer_large_media=True,
            show_above_text=True
        )

    # ======================================================================
    # КНОПКА
    # ======================================================================

    def _get_original_post_keyboard(self, post: Dict, source: ContentSource) -> Optional[InlineKeyboardMarkup]:
        """Кнопка с названием канала."""
        post_id = post.get('post_id')
        username = source.telegram_username
        channel_title = source.channel_title

        if not post_id or not username:
            return None

        url = f"https://t.me/{username}/{post_id}"
        button_text = f"📢 {channel_title}" if channel_title else f"📢 @{username}"

        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=url)]
        ])

    # ======================================================================
    # CLEANUP
    # ======================================================================

    async def _mark_group_inactive(self, chat_id: int):
        """Пометить группу как неактивную."""
        try:
            async with async_session() as cleanup_session:
                stmt = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
                result = await cleanup_session.execute(stmt)
                group = result.scalar_one_or_none()
                if group:
                    group.is_bot_active_in_group = False
                    group.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    await cleanup_session.commit()
                    logger.info(f"✅ Группа {chat_id} помечена как неактивная")
        except Exception as db_error:
            logger.error(f"❌ Не удалось обновить статус группы: {db_error}")

    async def _mark_topic_deleted(self, chat_id: int, thread_id: int):
        """Пометить тему как удалённую."""
        try:
            topic_identifier = f"{chat_id}:{thread_id}" if thread_id else f"{chat_id}:0"
            async with async_session() as cleanup_session:
                stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
                result = await cleanup_session.execute(stmt)
                topic = result.scalar_one_or_none()
                if topic:
                    topic.is_exists_in_tg = False
                    await cleanup_session.commit()
                    logger.info(f"✅ Тема {topic_identifier} помечена как удалённая")
        except Exception as db_error:
            logger.error(f"❌ Не удалось обновить статус темы: {db_error}")

    # ======================================================================
    # ФОРМАТИРОВАНИЕ
    # ======================================================================

    def _format_telegram_post_message(self, post: Dict, source: ContentSource) -> str:
        """Форматирование текста поста (HTML)."""
        text = post.get('text', '').strip()
        if not text:
            text = "📎 [Медиа-сообщение]"

        if source.channel_title:
            source_name = f"{source.channel_title} | @{source.telegram_username}"
        else:
            source_name = f"@{source.telegram_username}"

        timestamp = post.get('timestamp')
        time_str = ""
        if timestamp:
            try:
                time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M")
            except Exception:
                pass

        message = f"<b>{source_name}</b>\n"
        if time_str:
            message += f"<i>{time_str}</i>\n\n"

        message += text

        if len(message) > 4000:
            message = message[:3997] + "..."

        return message

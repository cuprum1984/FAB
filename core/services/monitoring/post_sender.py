# core/services/monitoring/post_sender.py
"""
Отправка постов в темы (медиа/текст).
Версия: 6.2 — Оптимизация масштабирования
Изменения:
- Убран session.flush() после каждой отправки
- Изоляция ошибок — raise заменён на логирование
- Отдельные сессии для cleanup операций
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource, ManagedGroup, GroupTopic
from core.database import async_session
from sqlalchemy import select

logger = logging.getLogger(__name__)


class PostSender:
    """
    Отправка постов в темы.
    Версия 6.2: Без session.flush(), с изоляцией ошибок.
    """

    def __init__(self, bot):
        self.bot = bot
        
        # ✅ КЭШ СТАТУСОВ ТЕМ (LRU-like, 5 минут)
        self._topic_cache: Dict[str, datetime] = {}
        self._group_cache: Dict[int, datetime] = {}
        self._cache_ttl = 300  # 5 минут

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

    async def send_media_to_assignment(
        self,
        post: Dict,
        file_id: str,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ):
        """
        Отправить медиа с file_id.
        updated_topics: множество topic_id для последующего bulk update
        """
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта или не существует: {assignment.topic_identifier}")
                return False

            # ✅ ПРОВЕРКА КЭША
            topic_key = f"{topic.telegram_chat_id}:{topic.telegram_thread_id}"
            if self._is_topic_cached_inactive(topic_key):
                logger.debug(f"⏭️ Тема {topic_key} в кэше неактивных, пропускаем")
                return False

            text = post.get('text', '').strip()

            if source.channel_title:
                source_name = f"{source.channel_title} | @{source.telegram_username}"
            else:
                source_name = f"@{source.telegram_username}"

            caption = f"<b>{source_name}</b>\n\n{text}"
            if len(caption) > 1024:
                caption = caption[:1021] + "..."

            logger.info(f"📤 Отправляю медиа в тему '{topic.topic_name}' (chat_id={topic.telegram_chat_id}, thread_id={topic.telegram_thread_id})")

            success = False

            # Попытка отправить как фото
            try:
                await self.bot.send_photo(
                    chat_id=topic.telegram_chat_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    message_thread_id=topic.telegram_thread_id
                )
                logger.info(f"✅ Медиа отправлено в тему '{topic.topic_name}'")
                success = True

            except Exception as photo_error:
                logger.warning(f"⚠️ Не удалось отправить как фото: {photo_error}")

                # Попытка отправить как документ
                try:
                    await self.bot.send_document(
                        chat_id=topic.telegram_chat_id,
                        document=file_id,
                        caption=caption,
                        parse_mode="HTML",
                        message_thread_id=topic.telegram_thread_id
                    )
                    logger.info(f"✅ Документ отправлен в тему '{topic.topic_name}'")
                    success = True

                except Exception as doc_error:
                    logger.error(f"❌ Не удалось отправить медиа: {doc_error}")
                    # Пробуем отправить текст
                    success = await self._send_text_only(post, assignment, source, session, updated_topics)

            # ✅ ОБНОВЛЯЕМ last_seen_at (только标记, без flush!)
            if success:
                topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                updated_topics.add(topic)  # Добавляем в множество для bulk update
                return True

            return False

        except Exception as e:
            # ✅ ИЗОЛЯЦИЯ ОШИБОК — не прерываем поток, логируем
            logger.error(f"❌ Ошибка отправки медиа: {e}", exc_info=False)  # exc_info=False для краткости
            return False

    async def _send_text_only(
        self,
        post: Dict,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ) -> bool:
        """Отправить только текст (вспомогательный метод)"""
        try:
            topic = assignment.topic
            if not topic or topic.is_closed:
                return False

            message_text = self._format_telegram_post_message(post, source)

            success = await self._send_message_with_retry(
                chat_id=topic.telegram_chat_id,
                text=message_text,
                thread_id=topic.telegram_thread_id
            )

            if success:
                topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                updated_topics.add(topic)
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}", exc_info=False)
            return False

    async def send_text_to_assignment(
        self,
        post: Dict,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ):
        """
        Отправить только текст.
        updated_topics: множество topic_id для последующего bulk update
        """
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта или не существует: {assignment.topic_identifier}")
                return False

            # ✅ ПРОВЕРКА КЭША
            topic_key = f"{topic.telegram_chat_id}:{topic.telegram_thread_id}"
            if self._is_topic_cached_inactive(topic_key):
                logger.debug(f"⏭️ Тема {topic_key} в кэше неактивных, пропускаем")
                return False

            message_text = self._format_telegram_post_message(post, source)

            logger.info(f"📤 Отправляю текст в тему '{topic.topic_name}' (chat_id={topic.telegram_chat_id}, thread_id={topic.telegram_thread_id})")

            success = await self._send_message_with_retry(
                chat_id=topic.telegram_chat_id,
                text=message_text,
                thread_id=topic.telegram_thread_id
            )

            # ✅ ОБНОВЛЯЕМ last_seen_at (только标记, без flush!)
            if success:
                topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                updated_topics.add(topic)  # Добавляем в множество для bulk update
                return True

            return False

        except Exception as e:
            # ✅ ИЗОЛЯЦИЯ ОШИБОК — не прерываем поток
            logger.error(f"❌ Ошибка отправки текста: {e}", exc_info=False)
            return False

    async def _send_message_with_retry(
        self,
        chat_id: int,
        text: str,
        thread_id: Optional[int] = None,
        max_retries: int = 3
    ) -> bool:
        """Отправить сообщение с повторными попытками. Возвращает True при успехе."""
        
        for attempt in range(max_retries):
            try:
                logger.info(f"📤 Попытка {attempt + 1}/{max_retries}: отправка в chat_id={chat_id}, thread_id={thread_id}")

                await self.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )

                logger.info(f"✅ Сообщение успешно отправлено в chat_id={chat_id}, thread_id={thread_id}")
                return True

            except Exception as e:
                error = str(e).lower()
                error_type = type(e).__name__

                logger.error(f"❌ Ошибка отправки (попытка {attempt + 1}): {error_type} - {e}")

                # Если бота кикнули из группы или запретили отправку
                if "forbidden" in error or "bot was kicked" in error or "not enough rights" in error:
                    logger.error(f"👢 Бот потерял доступ к группе {chat_id}")
                    
                    # ✅ КЭШИРУЕМ неактивную группу
                    self._group_cache[chat_id] = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    # ✅ ОТДЕЛЬНАЯ СЕССИЯ для cleanup (не конфликтует с основной)
                    await self._mark_group_inactive(chat_id)
                    return False

                # Если тема удалена в Telegram
                elif "message thread not found" in error:
                    logger.error(f"❌ Тема {thread_id} не найдена в чате {chat_id}")
                    
                    # ✅ КЭШИРУЕМ удалённую тему
                    topic_key = f"{chat_id}:{thread_id}"
                    self._topic_cache[topic_key] = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    # ✅ ОТДЕЛЬНАЯ СЕССИЯ для cleanup
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

                # Сообщение слишком длинное
                elif "message is too long" in error:
                    logger.warning(f"⚠️ Сообщение слишком длинное, обрезаю...")
                    text = text[:3000] + "...\n\n[сообщение обрезано]"
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error(f"❌ Не удалось отправить даже после обрезания")
                        return False

                # Остальные ошибки
                else:
                    if attempt < max_retries - 1:
                        wait = 2 * (attempt + 1)
                        logger.warning(f"⏳ Неизвестная ошибка, жду {wait}с...")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"❌ Все попытки исчерпаны: {e}")
                        return False

        return False

    # ----------------------------------------------------------------------
    # ✅ CLEANUP МЕТОДЫ С ОТДЕЛЬНЫМИ СЕССИЯМИ
    # ----------------------------------------------------------------------

    async def _mark_group_inactive(self, chat_id: int):
        """Пометить группу как неактивную (отдельная сессия)"""
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
        """Пометить тему как удалённую (отдельная сессия)"""
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

    def _format_telegram_post_message(self, post: Dict, source: ContentSource) -> str:
        """Форматирование текста Telegram поста"""
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
            except:
                pass

        message = f"<b>{source_name}</b>\n"
        if time_str:
            message += f"<i>{time_str}</i>\n\n"

        message += text

        if post.get('post_id') and source.telegram_username:
            message += f"\n\n<a href='https://t.me/{source.telegram_username}/{post['post_id']}'>🔗 Оригинал</a>"

        if len(message) > 4000:
            message = message[:3997] + "..."

        return message


# core/services/monitoring/post_sender.py
"""
Отправка постов в темы (медиа/текст).
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from core.models import ContentSource, ManagedGroup, GroupTopic
from core.database import async_session
from sqlalchemy import select

logger = logging.getLogger(__name__)


class PostSender:
    """Отправка постов в темы."""

    def __init__(self, bot):
        self.bot = bot

    async def send_media_to_assignment(self, post: Dict, file_id: str, assignment, source: ContentSource):
        """Отправить медиа с file_id"""
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта или не существует: {assignment.topic_identifier}")
                return

            text = post.get('text', '').strip()

            # 🔥 ИСПРАВЛЕНО: используем channel_title для отображения
            if source.channel_title:
                source_name = f"{source.channel_title} | @{source.telegram_username}"
            else:
                source_name = f"@{source.telegram_username}"

            caption = f"<b>{source_name}</b>\n\n{text}"
            if len(caption) > 1024:
                caption = caption[:1021] + "..."

            logger.info(f"📤 Отправляю медиа в тему '{topic.topic_name}' (chat_id={topic.telegram_chat_id}, thread_id={topic.telegram_thread_id})")

            try:
                await self.bot.send_photo(
                    chat_id=topic.telegram_chat_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    message_thread_id=topic.telegram_thread_id
                )
                logger.info(f"✅ Медиа отправлено в тему '{topic.topic_name}'")
                return

            except Exception as photo_error:
                logger.warning(f"⚠️ Не удалось отправить как фото: {photo_error}")

                try:
                    await self.bot.send_document(
                        chat_id=topic.telegram_chat_id,
                        document=file_id,
                        caption=caption,
                        parse_mode="HTML",
                        message_thread_id=topic.telegram_thread_id
                    )
                    logger.info(f"✅ Документ отправлен в тему '{topic.topic_name}'")
                    return

                except Exception as doc_error:
                    logger.error(f"❌ Не удалось отправить медиа: {doc_error}")
                    await self.send_text_to_assignment(post, assignment, source)

        except Exception as e:
            logger.error(f"❌ Ошибка отправки медиа: {e}", exc_info=True)
            raise

    async def send_text_to_assignment(self, post: Dict, assignment, source: ContentSource):
        """Отправить только текст"""
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта или не существует: {assignment.topic_identifier}")
                return

            message_text = self._format_telegram_post_message(post, source)

            logger.info(f"📤 Отправляю текст в тему '{topic.topic_name}' (chat_id={topic.telegram_chat_id}, thread_id={topic.telegram_thread_id})")

            await self._send_message_with_retry(
                chat_id=topic.telegram_chat_id,
                text=message_text,
                thread_id=topic.telegram_thread_id
            )

        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}", exc_info=True)
            raise

    async def _send_message_with_retry(
        self,
        chat_id: int,
        text: str,
        thread_id: Optional[int] = None,
        max_retries: int = 3
    ):
        """Отправить сообщение с повторными попытками и подробным логированием ошибок"""
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
                return

            except Exception as e:
                error = str(e).lower()
                error_type = type(e).__name__

                logger.error(f"❌ Ошибка отправки (попытка {attempt + 1}): {error_type} - {e}")

                # ===== НОВАЯ ЛОГИКА ОБРАБОТКИ СПЕЦИФИЧЕСКИХ ОШИБОК =====

                # Если бота кикнули из группы или запретили отправку
                if "forbidden" in error or "bot was kicked" in error or "not enough rights" in error:
                    logger.error(f"👢 Бот потерял доступ к группе {chat_id}, помечаю неактивной")

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

                    return

                # Если тема удалена в Telegram
                elif "message thread not found" in error:
                    logger.error(f"❌ Тема {thread_id} не найдена в чате {chat_id}")

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

                    return

                # Стандартная обработка остальных ошибок
                elif "too many requests" in error or "flood" in error:
                    wait = 5 * (attempt + 1)
                    logger.warning(f"⏳ Flood control, жду {wait}с...")
                    await asyncio.sleep(wait)

                elif "chat not found" in error:
                    logger.error(f"❌ Чат {chat_id} не найден! Бот удалён из группы?")
                    return

                elif "message is too long" in error:
                    logger.warning(f"⚠️ Сообщение слишком длинное, обрезаю...")
                    text = text[:3000] + "...\n\n[сообщение обрезано]"
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error(f"❌ Не удалось отправить даже после обрезания")
                        return

                else:
                    if attempt < max_retries - 1:
                        wait = 2 * (attempt + 1)
                        logger.warning(f"⏳ Неизвестная ошибка, жду {wait}с...")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"❌ Все попытки исчерпаны: {e}")
                        return

    def _format_telegram_post_message(self, post: Dict, source: ContentSource) -> str:
        """Форматирование текста Telegram поста"""
        text = post.get('text', '').strip()
        if not text:
            text = "📎 [Медиа-сообщение]"

        # 🔥 ИСПРАВЛЕНО: используем channel_title для отображения
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


# Импорты в конце для избежания циклических зависимостей


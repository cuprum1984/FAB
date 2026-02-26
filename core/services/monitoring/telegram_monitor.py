# core/services/monitoring/telegram_monitor.py
"""
Проверка Telegram каналов и отправка постов.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource, CachedMedia
from core.parser.telegram_posts import get_new_posts as get_telegram_posts
from core.redis_client import get_cached_last_post, set_cached_last_post
from core.services.destination_service import (
    get_source_last_post_id,
    update_source_last_post_id,
)

logger = logging.getLogger(__name__)


class TelegramMonitor:
    """Мониторинг Telegram каналов."""

    def __init__(self, bot, monitoring_service):
        self.bot = bot
        self.monitoring = monitoring_service

    async def check_telegram_source(self, source: ContentSource, session: AsyncSession):
        """
        Проверить Telegram канал и отправить новые посты.
        """
        if not source.telegram_username:
            logger.warning(f"⚠️ Источник {source.source_global_id} не имеет telegram_username")
            return

        username = source.telegram_username
        source_name = f"@{username}"

        logger.info(f"🔍 Проверяю Telegram канал: {source_name}")
        logger.info(f"   📦 В БД last_successful_post_id = {source.last_successful_post_id}")

        try:
            cached_id = await get_cached_last_post(username)
            logger.info(f"   📦 В Redis cached_id = {cached_id}")

            if source.last_successful_post_id:
                if cached_id != source.last_successful_post_id:
                    logger.warning(
                        f"⚠️ Redis устарел для @{username}: "
                        f"в Redis={cached_id}, в БД={source.last_successful_post_id}. Чиним..."
                    )
                    await set_cached_last_post(username, source.last_successful_post_id)
                    logger.info(f"✅ Redis обновлён: {source.last_successful_post_id}")

            if source.last_successful_post_id is None:
                logger.info(f"🆕 Первый запуск для {source_name}, новых постов нет (уже отправили при добавлении)")
                source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.flush()
                await self.monitoring._reset_source_error_stats(source.source_global_id)
                return

            logger.info(f"✅ В БД есть ID={source.last_successful_post_id}, проверяю новые посты...")

            last_post_id = await get_source_last_post_id(source, session, use_cache=True)
            logger.info(f"   🔍 last_post_id для проверки = {last_post_id}")

            assignments = await self.monitoring._get_source_assignments(source.source_global_id, session)

            if not assignments:
                logger.debug(f"📭 Нет активных назначений для источника {source_name}")
                source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.flush()
                await self.monitoring._reset_source_error_stats(source.source_global_id)
                return

            logger.info(f"   📋 Найдено назначений: {len(assignments)}")

            new_posts = await get_telegram_posts(
                username,
                str(last_post_id) if last_post_id else None,
                first_only=False
            )

            logger.info(f"   📬 Парсер вернул {len(new_posts)} постов")

            if not new_posts:
                logger.debug(f"📭 Нет новых постов в {source_name}")
                source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.flush()
                await self.monitoring._reset_source_error_stats(source.source_global_id)
                return

            logger.info(f"✅ Найдено {len(new_posts)} новых постов в {source_name}")

            # Сохраняем текущий last_post_id для проверок во время цикла
            current_last_id = source.last_successful_post_id
            last_successful_id = None

            for i, post in enumerate(new_posts, 1):
                post_id = post.get('post_id')
                logger.info(f"   📝 Обработка поста {i}/{len(new_posts)}: ID={post_id}")

                try:
                    await self._process_telegram_post(
                        post=post,
                        source=source,
                        assignments=assignments,
                        session=session,
                        current_last_id=current_last_id
                    )

                    if post_id:
                        last_successful_id = post_id

                    if i < len(new_posts):
                        await asyncio.sleep(2.0)

                except Exception as e:
                    logger.error(f"❌ Ошибка обработки поста {post_id}: {e}")
                    await session.rollback()
                    await asyncio.sleep(2.0)
                    continue

            if last_successful_id:
                try:
                    last_id_int = int(last_successful_id)
                    logger.info(f"   💾 ФИНАЛЬНОЕ обновление last_post_id в БД: {last_id_int}")
                    await update_source_last_post_id(source, session, last_id_int)
                except (ValueError, TypeError) as e:
                    logger.error(f"   ❌ Ошибка конвертации финального ID {last_successful_id}: {e}")

            source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.flush()
            await self.monitoring._reset_source_error_stats(source.source_global_id)

            logger.info(f"✅ Обработано {len(new_posts)} постов из {source_name}")

        except Exception as e:
            logger.error(f"❌ Ошибка в _check_telegram_source для {source_name}: {e}", exc_info=True)
            await session.rollback()
            raise

    async def _process_telegram_post(
        self,
        post: Dict,
        source: ContentSource,
        assignments: List,
        session: AsyncSession,
        current_last_id: Optional[int] = None
    ):
        """Обработать один Telegram пост"""
        from core.services.monitoring.post_sender import PostSender
        
        post_id = post.get('post_id')
        if not post_id:
            return

        try:
            post_id_int = int(post_id)
        except:
            return

        post_key = f"{source.source_global_id}:{post_id_int}"
        if post_key in self.monitoring._processed_posts:
            logger.warning(f"⚠️ Пост {post_id_int} уже обработан")
            return

        self.monitoring._processed_posts.add(post_key)

        if current_last_id and post_id_int <= current_last_id:
            logger.debug(f"⏭️ Пропускаю старый пост {post_id_int} (<= {current_last_id})")
            return

        logger.info(f"📝 Новый пост {post_id_int} из {source.telegram_username}")

        media_items = post.get('media', [])
        logger.debug(f"📸 Медиа в посте: {len(media_items)} шт.")

        file_id = None

        if media_items and len(media_items) > 0:
            media = media_items[0]
            media_url = media.get('url')

            if media_url:
                logger.debug(f"🔍 Ищу file_id для source={source.source_global_id}, post_id={post_id}")

                stmt = select(CachedMedia).where(
                    CachedMedia.source_global_id == source.source_global_id,
                    CachedMedia.post_id == post_id
                )
                result = await session.execute(stmt)
                cached = result.scalar_one_or_none()

                if cached:
                    file_id = cached.file_id
                    logger.info(f"✅ Найден file_id в кеше: {file_id}")
                else:
                    logger.debug(f"❌ file_id НЕ НАЙДЕН в кеше")

        post_sender = PostSender(self.bot)
        
        for assignment in assignments:
            try:
                if file_id:
                    await post_sender.send_media_to_assignment(
                        post=post,
                        file_id=file_id,
                        assignment=assignment,
                        source=source
                    )
                else:
                    await post_sender.send_text_to_assignment(post, assignment, source)

                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"❌ Ошибка отправки поста {post_id_int}: {e}")


# Импорты в конце для избежания циклических зависимостей
from sqlalchemy import select

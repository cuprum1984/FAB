# core/services/youtube_simple_service.py
"""
Простой сервис мониторинга YouTube через новый парсер.
Версия: 1.0 (17 февраля 2026)
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import ContentSource, TopicSourceAssignment, SourceSubscription, GroupTopic, ManagedGroup
from core.parser.youtube_simple import get_parser
from core.services.destination_service import update_source_last_post_id

logger = logging.getLogger(__name__)

class YouTubeSimpleMonitoringService:
    """Простой сервис мониторинга YouTube"""
    
    def __init__(self, bot):
        self.bot = bot
        self.parser = get_parser()
        self._processed_videos = set()
    
    async def check_source(self, source: ContentSource, session: AsyncSession):
        """Проверить YouTube канал на новые видео"""
        
        if source.source_type != 'youtube':
            return
        
        # Получаем username
        username = source.youtube_username
        if not username:
            logger.warning(f"⚠️ Источник {source.source_global_id} не имеет youtube_username")
            return
        
        source_name = f"YouTube канал @{username}"
        
        logger.info(f"🔍 Проверяю YouTube канал (простой): {source_name}")
        logger.info(f"   📺 Последнее сохранённое видео: {source.last_video_id}")
        
        try:
            # Получаем последнее видео через простой парсер
            video_id = await self.parser.get_latest_video_id(username)

            if not video_id:
                logger.debug(f"📭 Не удалось получить видео для {source_name}")
                source.last_checked_timestamp = datetime.utcnow()
                await session.flush()
                return

            # Проверяем, новое ли видео
            if source.last_video_id == video_id:
                logger.debug(f"📭 Нет новых видео в {source_name} (последнее: {video_id})")
                source.last_checked_timestamp = datetime.utcnow()
                await session.flush()
                return

            logger.info(f"✅ Найдено НОВОЕ видео в {source_name}: {video_id}")

            # Получаем назначения
            assignments = await self._get_source_assignments(source.source_global_id, session)

            if not assignments:
                logger.debug(f"📭 Нет активных назначений для {source_name}")
                source.last_checked_timestamp = datetime.utcnow()
                await session.flush()
                return

            # Отправляем видео
            await self._send_video(video_id, source, assignments, session)

            # Обновляем информацию в БД
            source.last_video_id = video_id

            # Для обратной совместимости обновляем числовой хеш
            import hashlib
            video_id_num = int(hashlib.md5(video_id.encode()).hexdigest()[:15], 16) % (10**15)
            source.last_successful_post_id = video_id_num

            source.last_checked_timestamp = datetime.utcnow()
            await session.flush()

            logger.info(f"✅ Обработано новое видео {video_id} из {source_name}")

        except Exception as e:
            logger.error(f"❌ Ошибка проверки YouTube канала {source_name}: {e}")
            await session.rollback()
            raise
        
        finally:
            # Случайная задержка между каналами
            await asyncio.sleep(random.uniform(5, 15))
    
    async def _get_source_assignments(self, source_global_id: str, session: AsyncSession) -> List[TopicSourceAssignment]:
        """Получить активные назначения для источника"""
        stmt = (
            select(TopicSourceAssignment)
            .join(SourceSubscription, SourceSubscription.subscription_id == TopicSourceAssignment.subscription_id)
            .join(GroupTopic, GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier)
            .join(ManagedGroup, ManagedGroup.telegram_chat_id == GroupTopic.telegram_chat_id)
            .where(
                and_(
                    SourceSubscription.source_global_id == source_global_id,
                    GroupTopic.is_closed == False,
                    ManagedGroup.is_bot_active_in_group == True
                )
            )
            .options(
                selectinload(TopicSourceAssignment.topic),
                selectinload(TopicSourceAssignment.subscription)
            )
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def _send_video(self, video_id: str, source: ContentSource, assignments: List[TopicSourceAssignment], session: AsyncSession):
        """Отправить видео во все назначения"""
        
        video_url = f"https://youtu.be/{video_id}"
        source_name = f"YouTube канал"
        
        message_text = f"{video_url}\n\n<b>{source_name}</b>"
        
        for assignment in assignments:
            try:
                topic = assignment.topic
                if not topic or topic.is_closed:
                    continue
                
                logger.info(f"📤 Отправляю видео в тему '{topic.topic_name}'")
                
                await self.bot.send_message(
                    chat_id=topic.telegram_chat_id,
                    message_thread_id=topic.telegram_thread_id,
                    text=message_text,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки видео {video_id}: {e}")
    
    async def close(self):
        """Закрыть парсер"""
        await self.parser.close()
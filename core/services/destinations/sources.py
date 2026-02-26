# core/services/destinations/sources.py
"""
Функции для работы с источниками контента (ContentSource).
"""
import logging
from typing import Tuple, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource

logger = logging.getLogger(__name__)


async def get_or_create_content_source(
    session: AsyncSession,
    source_global_id: str,
    source_type: str,
    telegram_username: Optional[str] = None,
    channel_title: Optional[str] = None,
    feed_url: Optional[str] = None,
    youtube_username: Optional[str] = None
) -> Tuple[ContentSource, bool]:
    """
    Получить или создать источник контента.

    Args:
        session: Сессия БД
        source_global_id: Уникальный ID источника
        source_type: Тип источника (telegram/rss/youtube)
        telegram_username: Username Telegram канала
        channel_title: Название канала для отображения
        feed_url: URL RSS/Atom ленты
        youtube_username: Username YouTube канала

    Returns:
        Tuple[ContentSource, bool]: (источник, True если создан)
    """
    try:
        stmt = select(ContentSource).where(ContentSource.source_global_id == source_global_id)
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()

        if source:
            # Обновляем информацию
            if telegram_username and not source.telegram_username:
                source.telegram_username = telegram_username
            if channel_title and not source.channel_title:
                source.channel_title = channel_title
            if feed_url and not source.feed_url:
                source.feed_url = feed_url
            if youtube_username and not source.youtube_username:
                source.youtube_username = youtube_username

            await session.flush()
            return source, False

        # Создаём новый источник
        source = ContentSource(
            source_global_id=source_global_id,
            source_type=source_type,
            telegram_username=telegram_username,
            channel_title=channel_title,
            feed_url=feed_url,
            youtube_username=youtube_username,
            parsing_interval=300
        )

        session.add(source)
        await session.flush()

        return source, True

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка создания источника {source_global_id}: {e}")
        raise

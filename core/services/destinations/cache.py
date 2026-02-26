# core/services/destinations/cache.py
"""
Функции для работы с кешем (last_post_id, Redis cache).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource
from core.redis_client import get_cached_last_post, set_cached_last_post, invalidate_source_cache

logger = logging.getLogger(__name__)


async def get_source_last_post_id(
    source: ContentSource,
    session: AsyncSession,
    use_cache: bool = True
) -> Optional[int]:
    """
    Получить ID последнего успешного поста для источника.
    Использует Redis-кеш при наличии.

    Args:
        source: Источник контента
        session: Сессия БД
        use_cache: Использовать ли Redis-кеш

    Returns:
        ID последнего поста или None
    """
    try:
        if use_cache and source.telegram_username:
            # Пробуем получить из Redis
            cached = await get_cached_last_post(source.telegram_username)
            if cached is not None:
                return cached

        # Берём из БД
        return source.last_successful_post_id

    except Exception as e:
        logger.error(f"❌ Ошибка получения last_post_id для {source.source_global_id}: {e}")
        return source.last_successful_post_id


async def update_source_last_post_id(
    source: ContentSource,
    session: AsyncSession,
    post_id: int,
    update_cache: bool = True
) -> None:
    """
    Обновить ID последнего успешного поста для источника.
    Обновляет Redis-кеш при наличии.

    Args:
        source: Источник контента
        session: Сессия БД
        post_id: ID нового последнего поста
        update_cache: Обновлять ли Redis-кеш
    """
    try:
        # Только если новый ID больше текущего!
        if post_id > (source.last_successful_post_id or 0):
            source.last_successful_post_id = post_id
            source.last_successful_post_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

            if update_cache and source.telegram_username:
                await set_cached_last_post(source.telegram_username, post_id)
                logger.debug(f"✅ Redis кеш обновлён для @{source.telegram_username}: {post_id}")

            await session.commit()
            logger.debug(f"💾 БД обновлена для {source.source_global_id}: last_successful_post_id={post_id}")
        else:
            # Просто обновляем время проверки
            source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.commit()
            logger.debug(f"⏱️ Обновлено время проверки для {source.source_global_id}")

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка обновления last_successful_post_id для {source.source_global_id}: {e}")
        raise


async def invalidate_source_cache_by_username(username: str) -> None:
    """
    Инвалидировать Redis-кеш для источника.

    Args:
        username: Username Telegram канала
    """
    try:
        await invalidate_source_cache(username)
        logger.debug(f"🗑️ Кеш для @{username} сброшен")
    except Exception as e:
        logger.error(f"❌ Ошибка сброса кеша для @{username}: {e}")

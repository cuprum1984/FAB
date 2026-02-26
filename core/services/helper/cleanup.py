"""
Ежедневная чистка устаревших записей в кеше.
Версия: 1.0 (14 февраля 2026)
"""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import CachedMedia, UserCachedMedia
from core.database import async_session

logger = logging.getLogger(__name__)


async def cleanup_expired_cache():
    """
    Удалить устаревшие записи из кеша.
    Запускать раз в день.
    """
    logger.info("🧹 Запуск ежедневной чистки кеша...")

    try:
        async with async_session() as session:
            # 1. Удаляем из общего кеша
            expired_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
            stmt = delete(CachedMedia).where(
                CachedMedia.last_used < expired_date
            )
            result = await session.execute(stmt)
            logger.info(f"🗑️ Удалено из общего кеша: {result.rowcount} записей")
            
            # 2. Удаляем из личного кеша
            stmt = delete(UserCachedMedia).where(
                UserCachedMedia.last_accessed < expired_date
            )
            result = await session.execute(stmt)
            logger.info(f"🗑️ Удалено из личного кеша: {result.rowcount} записей")
            
            await session.commit()
            
    except Exception as e:
        logger.error(f"❌ Ошибка при чистке кеша: {e}", exc_info=True)
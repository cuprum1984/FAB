# core/services/cleanup/media_cleanup.py
"""
Очистка кеша медиа:
- cleanup_expired_media: удаление устаревшего кеша (expires_at < now)
"""
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import CachedMedia
from .base import logger, console_print


async def cleanup_expired_media(session: AsyncSession):
    """
    Удалить устаревший кеш медиа.

    Условия:
    - expires_at < текущего времени
    """
    msg = "🔍 Проверка устаревшего кеша медиа..."
    logger.info(msg)
    console_print(msg)

    try:
        now = datetime.utcnow()

        # Очищаем основной кеш
        stmt_main = select(CachedMedia).where(CachedMedia.expires_at < now)
        result_main = await session.execute(stmt_main)
        expired_main = result_main.scalars().all()

        if expired_main:
            msg = f"📊 Найдено {len(expired_main)} устаревших записей в основном кеше:"
            logger.info(msg)
            console_print(msg)

            for media in expired_main[:5]:
                log_msg = f"   🗑️ {media.source_global_id}: пост {media.post_id}, истёк {media.expires_at}"
                logger.info(log_msg)
                console_print(log_msg)

            if len(expired_main) > 5:
                log_msg = f"      ... и ещё {len(expired_main) - 5} записей"
                logger.info(log_msg)
                console_print(log_msg)

            # Удаляем
            del_main = delete(CachedMedia).where(CachedMedia.expires_at < now)
            await session.execute(del_main)

        msg = f"✅ Очистка кеша: удалено {len(expired_main)} записей"
        logger.info(msg)
        console_print(msg)

    except Exception as e:
        error_msg = f"❌ Ошибка при очистке кеша медиа: {e}"
        logger.error(error_msg)
        console_print(error_msg)
        raise

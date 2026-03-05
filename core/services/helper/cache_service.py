"""
Сервис кеширования для бота-помощника.
Версия: 1.0 (14 февраля 2026)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import CachedMedia, UserCachedMedia

logger = logging.getLogger(__name__)


async def save_media_to_cache(
    session: AsyncSession,
    user_id: int,
    chat_id: int,
    message_id: int,
    media: Dict,
    caption: Optional[str] = None,
    post_url: Optional[str] = None
) -> None:
    """
    Сохранить медиа в общий кеш и личный кеш пользователя.
    """
    try:
        # 1. Сохраняем в общий кеш (если ещё нет)
        file_unique_id = media.get('file_unique_id')
        if file_unique_id:
            # Проверяем, есть ли уже в общем кеше
            stmt = select(CachedMedia).where(
                CachedMedia.file_unique_id == file_unique_id
            )
            result = await session.execute(stmt)
            cached = result.scalar_one_or_none()
            
            if not cached:
                # Создаём новую запись в общем кеше
                cached = CachedMedia(
                    source_global_id=None,  # неизвестно
                    post_id=None,
                    file_id=media['file_id'],
                    file_unique_id=file_unique_id,
                    file_type=media['type'],
                    file_size=media.get('file_size'),
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30),  # живёт месяц
                    last_used=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                session.add(cached)
                logger.debug(f"➕ Добавлено в общий кеш: {file_unique_id}")
            else:
                # Обновляем last_used
                cached.last_used = datetime.now(timezone.utc).replace(tzinfo=None)

        # 2. Сохраняем в личный кеш пользователя
        # Проверяем, не сохраняли ли уже это сообщение
        stmt = select(UserCachedMedia).where(
            and_(
                UserCachedMedia.user_id == user_id,
                UserCachedMedia.chat_id == chat_id,
                UserCachedMedia.message_id == message_id,
                UserCachedMedia.file_unique_id == file_unique_id
            )
        )
        result = await session.execute(stmt)
        user_cached = result.scalar_one_or_none()

        if not user_cached:
            # Создаём новую запись
            user_cached = UserCachedMedia(
                user_id=user_id,
                chat_id=chat_id,
                message_id=message_id,
                file_id=media['file_id'],
                file_unique_id=file_unique_id,
                file_type=media['type'],
                file_size=media.get('file_size'),
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30),
                last_accessed=datetime.now(timezone.utc).replace(tzinfo=None),
                caption=caption,
                post_url=post_url
            )
            session.add(user_cached)
            logger.debug(f"➕ Добавлено в личный кеш пользователя {user_id}: {file_unique_id}")
        else:
            # Обновляем last_accessed
            user_cached.last_accessed = datetime.now(timezone.utc).replace(tzinfo=None)
        
        await session.commit()
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка сохранения в кеш: {e}", exc_info=True)


async def get_user_cached_media(
    session: AsyncSession,
    user_id: int,
    limit: int = 10
) -> List[Dict]:
    """
    Получить последние сохранённые медиа пользователя.
    Для команды /saved (потом).
    """
    try:
        stmt = select(UserCachedMedia).where(
            UserCachedMedia.user_id == user_id
        ).order_by(
            UserCachedMedia.created_at.desc()
        ).limit(limit)
        
        result = await session.execute(stmt)
        media_list = result.scalars().all()
        
        return [
            {
                'message_id': m.message_id,
                'chat_id': m.chat_id,
                'file_id': m.file_id,
                'file_type': m.file_type,
                'caption': m.caption,
                'created_at': m.created_at,
                'post_url': m.post_url
            }
            for m in media_list
        ]
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения кеша пользователя {user_id}: {e}")
        return []
# core/services/destinations/subscriptions.py
"""
Функции для работы с подписками (SourceSubscription, UserChannelSubscription).
"""
import logging
from typing import List, Dict, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import (
    UserChannelSubscription,
    ContentSource,
    SourceSubscription,
    TelegramAccount
)

logger = logging.getLogger(__name__)


async def create_user_channel_subscription(
    session: AsyncSession,
    user_id: int,
    source_global_id: str,
    custom_title: Optional[str] = None,
    is_active: bool = True
) -> UserChannelSubscription:
    """
    Создать личную подписку пользователя на канал.

    Args:
        session: Сессия БД
        user_id: ID пользователя Telegram
        source_global_id: ID источника
        custom_title: Пользовательское название (опционально)
        is_active: Активна ли подписка

    Returns:
        UserChannelSubscription: Созданная подписка
    """
    try:
        # Проверяем, не существует ли уже подписка
        stmt = select(UserChannelSubscription).where(
            and_(
                UserChannelSubscription.user_id == user_id,
                UserChannelSubscription.source_global_id == source_global_id
            )
        )
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if subscription:
            # Обновляем существующую
            subscription.custom_title = custom_title or subscription.custom_title
            subscription.is_active = is_active
            await session.flush()
            return subscription

        # Создаём новую
        subscription = UserChannelSubscription(
            user_id=user_id,
            source_global_id=source_global_id,
            custom_title=custom_title,
            is_active=is_active
        )

        session.add(subscription)
        await session.flush()

        return subscription

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка создания подписки для пользователя {user_id}: {e}")
        raise


async def get_user_channel_subscriptions(
    user_id: int,
    session: AsyncSession,
    only_active: bool = True
) -> List[Dict]:
    """
    Получить все личные подписки пользователя на каналы.

    Args:
        user_id: ID пользователя
        session: Сессия БД
        only_active: Только активные подписки

    Returns:
        Список подписок с информацией о каналах
    """
    try:
        query = (
            select(UserChannelSubscription, ContentSource)
            .join(ContentSource, ContentSource.source_global_id == UserChannelSubscription.source_global_id)
            .where(UserChannelSubscription.user_id == user_id)
        )

        if only_active:
            query = query.where(UserChannelSubscription.is_active == True)

        query = query.order_by(UserChannelSubscription.created_at.desc())

        result = await session.execute(query)
        rows = result.all()

        return [
            {
                "subscription_id": row.UserChannelSubscription.id,
                "source_global_id": row.ContentSource.source_global_id,
                "telegram_username": row.ContentSource.telegram_username,
                "title": (row.ContentSource.channel_title or
                         (f"@{row.ContentSource.telegram_username}" if row.ContentSource.telegram_username
                          else row.ContentSource.youtube_username or "YouTube канал")),
                "custom_title": row.UserChannelSubscription.custom_title,
                "is_active": row.UserChannelSubscription.is_active,
                "created_at": row.UserChannelSubscription.created_at,
                "public_url": row.ContentSource.public_url,
                "parsing_url": row.ContentSource.parsing_url
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"❌ Ошибка получения подписок пользователя {user_id}: {e}")
        return []


async def update_user_channel_subscription(
    user_id: int,
    source_global_id: str,
    session: AsyncSession,
    is_active: Optional[bool] = None,
    custom_title: Optional[str] = None
) -> Optional[UserChannelSubscription]:
    """
    Обновить личную подписку пользователя на канал.
    """
    try:
        stmt = select(UserChannelSubscription).where(
            and_(
                UserChannelSubscription.user_id == user_id,
                UserChannelSubscription.source_global_id == source_global_id
            )
        )
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription:
            return None

        if is_active is not None:
            subscription.is_active = is_active

        if custom_title is not None:
            subscription.custom_title = custom_title

        await session.flush()
        await session.commit()

        return subscription

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка обновления подписки {user_id}:{source_global_id}: {e}")
        return None


async def get_source_subscription(
    chat_id: int,
    source_global_id: str,
    session: AsyncSession
) -> Optional[SourceSubscription]:
    """
    Получить подписку группы на источник.
    """
    try:
        stmt = select(SourceSubscription).where(
            and_(
                SourceSubscription.telegram_chat_id == chat_id,
                SourceSubscription.source_global_id == source_global_id
            )
        )

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"❌ Ошибка получения подписки {chat_id}:{source_global_id}: {e}")
        return None


async def create_source_subscription(
    chat_id: int,
    source_global_id: str,
    added_by_id: int,
    session: AsyncSession
) -> SourceSubscription:
    """
    Создать подписку группы на источник.
    """
    try:
        # Проверяем, существует ли источник
        source_stmt = select(ContentSource).where(ContentSource.source_global_id == source_global_id)
        source_result = await session.execute(source_stmt)
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Источник {source_global_id} не существует")

        # Создаём подписку
        subscription = SourceSubscription(
            telegram_chat_id=chat_id,
            source_global_id=source_global_id,
            added_by_telegram_account_id=added_by_id
        )

        session.add(subscription)
        await session.flush()

        return subscription

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка создания подписки {chat_id}:{source_global_id}: {e}")
        raise

# core/services/destinations/topics.py
"""
Функции для работы с темами (GroupTopic) — CRUD операции.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import GroupTopic
from .topic_utils import TopicUtils

logger = logging.getLogger(__name__)


async def create_or_update_topic(
    chat_id: int,
    thread_id: Optional[int],
    topic_name: str,
    created_by_id: int,
    session: AsyncSession
) -> GroupTopic:
    """
    Создать или обновить тему.
    """
    try:
        topic_identifier = TopicUtils.generate_topic_identifier(chat_id, thread_id)

        # Проверяем, существует ли уже такая тема
        stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
        result = await session.execute(stmt)
        topic = result.scalar_one_or_none()

        if topic:
            # Обновляем существующую тему
            topic.topic_name = topic_name
            topic.telegram_thread_id = thread_id
            topic.is_closed = False
        else:
            # Создаём новую тему
            topic = GroupTopic(
                topic_identifier=topic_identifier,
                telegram_chat_id=chat_id,
                telegram_thread_id=thread_id,
                topic_name=topic_name,
                is_closed=False,
                created_by_telegram_account_id=created_by_id
            )
            session.add(topic)

        await session.commit()
        return topic

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка создания/обновления темы {topic_identifier}: {e}")
        raise


async def get_topic_by_identifier(
    topic_identifier: str,
    session: AsyncSession
) -> Optional[GroupTopic]:
    """Получить тему по её идентификатору."""
    try:
        stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"❌ Ошибка получения темы {topic_identifier}: {e}")
        return None


async def get_topic_by_chat_and_thread(
    chat_id: int,
    thread_id: Optional[int],
    session: AsyncSession
) -> Optional[GroupTopic]:
    """Получить тему по chat_id и thread_id."""
    try:
        topic_identifier = TopicUtils.generate_topic_identifier(chat_id, thread_id)
        return await get_topic_by_identifier(topic_identifier, session)
    except Exception as e:
        logger.error(f"❌ Ошибка получения темы {chat_id}:{thread_id}: {e}")
        return None


async def close_topic(
    topic_identifier: str,
    session: AsyncSession
) -> bool:
    """Закрыть тему (пометить как is_closed = True)."""
    try:
        topic = await get_topic_by_identifier(topic_identifier, session)
        if not topic:
            return False

        topic.is_closed = True
        await session.commit()
        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка закрытия темы {topic_identifier}: {e}")
        return False


async def reopen_topic(
    topic_identifier: str,
    session: AsyncSession
) -> bool:
    """Открыть тему заново (пометить как is_closed = False)."""
    try:
        topic = await get_topic_by_identifier(topic_identifier, session)
        if not topic:
            return False

        topic.is_closed = False
        await session.commit()
        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка открытия темы {topic_identifier}: {e}")
        return False

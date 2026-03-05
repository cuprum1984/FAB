# core/services/destinations/assignments.py
"""
Функции для работы с назначениями (TopicSourceAssignment).
"""
import logging
from typing import List, Dict, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    TopicSourceAssignment,
    GroupTopic,
    SourceSubscription,
    ContentSource,
    ManagedGroup
)
from .topic_utils import TopicUtils
from .topics import get_topic_by_identifier

logger = logging.getLogger(__name__)


async def create_topic_assignment(
    topic_identifier: str,
    subscription_id: int,
    session: AsyncSession
) -> TopicSourceAssignment:
    """
    Создать назначение источника в тему.

    Args:
        topic_identifier: ID темы
        subscription_id: ID подписки группы на источник
        session: Сессия БД

    Returns:
        TopicSourceAssignment: Созданное назначение
    """
    try:
        # Проверяем, существует ли тема
        topic = await get_topic_by_identifier(topic_identifier, session)
        if not topic:
            raise ValueError(f"Тема {topic_identifier} не существует")

        # Проверяем, существует ли подписка
        sub_stmt = select(SourceSubscription).where(SourceSubscription.subscription_id == subscription_id)
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()

        if not subscription:
            raise ValueError(f"Подписка {subscription_id} не существует")

        # Проверяем, не существует ли уже такое назначение
        check_stmt = select(TopicSourceAssignment).where(
            and_(
                TopicSourceAssignment.topic_identifier == topic_identifier,
                TopicSourceAssignment.subscription_id == subscription_id
            )
        )
        check_result = await session.execute(check_stmt)
        existing = check_result.scalar_one_or_none()

        if existing:
            return existing

        # Создаём назначение
        assignment = TopicSourceAssignment(
            topic_identifier=topic_identifier,
            subscription_id=subscription_id
        )

        session.add(assignment)
        await session.flush()

        return assignment

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка создания назначения {topic_identifier}:{subscription_id}: {e}")
        raise


async def get_source_assignments_for_user(
    account_id: int,
    source_global_id: str,
    session: AsyncSession
) -> List[Dict]:
    """
    Получить все назначения источника для пользователя.
    """
    try:
        # Получаем группы пользователя
        from .access import get_user_groups
        groups = await get_user_groups(account_id, session)
        group_ids = [g["chat_id"] for g in groups]

        if not group_ids:
            return []

        # Получаем все назначения источника в группах пользователя
        query = (
            select(
                TopicSourceAssignment,
                GroupTopic,
                ManagedGroup
            )
            .join(
                GroupTopic,
                GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier
            )
            .join(
                ManagedGroup,
                ManagedGroup.telegram_chat_id == GroupTopic.telegram_chat_id
            )
            .join(
                SourceSubscription,
                SourceSubscription.subscription_id == TopicSourceAssignment.subscription_id
            )
            .where(
                and_(
                    SourceSubscription.source_global_id == source_global_id,
                    SourceSubscription.telegram_chat_id.in_(group_ids)
                )
            )
        )

        result = await session.execute(query)
        rows = result.all()

        assignments = []
        for row in rows:
            assignment, topic, group = row
            display_name = f"{group.telegram_chat_title or f'Группа {group.telegram_chat_id}'}"
            if topic.topic_name and topic.topic_name != "General":
                display_name += f" → {topic.topic_name}"

            assignments.append({
                "assignment_id": assignment.assignment_id,
                "topic_identifier": assignment.topic_identifier,
                "chat_id": group.telegram_chat_id,
                "thread_id": topic.telegram_thread_id,
                "topic_name": topic.topic_name,
                "group_title": group.telegram_chat_title,
                "display_name": display_name
            })

        return assignments

    except Exception as e:
        logger.error(f"❌ Ошибка получения назначений для пользователя {account_id}: {e}")
        return []


async def delete_source_assignment(
    assignment_id: int,
    account_id: int,
    session: AsyncSession
) -> bool:
    """
    Удалить назначение источника.

    Returns:
        True если удалено успешно, False если нет доступа или не найдено
    """
    try:
        # Получаем назначение
        stmt = select(TopicSourceAssignment).where(TopicSourceAssignment.assignment_id == assignment_id)
        result = await session.execute(stmt)
        assignment = result.scalar_one_or_none()

        if not assignment:
            return False

        # Проверяем доступ пользователя к теме
        from .access import check_destination_access
        has_access = await check_destination_access(account_id, assignment.topic_identifier, session)
        if not has_access:
            return False

        # Удаляем назначение
        await session.delete(assignment)
        await session.commit()

        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка удаления назначения {assignment_id}: {e}")
        return False


async def get_active_assignments_for_source(
    source_global_id: str,
    session: AsyncSession
) -> List[TopicSourceAssignment]:
    """
    Получить все активные назначения для источника.
    """
    try:
        stmt = (
            select(TopicSourceAssignment)
            .join(GroupTopic, GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier)
            .join(SourceSubscription, SourceSubscription.subscription_id == TopicSourceAssignment.subscription_id)
            .where(
                and_(
                    SourceSubscription.source_global_id == source_global_id,
                    GroupTopic.is_closed == False
                )
            )
        )

        result = await session.execute(stmt)
        return result.scalars().all()

    except Exception as e:
        logger.error(f"❌ Ошибка получения назначений для источника {source_global_id}: {e}")
        return []


async def get_subscribed_sources_for_destination(
    topic_identifier: str,
    session: AsyncSession
) -> List[Dict]:
    """
    Получить все источники, подписанные на конкретную тему.
    """
    try:
        query = (
            select(
                ContentSource,
                TopicSourceAssignment.subscription_id,
                TopicSourceAssignment.assignment_id
            )
            .join(
                SourceSubscription,
                SourceSubscription.subscription_id == TopicSourceAssignment.subscription_id
            )
            .join(
                ContentSource,
                ContentSource.source_global_id == SourceSubscription.source_global_id
            )
            .where(TopicSourceAssignment.topic_identifier == topic_identifier)
            .order_by(ContentSource.source_global_id)
        )

        result = await session.execute(query)
        rows = result.all()

        return [
            {
                "source_global_id": row.ContentSource.source_global_id,
                "source_type": row.ContentSource.source_type,
                "telegram_username": row.ContentSource.telegram_username,
                "name": (row.ContentSource.channel_title or
                        (f"@{row.ContentSource.telegram_username}" if row.ContentSource.telegram_username
                         else row.ContentSource.youtube_username or row.ContentSource.source_global_id)),
                "public_url": row.ContentSource.public_url,
                "parsing_url": row.ContentSource.parsing_url,
                "subscription_id": row.subscription_id,
                "assignment_id": row.assignment_id
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"❌ Ошибка получения источников для темы {topic_identifier}: {e}")
        return []

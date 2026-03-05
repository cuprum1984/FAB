# core/services/destinations/access.py
"""
Функции для проверки доступа и получения групп/destinations.
"""
import logging
from typing import List, Dict, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import ManagedGroup, GroupTopic
from .topic_utils import TopicUtils

logger = logging.getLogger(__name__)


async def get_user_groups(
    account_id: int,
    session: AsyncSession,
    only_active: bool = True,
    load_topics: bool = False,
    only_existing_topics: bool = True
) -> List[Dict]:
    """
    Возвращает список всех групп, где пользователь является создателем (creator_id)
    и где бот активен.

    Формат:
    [
        {
            "chat_id": -1001234567890,
            "chat_title": "Название группы",
            "display_name": "Название группы",
            "is_active": True/False,
            "topics": [список тем, если load_topics=True]
        },
        ...
    ]
    
    Args:
        only_existing_topics: Если True, фильтровать темы по is_exists_in_tg=True
    """
    try:
        # Получаем группы, где пользователь является создателем
        query = select(ManagedGroup).where(
            ManagedGroup.creator_id == account_id
        )

        # Фильтруем по активности бота в группе
        if only_active:
            query = query.where(ManagedGroup.is_bot_active_in_group == True)

        if load_topics:
            query = query.options(selectinload(ManagedGroup.topics))

        query = query.order_by(ManagedGroup.telegram_chat_title)

        result = await session.execute(query)
        groups = result.scalars().all()

        return [
            {
                "chat_id": group.telegram_chat_id,
                "chat_title": group.telegram_chat_title or f"Группа {group.telegram_chat_id}",
                "display_name": group.telegram_chat_title or f"Группа {group.telegram_chat_id}",
                "is_active": group.is_bot_active_in_group,
                "topics": [
                    {
                        "topic_identifier": topic.topic_identifier,
                        "topic_name": topic.topic_name,
                        "thread_id": topic.telegram_thread_id,
                        "is_closed": topic.is_closed
                    }
                    for topic in group.topics
                    if not only_existing_topics or topic.is_exists_in_tg
                ] if load_topics else []
            }
            for group in groups
        ]

    except Exception as e:
        logger.error(f"❌ Ошибка получения групп пользователя {account_id}: {e}")
        return []


async def get_user_destinations(
    account_id: int,
    session: AsyncSession,
    only_active: bool = True,
    include_general: bool = True,
    include_closed_topics: bool = False,
    only_existing_topics: bool = True
) -> List[Dict]:
    """
    Список всех групп и тем, куда пользователь может направлять посты.
    
    Args:
        only_existing_topics: Если True, фильтровать темы по is_exists_in_tg=True
    """
    try:
        destinations = []
        general_topics_added = set()

        # Получаем группы пользователя с темами
        groups = await get_user_groups(
            account_id, session, only_active, load_topics=True,
            only_existing_topics=only_existing_topics
        )

        for group in groups:
            chat_id = group["chat_id"]
            chat_title = group["chat_title"]
            has_general_topic = False

            # Добавляем темы из группы
            for topic_info in group["topics"]:
                if topic_info["is_closed"] and not include_closed_topics:
                    continue

                # Проверяем, не является ли тема General
                is_general = (
                    topic_info["topic_name"] == "General" or
                    topic_info["thread_id"] is None or
                    TopicUtils.is_general_topic(topic_info["topic_identifier"])
                )

                if is_general:
                    has_general_topic = True
                    general_topics_added.add(chat_id)

                display_name = f"{chat_title}"
                if topic_info["topic_name"] and not is_general:
                    display_name += f" → {topic_info['topic_name']}"
                elif is_general:
                    display_name += f" → General"

                destinations.append({
                    "chat_id": chat_id,
                    "thread_id": topic_info["thread_id"],
                    "chat_title": chat_title,
                    "thread_name": topic_info["topic_name"] or "Без названия",
                    "display_name": display_name,
                    "topic_identifier": topic_info["topic_identifier"],
                    "is_topic_active": not topic_info["is_closed"],
                    "is_closed": topic_info["is_closed"],
                    "is_general": is_general
                })

            # Добавляем General тему если требуется И если её ещё нет
            if include_general and not has_general_topic and chat_id not in general_topics_added:
                general_identifier = TopicUtils.generate_topic_identifier(chat_id, None)

                destinations.append({
                    "chat_id": chat_id,
                    "thread_id": None,
                    "chat_title": chat_title,
                    "thread_name": "General",
                    "display_name": f"{chat_title} → General",
                    "topic_identifier": general_identifier,
                    "is_topic_active": True,
                    "is_closed": False,
                    "is_general": True
                })
                general_topics_added.add(chat_id)

        # Сортируем
        destinations.sort(key=lambda x: (
            1 if x.get("is_general", False) else 0,
            x["chat_title"] or "",
            x["thread_name"] or ""
        ))

        # Удаляем дубликаты
        unique_destinations = []
        seen_identifiers = set()

        for dest in destinations:
            if dest["topic_identifier"] not in seen_identifiers:
                seen_identifiers.add(dest["topic_identifier"])
                unique_destinations.append(dest)

        return unique_destinations

    except Exception as e:
        logger.error(f"❌ Ошибка получения destinations для пользователя {account_id}: {e}")
        return []


async def get_group_destinations(
    chat_id: int,
    session: AsyncSession,
    include_general: bool = True,
    include_closed_topics: bool = False
) -> List[Dict]:
    """
    Получить все темы в конкретной группе.
    """
    try:
        # Получаем информацию о группе с темами
        query = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
        query = query.options(selectinload(ManagedGroup.topics))

        result = await session.execute(query)
        group = result.scalar_one_or_none()

        if not group or not group.is_bot_active_in_group:
            return []

        destinations = []
        chat_title = group.telegram_chat_title or f"Группа {chat_id}"

        # Обрабатываем темы группы
        for topic in group.topics:
            if topic.is_closed and not include_closed_topics:
                continue

            display_name = chat_title
            if topic.topic_name and topic.topic_name != "General":
                display_name += f" → {topic.topic_name}"

            destinations.append({
                "chat_id": chat_id,
                "thread_id": topic.telegram_thread_id,
                "chat_title": chat_title,
                "thread_name": topic.topic_name or "Без названия",
                "display_name": display_name,
                "topic_identifier": topic.topic_identifier,
                "is_topic_active": not topic.is_closed,
                "is_closed": topic.is_closed,
                "is_general": topic.telegram_thread_id is None
            })

        # Добавляем General если требуется
        if include_general:
            general_identifier = TopicUtils.generate_topic_identifier(chat_id, None)

            destinations.append({
                "chat_id": chat_id,
                "thread_id": None,
                "chat_title": chat_title,
                "thread_name": "General",
                "display_name": f"{chat_title} → General",
                "topic_identifier": general_identifier,
                "is_topic_active": True,
                "is_closed": False,
                "is_general": True
            })

        # Сортируем: сначала активные темы, потом General
        destinations.sort(key=lambda x: (
            0 if x.get("is_general", False) else 1,
            not x.get("is_topic_active", False),
            x["thread_name"] or ""
        ))

        return destinations

    except Exception as e:
        logger.error(f"❌ Ошибка получения destinations для группы {chat_id}: {e}")
        return []


async def check_destination_access(
    account_id: int,
    topic_identifier: str,
    session: AsyncSession
) -> bool:
    """
    Проверить, имеет ли пользователь доступ к указанной теме/группе.
    """
    try:
        chat_id, _ = TopicUtils.parse_topic_identifier(topic_identifier)
    except ValueError:
        return False

    try:
        # Проверяем, является ли пользователь создателем группы
        stmt = select(ManagedGroup).where(
            and_(
                ManagedGroup.telegram_chat_id == chat_id,
                ManagedGroup.creator_id == account_id
            )
        )

        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        return group is not None

    except Exception as e:
        logger.error(f"❌ Ошибка проверки доступа {account_id}:{topic_identifier}: {e}")
        return False


async def get_destination_by_display_name(
    account_id: int,
    display_name: str,
    session: AsyncSession
) -> Optional[Dict]:
    """
    Найти destination по display_name (учитывая эмодзи).
    """
    try:
        destinations = await get_user_destinations(account_id, session)

        for dest in destinations:
            # Сравниваем как есть
            if dest["display_name"] == display_name:
                return dest

            # Сравниваем без эмодзи
            clean_display = dest["display_name"]
            emoji_prefixes = ["💬 ", "🗨️ ", "👥 ", "📰 ", "🎯 ", "🔗 "]

            for prefix in emoji_prefixes:
                if clean_display.startswith(prefix):
                    clean_display = clean_display[len(prefix):]
                    break

            if clean_display == display_name:
                return dest

        return None

    except Exception as e:
        logger.error(f"❌ Ошибка поиска destination по имени {display_name}: {e}")
        return None


async def get_user_topics_for_verification(
    account_id: int,
    session: AsyncSession
) -> List[GroupTopic]:
    """
    Получить ВСЕ темы пользователя для проверки.
    
    Включает темы, которые уже помечены как удалённые (is_exists_in_tg=False),
    чтобы можно было проверить их повторно.
    
    Args:
        account_id: ID пользователя (creator_id)
        session: Сессия БД
    
    Returns:
        Список всех тем пользователя
    """
    # Получаем все группы пользователя
    groups_stmt = select(ManagedGroup.telegram_chat_id).where(
        ManagedGroup.creator_id == account_id
    )
    groups_result = await session.execute(groups_stmt)
    group_chat_ids = [row[0] for row in groups_result.all()]
    
    if not group_chat_ids:
        return []
    
    # Получаем все темы этих групп
    topics_stmt = select(GroupTopic).where(
        GroupTopic.telegram_chat_id.in_(group_chat_ids)
    )
    topics_result = await session.execute(topics_stmt)
    
    return list(topics_result.scalars().all())

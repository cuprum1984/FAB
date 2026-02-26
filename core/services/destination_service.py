# core/services/destination_service.py
"""
Сервис для работы с группами, темами, подписками и назначениями источников.
Версия: 3.4 (22 февраля 2026)
Изменения:
- Удалены все упоминания GroupMembership
- Функция get_user_groups теперь использует creator_id вместо GroupMembership
- Исправлены все импорты
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import (
    ManagedGroup,      # ✅ GroupMembership удалён
    GroupTopic,
    SourceSubscription,
    TopicSourceAssignment,
    ContentSource,
    UserChannelSubscription,
    TelegramAccount
)
from core.redis_client import get_cached_last_post, set_cached_last_post, invalidate_source_cache


# Настройка логгера
logger = logging.getLogger(__name__)


class TopicUtils:
    """Утилиты для работы с идентификаторами тем"""
    
    @staticmethod
    def generate_topic_identifier(chat_id: int, thread_id: Optional[int] = None) -> str:
        """
        Генерирует идентификатор темы.
        
        Args:
            chat_id: ID чата/группы
            thread_id: ID темы (thread) или None для General
            
        Returns:
            topic_identifier в формате "chat_id:thread_id" или "chat_id:0" для General
        """
        if thread_id is None or thread_id == 0:
            return f"{chat_id}:0"
        return f"{chat_id}:{thread_id}"
    
    @staticmethod
    def parse_topic_identifier(topic_identifier: str) -> Tuple[int, Optional[int]]:
        """
        Парсит topic_identifier, извлекая chat_id и thread_id.
        
        Args:
            topic_identifier: строка в формате "chat_id:thread_id"
            
        Returns:
            tuple(chat_id, thread_id) где thread_id может быть None
            
        Raises:
            ValueError: если формат неверный
        """
        if ":" not in topic_identifier:
            raise ValueError(f"Invalid topic_identifier format: {topic_identifier}")
        
        parts = topic_identifier.split(":", 1)
        try:
            chat_id = int(parts[0])
            thread_id_str = parts[1]
            
            if thread_id_str == "0":
                thread_id = None
            else:
                thread_id = int(thread_id_str)
                
            return chat_id, thread_id
        except (ValueError, IndexError) as e:
            raise ValueError(f"Cannot parse topic_identifier: {topic_identifier}") from e
    
    @staticmethod
    def is_general_topic(topic_identifier: str) -> bool:
        """Проверяет, является ли тема General (без thread_id)."""
        try:
            _, thread_id = TopicUtils.parse_topic_identifier(topic_identifier)
            return thread_id is None or thread_id == 0
        except ValueError:
            return False


async def get_or_create_content_source(
    session: AsyncSession,
    source_global_id: str,
    source_type: str,
    telegram_username: Optional[str] = None,
    channel_title: Optional[str] = None,  # ✅ НОВЫЙ ПАРАМЕТР
    feed_url: Optional[str] = None,
    youtube_username: Optional[str] = None
) -> Tuple[ContentSource, bool]:
    
    try:
        stmt = select(ContentSource).where(ContentSource.source_global_id == source_global_id)
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()
        
        if source:
            # Обновляем информацию
            if telegram_username and not source.telegram_username:
                source.telegram_username = telegram_username
            if channel_title and not source.channel_title:  # ✅ СОХРАНЯЕМ
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
            channel_title=channel_title,  # ✅ СОХРАНЯЕМ
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


async def get_user_groups(
    account_id: int,
    session: AsyncSession,
    only_active: bool = True,
    load_topics: bool = False
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
    
    🔥 ИСПРАВЛЕНО: вместо GroupMembership используем creator_id
    """
    try:
        # Получаем группы, где пользователь является создателем
        query = select(ManagedGroup).where(
            ManagedGroup.creator_id == account_id
        )
        
        # ✅ ВАЖНО: Фильтруем по активности бота в группе
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
    include_closed_topics: bool = False
) -> List[Dict]:
    """
    Список всех групп и тем, куда пользователь может направлять посты.
    
    🔥 ИСПРАВЛЕНО: используем обновлённую get_user_groups
    """
    try:
        destinations = []
        general_topics_added = set()
        
        # Получаем группы пользователя с темами
        groups = await get_user_groups(account_id, session, only_active, load_topics=True)
        
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
            1 if x.get("is_general", False) else 0,  # General в конце
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
                # 🔥 ИСПРАВЛЕНО: используем channel_title если есть
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


async def check_destination_access(
    account_id: int,
    topic_identifier: str,
    session: AsyncSession
) -> bool:
    """
    Проверить, имеет ли пользователь доступ к указанной теме/группе.
    
    🔥 ИСПРАВЛЕНО: теперь проверяем через creator_id
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


async def get_source_assignments_for_user(
    account_id: int,
    source_global_id: str,
    session: AsyncSession
) -> List[Dict]:
    """
    Получить все назначения источника для пользователя.
    
    🔥 ИСПРАВЛЕНО: используем обновлённую логику с creator_id
    """
    try:
        # Получаем группы пользователя
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


async def get_destination_by_display_name(
    account_id: int,
    display_name: str,
    session: AsyncSession
) -> Optional[Dict]:
    """
    Найти destination по display_name (учитывая эмодзи).
    
    Args:
        account_id: ID пользователя
        display_name: Искомое название (с эмодзи или без)
        session: Сессия БД
        
    Returns:
        Словарь с информацией о destination или None
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
                # 🔥 ИСПРАВЛЕНО: используем channel_title если есть
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
        return source.last_successful_post_id  # Fallback на БД


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
        
    ✅ ПОЛНОСТЬЮ ИСПРАВЛЕНО: try/except, rollback(), защита от меньших ID
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
        await session.rollback()  # ✅ КРИТИЧЕСКИ ВАЖНО!
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
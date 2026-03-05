# core/services/cleanup/topic_cleanup.py
"""
Очистка тем:
- cleanup_orphan_topics: удаление тем с is_exists_in_tg=False
- cleanup_old_topics: удаление тем без активности >90 дней
"""
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import GroupTopic, TopicSourceAssignment
from .base import logger, console_print


async def cleanup_orphan_topics(session: AsyncSession):
    """
    Удалить темы, помеченные как несуществующие в Telegram (is_exists_in_tg=False).

    ⚠️ ВАЖНО: Назначения (TopicSourceAssignment) не проверяются — они будут
    удалены автоматически через CASCADE при удалении темы.
    
    Если тема удалена в Telegram (is_exists_in_tg=False), она бесполезна —
    назначения на неё не могут работать, thread_id уже не существует.
    """
    msg = "🔍 Проверка удалённых тем..."
    logger.info(msg)
    console_print(msg)

    try:
        # Находим темы с is_exists_in_tg=False (без ограничения по дате создания)
        stmt = select(GroupTopic).where(
            GroupTopic.is_exists_in_tg == False
        )
        result = await session.execute(stmt)
        dead_topics = result.scalars().all()

        if not dead_topics:
            msg = "✅ Нет удалённых тем для очистки"
            logger.info(msg)
            console_print(msg)
            return

        msg = f"📊 Найдено {len(dead_topics)} удалённых тем для очистки:"
        logger.info(msg)
        console_print(msg)

        # Удаляем все найденные темы (CASCADE удалит TopicSourceAssignment)
        total_assignments_deleted = 0
        for topic in dead_topics:
            # Подсчитываем назначения перед удалением
            assign_stmt = select(TopicSourceAssignment).where(
                TopicSourceAssignment.topic_identifier == topic.topic_identifier
            )
            assign_result = await session.execute(assign_stmt)
            assignments = assign_result.scalars().all()
            assignments_count = len(assignments)
            total_assignments_deleted += assignments_count

            log_msg = f"   🗑️ Удаляется тема:"
            logger.info(log_msg)
            console_print(log_msg)

            logger.info(f"      • ID: {topic.topic_identifier}")
            logger.info(f"      • Название: {topic.topic_name}")
            logger.info(f"      • Группа: {topic.telegram_chat_id}")
            logger.info(f"      • Создана: {topic.created_timestamp}")
            logger.info(f"      • Помечена как удалённая: {topic.is_exists_in_tg}")
            logger.info(f"      • Назначений удалено: {assignments_count}")
            console_print(f"      • Назначений удалено: {assignments_count}")

            await session.delete(topic)

        msg = f"✅ Очистка тем завершена: удалено {len(dead_topics)} тем, {total_assignments_deleted} назначений"
        logger.info(msg)
        console_print(msg)

    except Exception as e:
        error_msg = f"❌ Ошибка при очистке тем: {e}"
        logger.error(error_msg)
        console_print(error_msg)
        raise


async def cleanup_old_topics(session: AsyncSession):
    """
    Удалить темы, которые не посещались админом через /plus >90 дней.

    Условия:
    - last_seen_at IS NOT NULL
    - last_seen_at < 90 дней назад
    - нет активных подписок на эту тему

    ⚠️ ВАЖНО: Не удаляем General темы и темы с last_seen_at = NULL
    """
    msg = "🔍 Проверка старых тем (нет активности /plus >90 дней)..."
    logger.info(msg)
    console_print(msg)

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=0)

        # Находим старые темы
        stmt = select(GroupTopic).where(
            and_(
                GroupTopic.last_seen_at != None,
                GroupTopic.last_seen_at < cutoff_date,
                GroupTopic.topic_name != "General"
            )
        )
        result = await session.execute(stmt)
        old_topics = result.scalars().all()

        if not old_topics:
            msg = "✅ Нет старых тем для удаления"
            logger.info(msg)
            console_print(msg)
            return

        msg = f"📊 Найдено {len(old_topics)} старых тем:"
        logger.info(msg)
        console_print(msg)

        # Проверяем, используются ли темы в назначениях
        topics_to_delete = []
        for topic in old_topics:
            assign_stmt = select(TopicSourceAssignment).where(
                TopicSourceAssignment.topic_identifier == topic.topic_identifier
            )
            assign_result = await session.execute(assign_stmt)
            assignments = assign_result.scalars().all()

            if not assignments:
                topics_to_delete.append(topic)
            else:
                logger.info(f"   ℹ️ Тема {topic.topic_name} имеет активные подписки, пропускается")

        if not topics_to_delete:
            msg = "✅ Нет неиспользуемых старых тем"
            logger.info(msg)
            console_print(msg)
            return

        msg = f"📊 Найдено {len(topics_to_delete)} старых тем для очистки:"
        logger.info(msg)
        console_print(msg)

        # Удаляем темы
        for topic in topics_to_delete:
            log_msg = f"   🗑️ Удаляется старая тема:"
            logger.info(log_msg)
            console_print(log_msg)

            logger.info(f"      • ID: {topic.topic_identifier}")
            logger.info(f"      • Название: {topic.topic_name}")
            logger.info(f"      • Группа: {topic.telegram_chat_id}")
            logger.info(f"      • Последнее посещение: {topic.last_seen_at}")
            logger.info(f"      • Создана: {topic.created_timestamp}")

            await session.delete(topic)

        msg = f"✅ Очистка старых тем завершена: удалено {len(topics_to_delete)}"
        logger.info(msg)
        console_print(msg)

    except Exception as e:
        error_msg = f"❌ Ошибка при очистке старых тем: {e}"
        logger.error(error_msg)
        console_print(error_msg)
        raise

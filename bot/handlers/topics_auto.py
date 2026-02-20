# bot/handlers/topics_auto.py
"""
Автоматическое отслеживание тем через служебные сообщения Bot API.
Версия: 1.1 (17 февраля 2026)
Исправлено: правильные названия полей для aiogram 3.x
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.services.destination_service import create_or_update_topic
from core.models import GroupTopic
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router(name="topics_auto")


@router.message(F.forum_topic_created)
async def on_topic_created(message: Message, session: AsyncSession):
    """
    Автоматическое сохранение новой темы при её создании.
    В aiogram 3.x название темы лежит в message.forum_topic_created.name
    """
    if not message.forum_topic_created:
        return
    
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    topic_name = message.forum_topic_created.name  # ✅ Правильно!
    user_id = message.from_user.id
    
    logger.info(f"📌 Создана новая тема: '{topic_name}' (ID: {thread_id}) в чате {chat_id}")
    
    try:
        topic_identifier = f"{chat_id}:{thread_id}"
        stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"ℹ️ Тема '{topic_name}' уже существует в БД, обновляю название")
            existing.topic_name = topic_name
            await session.commit()
        else:
            await create_or_update_topic(
                chat_id=chat_id,
                thread_id=thread_id,
                topic_name=topic_name,
                created_by_id=user_id,
                session=session
            )
            logger.info(f"✅ Тема '{topic_name}' автоматически сохранена в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении темы: {e}", exc_info=True)
        await session.rollback()


@router.message(F.forum_topic_edited)
async def on_topic_edited(message: Message, session: AsyncSession):
    """
    Автоматическое обновление названия темы при переименовании.
    В aiogram 3.x новое название лежит в message.forum_topic_edited.name
    """
    if not message.forum_topic_edited:
        return
    
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    new_name = message.forum_topic_edited.name  # ✅ Правильно!
    
    logger.info(f"🔄 Тема переименована: '{new_name}' (ID: {thread_id})")
    
    try:
        topic_identifier = f"{chat_id}:{thread_id}"
        stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
        result = await session.execute(stmt)
        topic = result.scalar_one_or_none()
        
        if topic:
            old_name = topic.topic_name
            topic.topic_name = new_name
            await session.commit()
            logger.info(f"✅ Название темы обновлено: '{old_name}' → '{new_name}'")
        else:
            await create_or_update_topic(
                chat_id=chat_id,
                thread_id=thread_id,
                topic_name=new_name,
                created_by_id=message.from_user.id,
                session=session
            )
            logger.info(f"✅ Новая тема '{new_name}' создана (была переименована до регистрации)")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении темы: {e}", exc_info=True)
        await session.rollback()


@router.message(F.forum_topic_closed)
async def on_topic_closed(message: Message, session: AsyncSession):
    """
    Отслеживание закрытия темы (опционально).
    """
    if not message.forum_topic_closed:
        return
    
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    
    logger.info(f"🔒 Тема закрыта (ID: {thread_id})")
    # Здесь можно добавить логику для закрытых тем
# bot/handlers/topics_auto.py
"""
Автоматическое отслеживание тем через служебные сообщения Bot API.
Версия: 1.3 (23 февраля 2026)
Исправлено:
- Удалено автосохранение новых тем при создании (теперь только через /plus)
- Оставлено только отслеживание переименований/закрытий для УЖЕ зарегистрированных тем
- Защита от None в названии темы
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


# ⚠️ АВТОСОХРАНЕНИЕ ТЕМ ПРИ СОЗДАНИИ ОТКЛЮЧЕНО!
# Темы теперь регистрируются ТОЛЬКО через команду /plus
# Это позволяет админу контролировать, в каких темах будет работать бот


@router.message(F.forum_topic_edited)
async def on_topic_edited(message: Message, session: AsyncSession):
    """
    Автоматическое обновление названия темы при переименовании.
    Работает ТОЛЬКО для уже зарегистрированных тем (через /plus).
    """
    if not message.forum_topic_edited:
        return

    chat_id = message.chat.id
    thread_id = message.message_thread_id
    new_name = message.forum_topic_edited.name

    # 🔥 КРИТИЧЕСКИ ВАЖНО: проверяем, что new_name не None
    if new_name is None:
        logger.warning(f"⚠️ Получено None вместо нового названия темы для ID {thread_id}, пропускаю обновление")
        return

    logger.info(f"🔄 Тема переименована: '{new_name}' (ID: {thread_id})")

    try:
        topic_identifier = f"{chat_id}:{thread_id}"
        stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
        result = await session.execute(stmt)
        topic = result.scalar_one_or_none()

        if topic:
            # ✅ Обновляем ТОЛЬКО если тема уже зарегистрирована
            old_name = topic.topic_name
            topic.topic_name = new_name
            topic.is_exists_in_tg = True
            await session.commit()
            logger.info(f"✅ Название темы обновлено: '{old_name}' → '{new_name}'")
        else:
            # 🔥 ТЕПЕРЬ НЕ СОЗДАЁМ тему автоматически
            logger.info(f"ℹ️ Тема '{new_name}' (ID: {thread_id}) не зарегистрирована в БД (нет /plus), пропускаю")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении темы: {e}", exc_info=True)
        await session.rollback()


@router.message(F.forum_topic_closed)
async def on_topic_closed(message: Message, session: AsyncSession):
    """
    Отслеживание закрытия темы.
    Работает ТОЛЬКО для уже зарегистрированных тем (через /plus).
    """
    if not message.forum_topic_closed:
        return

    chat_id = message.chat.id
    thread_id = message.message_thread_id

    logger.info(f"🔒 Тема закрыта (ID: {thread_id})")

    try:
        topic_identifier = f"{chat_id}:{thread_id}"
        stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
        result = await session.execute(stmt)
        topic = result.scalar_one_or_none()

        if topic:
            # ✅ Обновляем ТОЛЬКО если тема уже зарегистрирована
            topic.is_closed = True
            await session.commit()
            logger.info(f"✅ Тема '{topic.topic_name}' помечена как закрытая")
        else:
            logger.debug(f"ℹ️ Тема (ID: {thread_id}) не зарегистрирована в БД, пропускаю закрытие")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии темы: {e}", exc_info=True)
        await session.rollback()


@router.message(F.forum_topic_reopened)
async def on_topic_reopened(message: Message, session: AsyncSession):
    """
    Отслеживание открытия темы.
    Работает ТОЛЬКО для уже зарегистрированных тем (через /plus).
    """
    if not message.forum_topic_reopened:
        return

    chat_id = message.chat.id
    thread_id = message.message_thread_id

    logger.info(f"🔓 Тема открыта заново (ID: {thread_id})")

    try:
        topic_identifier = f"{chat_id}:{thread_id}"
        stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
        result = await session.execute(stmt)
        topic = result.scalar_one_or_none()

        if topic:
            # ✅ Обновляем ТОЛЬКО если тема уже зарегистрирована
            topic.is_closed = False
            await session.commit()
            logger.info(f"✅ Тема '{topic.topic_name}' помечена как открытая")
        else:
            logger.debug(f"ℹ️ Тема (ID: {thread_id}) не зарегистрирована в БД, пропускаю открытие")
    except Exception as e:
        logger.error(f"❌ Ошибка при открытии темы: {e}", exc_info=True)
        await session.rollback()
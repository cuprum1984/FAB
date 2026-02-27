# core/utils/topic_checker.py
"""
Утилиты для проверки существования тем в Telegram.

Проверка происходит путём отправки тестового сообщения (точки) в тему
и его немедленного удаления. Если тема удалена в Telegram - получаем ошибку.
"""
import logging
from typing import List, Tuple, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import GroupTopic
from core.services.destinations.access import get_user_topics_for_verification

logger = logging.getLogger(__name__)


async def check_topic_live(
    bot: Bot,
    chat_id: int,
    thread_id: Optional[int]
) -> bool:
    """
    Проверить, можно ли писать в тему.
    
    Отправляет тестовое сообщение (точку) и сразу удаляет его.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID группы
        thread_id: ID темы (None для General)
    
    Returns:
        True если тема жива, False если удалена
    """
    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=".",
            disable_notification=True
        )
        await bot.delete_message(
            chat_id=chat_id,
            message_id=msg.message_id
        )
        return True
        
    except TelegramBadRequest as e:
        error = str(e).lower()
        # Тема удалена в Telegram
        if "message thread not found" in error:
            logger.info(f"🗑️ Тема {chat_id}:{thread_id} удалена в Telegram")
            return False
        # Другие ошибки (нет прав, бан и т.д.) — считаем тему живой
        logger.debug(f"⚠️ Тема {chat_id}:{thread_id} вернула ошибку, но считаем живой: {e}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при проверке темы {chat_id}:{thread_id}: {e}")
        # При неизвестной ошибке считаем тему живой (чтобы не удалять ложно)
        return True


async def verify_user_topics(
    user_id: int,
    bot: Bot,
    session: AsyncSession
) -> Tuple[List[GroupTopic], List[GroupTopic], int]:
    """
    Проверить все темы пользователя в Telegram.
    
    Args:
        user_id: ID пользователя
        bot: Экземпляр бота
        session: Сессия БД
    
    Returns:
        Кортеж из:
        - список живых тем (GroupTopic)
        - список удалённых тем (GroupTopic)
        - общее количество проверенных тем
    """
    # Получаем все темы пользователя из БД
    topics = await get_user_topics_for_verification(user_id, session)
    
    if not topics:
        logger.debug(f"📭 У пользователя {user_id} нет тем для проверки")
        return [], [], 0
    
    logger.info(f"🔍 Проверка {len(topics)} тем пользователя {user_id}")
    
    # Параллельная проверка всех тем через asyncio.gather()
    from asyncio import gather
    
    tasks = []
    for topic in topics:
        tasks.append(
            check_topic_live(bot, topic.telegram_chat_id, topic.telegram_thread_id)
        )
    
    results = await gather(*tasks, return_exceptions=True)
    
    # Сортируем на живые и удалённые
    alive_topics = []
    deleted_topics = []
    
    for i, result in enumerate(results):
        topic = topics[i]
        
        # Любая ошибка или False — считаем удалённой
        if isinstance(result, bool) and result:
            alive_topics.append(topic)
        else:
            deleted_topics.append(topic)
            topic.is_exists_in_tg = False
            logger.info(f"🗑️ Тема {topic.topic_name} ({topic.topic_identifier}) помечена как удалённая")
    
    # Сохраняем изменения в БД одной транзакцией
    if deleted_topics:
        await session.commit()
        logger.info(f"✅ Обновлено {len(deleted_topics)} удалённых тем в БД")

    return alive_topics, deleted_topics, len(topics)

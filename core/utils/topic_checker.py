# core/utils/topic_checker.py
"""
Утилиты для проверки существования тем в Telegram.

Проверка происходит путём отправки дружелюбного сообщения "🤗 Проверка...",
ожидания 4 секунды и удаления сообщения.

Проверка выполняется асинхронно — бот не ждёт удаления сообщений.
"""
import asyncio
import logging
from typing import List, Tuple, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import update, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import GroupTopic, ManagedGroup
from core.services.destinations.access import get_user_topics_for_verification

logger = logging.getLogger(__name__)

# Настройки проверки
CHECK_DELAY_SECONDS = 4  # Задержка перед удалением


async def check_topic_live(
    bot: Bot,
    chat_id: int,
    thread_id: Optional[int],
    session: Optional[AsyncSession] = None,
    check_text: str = "🤗 Проверка..."
) -> bool:
    """
    Проверить, можно ли писать в тему.

    Отправляет дружелюбное сообщение, ждёт 4 секунды, удаляет.
    НЕ БЛОКИРУЕТ основной процесс — удаление происходит в фоне.

    Args:
        bot: Экземпляр бота
        chat_id: ID группы
        thread_id: ID темы (None для General)
        session: Сессия БД (для обновления флага активности группы)
        check_text: Текст сообщения проверки (из локализации)

    Returns:
        True если тема жива, False если удалена
    """
    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=check_text,
            disable_notification=True
        )

        # Создаём задачу на удаление через 4 секунды (в фоне)
        asyncio.create_task(delete_check_message(bot, chat_id, msg.message_id))

        return True

    except TelegramBadRequest as e:
        error = str(e).lower()
        # Тема удалена в Telegram
        if "message thread not found" in error:
            logger.info(f"🗑️ Тема {chat_id}:{thread_id} удалена в Telegram")
            return False
        # Бот удалён из группы — обновляем флаг в БД
        if ("bot was kicked" in error or
            "bot was kicked from" in error or
            "forbidden" in error):
            if session:
                await session.execute(
                    update(ManagedGroup)
                    .where(ManagedGroup.telegram_chat_id == chat_id)
                    .values(is_bot_active_in_group=False, last_seen_at=func.now())
                )
                await session.commit()
                logger.info(f"🚫 Группа {chat_id} помечена неактивной: {e}")
            return False
        # Другие ошибки (нет прав, бан и т.д.) — считаем тему живой
        logger.debug(f"⚠️ Тема {chat_id}:{thread_id} вернула ошибку, но считаем живой: {e}")
        return True

    except TelegramForbiddenError as e:
        # Бот удалён из группы (TelegramForbiddenError)
        logger.info(f"🚫 Группа {chat_id} помечена неактивной: {e}")
        if session:
            await session.execute(
                update(ManagedGroup)
                .where(ManagedGroup.telegram_chat_id == chat_id)
                .values(is_bot_active_in_group=False, last_seen_at=func.now())
            )
            await session.commit()
        return False

    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при проверке темы {chat_id}:{thread_id}: {e}")
        # При неизвестной ошибке считаем тему живой (чтобы не удалять ложно)
        return True


async def delete_check_message(
    bot: Bot,
    chat_id: int,
    message_id: int
):
    """
    Удалить сообщение проверки через 4 секунды.
    Запускается как фоновая задача.
    """
    try:
        await asyncio.sleep(CHECK_DELAY_SECONDS)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug(f"🗑️ Сообщение проверки {message_id} в {chat_id} удалено")
    except Exception as e:
        logger.debug(f"⚠️ Не удалось удалить сообщение проверки {message_id}: {e}")


async def verify_user_topics(
    user_id: int,
    bot: Bot,
    session: AsyncSession,
    check_text: str = "🤗 Проверка..."
) -> Tuple[List[GroupTopic], List[GroupTopic], int]:
    """
    Проверить все темы пользователя в Telegram.

    Проверка выполняется асинхронно — бот не ждёт удаления сообщений.
    Темы из неактивных групп (is_bot_active_in_group=False) пропускаются.

    Args:
        user_id: ID пользователя
        bot: Экземпляр бота
        session: Сессия БД
        check_text: Текст сообщения проверки (из локализации)

    Returns:
        Кортеж из:
        - список живых тем (GroupTopic)
        - список удалённых тем (GroupTopic)
        - общее количество проверенных тем
    """
    from sqlalchemy import select
    from asyncio import gather

    # Получаем все темы пользователя с JOIN к ManagedGroup и фильтром по активности
    query = (
        select(GroupTopic)
        .join(ManagedGroup, GroupTopic.telegram_chat_id == ManagedGroup.telegram_chat_id)
        .where(
            ManagedGroup.creator_id == user_id,
            ManagedGroup.is_bot_active_in_group == True
        )
    )
    result = await session.execute(query)
    topics = list(result.scalars().all())

    if not topics:
        logger.debug(f"📭 У пользователя {user_id} нет тем для проверки")
        return [], [], 0

    logger.info(f"🔍 Проверка {len(topics)} тем пользователя {user_id}")

    # Параллельная проверка всех тем через asyncio.gather()
    tasks = []
    for topic in topics:
        tasks.append(
            check_topic_live(bot, topic.telegram_chat_id, topic.telegram_thread_id, session, check_text)
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

    logger.info(
        f"📊 Проверено {len(topics)} тем: "
        f"{len(alive_topics)} живых, "
        f"{len(deleted_topics)} удалённых"
    )

    return alive_topics, deleted_topics, len(topics)

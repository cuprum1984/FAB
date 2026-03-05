# core/services/cleanup/user_cleanup.py
"""
Очистка пользователей и групп:
- cleanup_gdpr: удаление заблокированных пользователей >30 дней
- cleanup_dead_groups: удаление неактивных групп >90 дней
"""
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import TelegramAccount, ManagedGroup
from .base import logger, console_print


async def cleanup_gdpr(session: AsyncSession):
    """
    Удалить пользователей, заблокировавших бота >30 дней назад.

    Условия:
    - is_bot_blocked = True
    - last_activity < 30 дней назад
    """
    msg = "🔍 Проверка пользователей для GDPR очистки..."
    logger.info(msg)
    console_print(msg)

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        # Находим пользователей для удаления
        stmt = select(TelegramAccount).where(
            and_(
                TelegramAccount.is_bot_blocked == True,
                TelegramAccount.last_activity < cutoff_date
            )
        )
        result = await session.execute(stmt)
        users_to_delete = result.scalars().all()

        if not users_to_delete:
            msg = "✅ Нет пользователей для GDPR очистки"
            logger.info(msg)
            console_print(msg)
            return

        msg = f"📊 Найдено {len(users_to_delete)} пользователей для удаления:"
        logger.info(msg)
        console_print(msg)

        # Удаляем пользователей с подробной информацией
        for user in users_to_delete:
            user_info = f"ID: {user.telegram_account_id}"
            if user.telegram_username:
                user_info += f", @{user.telegram_username}"
            if user.telegram_first_name:
                user_info += f", {user.telegram_first_name}"

            log_msg = f"   🗑️ Удаляется пользователь: {user_info}"
            logger.info(log_msg)
            console_print(log_msg)

            logger.info(f"      • Заблокирован: {user.is_bot_blocked}")
            logger.info(f"      • Последняя активность: {user.last_activity}")
            logger.info(f"      • Зарегистрирован: {user.registration_timestamp}")

            await session.delete(user)

        msg = f"✅ GDPR очистка завершена: удалено {len(users_to_delete)} пользователей"
        logger.info(msg)
        console_print(msg)

    except Exception as e:
        error_msg = f"❌ Ошибка при GDPR очистке: {e}"
        logger.error(error_msg)
        console_print(error_msg)
        raise


async def cleanup_dead_groups(session: AsyncSession):
    """
    Удалить неактивные группы (>90 дней).

    Условия:
    - is_bot_active_in_group = False
    - last_seen_at < 90 дней назад
    """
    msg = "🔍 Проверка неактивных групп..."
    logger.info(msg)
    console_print(msg)

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=0)

        # Находим группы для удаления
        stmt = select(ManagedGroup).where(
            and_(
                ManagedGroup.is_bot_active_in_group == False,
                ManagedGroup.last_seen_at < cutoff_date
            )
        )
        result = await session.execute(stmt)
        groups_to_delete = result.scalars().all()

        if not groups_to_delete:
            msg = "✅ Нет неактивных групп для удаления"
            logger.info(msg)
            console_print(msg)
            return

        msg = f"📊 Найдено {len(groups_to_delete)} неактивных групп:"
        logger.info(msg)
        console_print(msg)

        # Удаляем группы
        for group in groups_to_delete:
            log_msg = f"   🗑️ Удаляется группа:"
            logger.info(log_msg)
            console_print(log_msg)

            logger.info(f"      • ID: {group.telegram_chat_id}")
            logger.info(f"      • Название: {group.telegram_chat_title or 'Без названия'}")
            logger.info(f"      • Тип: {group.chat_type}")
            logger.info(f"      • Добавлена: {group.bot_added_timestamp}")
            logger.info(f"      • Последняя активность: {group.last_seen_at}")
            logger.info(f"      • Статус: {'Активна' if group.is_bot_active_in_group else 'Неактивна'}")

            await session.delete(group)

        msg = f"✅ Очистка групп завершена: удалено {len(groups_to_delete)} групп"
        logger.info(msg)
        console_print(msg)

    except Exception as e:
        error_msg = f"❌ Ошибка при очистке групп: {e}"
        logger.error(error_msg)
        console_print(error_msg)
        raise

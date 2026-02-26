# core/services/cleanup/subscription_cleanup.py
"""
Очистка подписок и источников:
- cleanup_orphan_sources: удаление источников без подписок
"""
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource, SourceSubscription
from .base import logger, console_print


async def cleanup_orphan_sources(session: AsyncSession):
    """
    Удалить источники без подписок.

    Условия:
    - нет записей в source_subscriptions с этим source_global_id
    - источник создан >0 дней назад (сразу)
    """
    msg = "🔍 Проверка источников без подписок..."
    logger.info(msg)
    console_print(msg)

    try:
        # Находим все source_global_id, у которых есть подписки
        subquery = select(SourceSubscription.source_global_id).distinct()
        subscribed_sources = await session.execute(subquery)
        subscribed_ids = {row[0] for row in subscribed_sources if row[0]}

        # Находим все источники
        stmt = select(ContentSource)
        result = await session.execute(stmt)
        all_sources = result.scalars().all()

        orphan_sources = []
        cutoff_date = datetime.utcnow()

        for source in all_sources:
            if source.source_global_id not in subscribed_ids:
                # Проверяем возраст источника
                # Приводим к naive для совместимости с SQLite/PostgreSQL
                source_created = source.created_timestamp
                if source_created.tzinfo is not None:
                    source_created = source_created.replace(tzinfo=None)
                if source_created < cutoff_date:
                    orphan_sources.append(source)

        if not orphan_sources:
            msg = "✅ Нет источников-сирот для удаления"
            logger.info(msg)
            console_print(msg)
            return

        msg = f"📊 Найдено {len(orphan_sources)} источников без подписок:"
        logger.info(msg)
        console_print(msg)

        # Удаляем источники
        for source in orphan_sources:
            source_info = f"ID: {source.source_global_id}"
            if source.source_type == "telegram" and source.telegram_username:
                source_info += f", @{source.telegram_username}"
            elif source.source_type == "youtube" and source.youtube_username:
                source_info += f", YouTube: {source.youtube_username}"

            log_msg = f"   🗑️ Удаляется источник: {source_info}"
            logger.info(log_msg)
            console_print(log_msg)

            logger.info(f"      • Тип: {source.source_type}")
            logger.info(f"      • Создан: {source.created_timestamp}")
            logger.info(f"      • Последняя проверка: {source.last_checked_timestamp}")
            logger.info(f"      • Последний пост: {source.last_successful_post_timestamp}")

            await session.delete(source)

        msg = f"✅ Очистка источников завершена: удалено {len(orphan_sources)}"
        logger.info(msg)
        console_print(msg)

    except Exception as e:
        error_msg = f"❌ Ошибка при очистке источников: {e}"
        logger.error(error_msg)
        console_print(error_msg)
        raise

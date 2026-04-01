"""
Лимиты Free плана — защита от злоупотреблений.

Ограничения на ресурсы для одного админа:
- 25 источников всего (TG + YouTube)
- 15 Telegram каналов
- 10 YouTube каналов
- 5 управляемых групп
- 20 топиков в группе
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource, SourceSubscription, ManagedGroup, GroupTopic
from core.settings import settings


class LimitExceededError(Exception):
    """Превышение лимита Free плана"""
    pass


async def check_source_limit(
    user_id: int,
    session: AsyncSession,
    source_type: str = None  # "telegram" | "youtube" | None (все)
) -> dict:
    """
    Проверить лимиты пользователя на источники.

    Возвращает:
    {
        "ok": True/False,
        "current": {"telegram": 5, "youtube": 3, "total": 8},
        "limits": {"telegram": 15, "youtube": 10, "total": 25},
        "error": "text" (если ok=False)
    }
    """
    # Подсчёт текущих источников пользователя
    stmt = select(
        ContentSource.source_type,
        func.count(ContentSource.source_global_id)
    ).join(
        SourceSubscription,
        SourceSubscription.source_global_id == ContentSource.source_global_id
    ).where(
        SourceSubscription.added_by_telegram_account_id == user_id
    ).group_by(
        ContentSource.source_type
    )

    result = await session.execute(stmt)
    counts = {row[0]: row[1] for row in result.all()}

    telegram_count = counts.get("telegram", 0)
    youtube_count = counts.get("youtube", 0)
    total_count = telegram_count + youtube_count

    limits = {
        "telegram": settings.FREE_PLAN_TELEGRAM_LIMIT,
        "youtube": settings.FREE_PLAN_YOUTUBE_LIMIT,
        "total": settings.FREE_PLAN_SOURCES_LIMIT
    }

    # Проверка по типу
    if source_type == "telegram":
        if telegram_count >= settings.FREE_PLAN_TELEGRAM_LIMIT:
            return {
                "ok": False,
                "current": {"telegram": telegram_count, "youtube": youtube_count, "total": total_count},
                "limits": limits,
                "error": f"🚫 Превышен лимит Telegram-каналов: {telegram_count} из {limits['telegram']}"
            }

    elif source_type == "youtube":
        if youtube_count >= settings.FREE_PLAN_YOUTUBE_LIMIT:
            return {
                "ok": False,
                "current": {"telegram": telegram_count, "youtube": youtube_count, "total": total_count},
                "limits": limits,
                "error": f"🚫 Превышен лимит YouTube-каналов: {youtube_count} из {limits['youtube']}"
            }

    # Общая проверка
    if total_count >= settings.FREE_PLAN_SOURCES_LIMIT:
        return {
            "ok": False,
            "current": {"telegram": telegram_count, "youtube": youtube_count, "total": total_count},
            "limits": limits,
            "error": f"🚫 Превышен общий лимит источников: {total_count} из {limits['total']}"
        }

    return {
        "ok": True,
        "current": {"telegram": telegram_count, "youtube": youtube_count, "total": total_count},
        "limits": limits
    }


async def check_group_limit(user_id: int, session: AsyncSession) -> dict:
    """
    Проверить лимит на управляемые группы.

    Возвращает:
    {
        "ok": True/False,
        "current": 3,
        "limit": 5,
        "error": "text" (если ok=False)
    }
    """
    stmt = select(func.count(ManagedGroup.telegram_chat_id)).where(
        ManagedGroup.creator_id == user_id
    )

    count = await session.scalar(stmt)
    limit = settings.FREE_PLAN_GROUPS_LIMIT

    if count >= limit:
        return {
            "ok": False,
            "current": count,
            "limit": limit,
            "error": f"🚫 Превышен лимит групп: {count} из {limit}"
        }

    return {
        "ok": True,
        "current": count,
        "limit": limit
    }


async def check_topic_limit(group_chat_id: int, session: AsyncSession) -> dict:
    """
    Проверить лимит на топики в группе.

    Возвращает:
    {
        "ok": True/False,
        "current": 15,
        "limit": 20,
        "error": "text" (если ok=False)
    }
    """
    stmt = select(func.count(GroupTopic.topic_identifier)).where(
        GroupTopic.telegram_chat_id == group_chat_id
    )

    count = await session.scalar(stmt)
    limit = settings.FREE_PLAN_TOPICS_PER_GROUP_LIMIT

    if count >= limit:
        return {
            "ok": False,
            "current": count,
            "limit": limit,
            "error": f"🚫 Превышен лимит топиков в группе: {count} из {limit}"
        }

    return {
        "ok": True,
        "current": count,
        "limit": limit
    }

"""
Тесты для лимитов Free плана.

Проверка:
- check_source_limit — лимиты на источники
- check_group_limit — лимиты на группы
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource, SourceSubscription, ManagedGroup, TelegramAccount
from core.services.limits import check_source_limit, check_group_limit
from core.settings import settings


@pytest.fixture
async def user_with_sources(db_session):
    """Создать пользователя с источниками"""
    user = TelegramAccount(
        telegram_account_id=999,
        telegram_username="test_user",
        telegram_first_name="Test User"
    )
    db_session.add(user)
    await db_session.flush()

    return user


@pytest.fixture
async def group(db_session, user_with_sources):
    """Создать управляемую группу"""
    group = ManagedGroup(
        telegram_chat_id=-1001234567890,
        telegram_chat_title="Test Group",
        chat_type="supergroup",
        bot_role_in_group="admin",
        creator_id=user_with_sources.telegram_account_id
    )
    db_session.add(group)
    await db_session.flush()

    return group


# =============================================================================
# check_source_limit — ТЕСТЫ
# =============================================================================

@pytest.mark.asyncio
async def test_check_source_limit_ok(db_session, user_with_sources):
    """Лимит не превышен — всё ок"""
    result = await check_source_limit(
        user_id=user_with_sources.telegram_account_id,
        session=db_session
    )

    assert result["ok"] is True
    assert result["current"]["telegram"] == 0
    assert result["current"]["youtube"] == 0
    assert result["current"]["total"] == 0
    assert result["limits"]["telegram"] == settings.FREE_PLAN_TELEGRAM_LIMIT
    assert result["limits"]["youtube"] == settings.FREE_PLAN_YOUTUBE_LIMIT
    assert result["limits"]["total"] == settings.FREE_PLAN_SOURCES_LIMIT


@pytest.mark.asyncio
async def test_check_source_limit_telegram_exceeded(db_session, user_with_sources):
    """Превышен лимит Telegram каналов"""
    # Создать 15 TG источников (лимит)
    for i in range(settings.FREE_PLAN_TELEGRAM_LIMIT):
        source = ContentSource(
            source_global_id=f"@tg_channel_{i}",
            source_type="telegram",
            telegram_username=f"tg_channel_{i}"
        )
        db_session.add(source)

        subscription = SourceSubscription(
            telegram_chat_id=-1001234567890,
            source_global_id=source.source_global_id,
            added_by_telegram_account_id=user_with_sources.telegram_account_id
        )
        db_session.add(subscription)

    await db_session.flush()

    # Проверка лимита
    result = await check_source_limit(
        user_id=user_with_sources.telegram_account_id,
        session=db_session,
        source_type="telegram"
    )

    assert result["ok"] is False
    assert "Telegram" in result["error"]
    assert "15" in result["error"]
    assert result["current"]["telegram"] == 15


@pytest.mark.asyncio
async def test_check_source_limit_youtube_exceeded(db_session, user_with_sources):
    """Превышен лимит YouTube каналов"""
    # Создать 10 YouTube источников (лимит)
    for i in range(settings.FREE_PLAN_YOUTUBE_LIMIT):
        source = ContentSource(
            source_global_id=f"yt_channel_{i}",
            source_type="youtube",
            feed_url=f"https://youtube.com/feeds/videos.xml?channel_id=yt_channel_{i}"
        )
        db_session.add(source)

        subscription = SourceSubscription(
            telegram_chat_id=-1001234567890,
            source_global_id=source.source_global_id,
            added_by_telegram_account_id=user_with_sources.telegram_account_id
        )
        db_session.add(subscription)

    await db_session.flush()

    # Проверка лимита
    result = await check_source_limit(
        user_id=user_with_sources.telegram_account_id,
        session=db_session,
        source_type="youtube"
    )

    assert result["ok"] is False
    assert "YouTube" in result["error"]
    assert "10" in result["error"]
    assert result["current"]["youtube"] == 10


@pytest.mark.asyncio
async def test_check_source_limit_total_exceeded(db_session, user_with_sources):
    """Превышен общий лимит источников"""
    # Создать 25 источников (лимит)
    for i in range(settings.FREE_PLAN_SOURCES_LIMIT):
        source_type = "telegram" if i < 15 else "youtube"
        source = ContentSource(
            source_global_id=f"@channel_{i}",
            source_type=source_type,
            telegram_username=f"channel_{i}" if source_type == "telegram" else None,
            feed_url=f"https://youtube.com/{i}" if source_type == "youtube" else None
        )
        db_session.add(source)

        subscription = SourceSubscription(
            telegram_chat_id=-1001234567890,
            source_global_id=source.source_global_id,
            added_by_telegram_account_id=user_with_sources.telegram_account_id
        )
        db_session.add(subscription)

    await db_session.flush()

    # Проверка общего лимита
    result = await check_source_limit(
        user_id=user_with_sources.telegram_account_id,
        session=db_session
    )

    assert result["ok"] is False
    assert "общий лимит" in result["error"].lower() or "total" in result["error"].lower()
    assert result["current"]["total"] == 25


@pytest.mark.asyncio
async def test_check_source_limit_mixed_counts(db_session, user_with_sources):
    """Проверка смешанных счётчиков (5 TG + 3 YouTube)"""
    # Создать 5 TG источников
    for i in range(5):
        source = ContentSource(
            source_global_id=f"@tg_{i}",
            source_type="telegram",
            telegram_username=f"tg_{i}"
        )
        db_session.add(source)
        subscription = SourceSubscription(
            telegram_chat_id=-1001234567890,
            source_global_id=source.source_global_id,
            added_by_telegram_account_id=user_with_sources.telegram_account_id
        )
        db_session.add(subscription)

    # Создать 3 YouTube источника
    for i in range(3):
        source = ContentSource(
            source_global_id=f"yt_{i}",
            source_type="youtube",
            feed_url=f"https://youtube.com/{i}"
        )
        db_session.add(source)
        subscription = SourceSubscription(
            telegram_chat_id=-1001234567890,
            source_global_id=source.source_global_id,
            added_by_telegram_account_id=user_with_sources.telegram_account_id
        )
        db_session.add(subscription)

    await db_session.flush()

    # Проверка
    result = await check_source_limit(
        user_id=user_with_sources.telegram_account_id,
        session=db_session
    )

    assert result["ok"] is True
    assert result["current"]["telegram"] == 5
    assert result["current"]["youtube"] == 3
    assert result["current"]["total"] == 8


# =============================================================================
# check_group_limit — ТЕСТЫ
# =============================================================================

@pytest.mark.asyncio
async def test_check_group_limit_ok(db_session, user_with_sources):
    """Лимит на группы не превышен"""
    result = await check_group_limit(
        user_id=user_with_sources.telegram_account_id,
        session=db_session
    )

    assert result["ok"] is True
    assert result["current"] == 0
    assert result["limit"] == 5


@pytest.mark.asyncio
async def test_check_group_limit_exceeded(db_session, user_with_sources):
    """Превышен лимит на группы"""
    # Создать 5 групп (лимит)
    for i in range(settings.FREE_PLAN_GROUPS_LIMIT):
        group = ManagedGroup(
            telegram_chat_id=-1001234567890 - i,
            telegram_chat_title=f"Group {i}",
            chat_type="supergroup",
            bot_role_in_group="admin",
            creator_id=user_with_sources.telegram_account_id
        )
        db_session.add(group)

    await db_session.flush()

    # Проверка лимита
    result = await check_group_limit(
        user_id=user_with_sources.telegram_account_id,
        session=db_session
    )

    assert result["ok"] is False
    assert "групп" in result["error"].lower() or "group" in result["error"].lower()
    assert "5" in result["error"]
    assert result["current"] == 5


@pytest.mark.asyncio
async def test_check_group_limit_with_existing_group(db_session, user_with_sources, group):
    """Проверка с одной существующей группой"""
    result = await check_group_limit(
        user_id=user_with_sources.telegram_account_id,
        session=db_session
    )

    assert result["ok"] is True
    assert result["current"] == 1
    assert result["limit"] == 5

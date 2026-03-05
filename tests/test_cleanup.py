"""
Тесты для GDPR и очистки данных.
Проверяют корректность удаления пользователей, групп, источников и тем.
"""
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from core.models import TelegramAccount, ManagedGroup, ContentSource, GroupTopic
from core.services.cleanup_service import CleanupService


# =============================================================================
# GDPR ТЕСТЫ (удаление заблокированных пользователей >30 дней)
# =============================================================================

@pytest.mark.asyncio
async def test_gdpr_removes_blocked_user_old(db_session):
    """GDPR удаляет заблокированных пользователей >30 дней"""

    # 1️⃣ ПОДГОТОВКА — пользователь заблокирован 31 день назад
    old_date = datetime.now(timezone.utc) - timedelta(days=31)
    user = TelegramAccount(
        telegram_account_id=99999,
        telegram_username="test_user",
        telegram_first_name="Test",
        is_bot_blocked=True,
        last_activity=old_date
    )
    db_session.add(user)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ — запускаем очистку
    cleanup = CleanupService()
    await cleanup._cleanup_gdpr(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — пользователь удалён
    result = await db_session.execute(
        select(TelegramAccount).where(TelegramAccount.telegram_account_id == 99999)
    )
    deleted_user = result.scalar()

    assert deleted_user is None, "Заблокированный пользователь должен быть удалён"


@pytest.mark.asyncio
async def test_gdpr_keeps_active_user(db_session):
    """GDPR НЕ удаляет активных пользователей (<30 дней)"""

    # 1️⃣ ПОДГОТОВКА — пользователь активен (вчера)
    recent_date = datetime.now(timezone.utc) - timedelta(days=1)
    user = TelegramAccount(
        telegram_account_id=88888,
        telegram_username="active_user",
        telegram_first_name="Active",
        is_bot_blocked=True,  # Заблокирован, но недавно
        last_activity=recent_date
    )
    db_session.add(user)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_gdpr(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — пользователь остался
    result = await db_session.execute(
        select(TelegramAccount).where(TelegramAccount.telegram_account_id == 88888)
    )
    active_user = result.scalar()

    assert active_user is not None, "Активный пользователь НЕ должен быть удалён"


@pytest.mark.asyncio
async def test_gdpr_keeps_unblocked_user(db_session):
    """GDPR НЕ удаляет незаблокированных пользователей"""

    # 1️⃣ ПОДГОТОВКА — пользователь не заблокирован, но старая активность
    old_date = datetime.now(timezone.utc) - timedelta(days=60)
    user = TelegramAccount(
        telegram_account_id=77777,
        telegram_username="unblocked_user",
        telegram_first_name="Unblocked",
        is_bot_blocked=False,  # Не заблокирован
        last_activity=old_date
    )
    db_session.add(user)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_gdpr(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — пользователь остался
    result = await db_session.execute(
        select(TelegramAccount).where(TelegramAccount.telegram_account_id == 77777)
    )
    unblocked_user = result.scalar()

    assert unblocked_user is not None, "Незаблокированный пользователь НЕ должен быть удалён"


# =============================================================================
# ТЕСТЫ ОЧИСТКИ ГРУПП (удаление неактивных групп >90 дней)
# =============================================================================

@pytest.mark.asyncio
async def test_cleanup_removes_dead_group(db_session):
    """Очистка удаляет группы, где бот неактивен >90 дней"""

    # 1️⃣ ПОДГОТОВКА — группа неактивна 91 день
    old_date = datetime.now(timezone.utc) - timedelta(days=91)
    group = ManagedGroup(
        telegram_chat_id=-111111,
        telegram_chat_title="Dead Group",
        chat_type="supergroup",
        bot_role_in_group="member",  # Обязательное поле
        is_bot_active_in_group=False,
        last_seen_at=old_date,
        bot_added_timestamp=datetime.now(timezone.utc) - timedelta(days=100)
    )
    db_session.add(group)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_dead_groups(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — группа удалена
    result = await db_session.execute(
        select(ManagedGroup).where(ManagedGroup.telegram_chat_id == -111111)
    )
    deleted_group = result.scalar()

    assert deleted_group is None, "Неактивная группа должна быть удалена"


@pytest.mark.asyncio
async def test_cleanup_keeps_active_group(db_session):
    """Очистка НЕ удаляет активные группы"""

    # 1️⃣ ПОДГОТОВКА — группа активна
    recent_date = datetime.now(timezone.utc) - timedelta(days=10)
    group = ManagedGroup(
        telegram_chat_id=-222222,
        telegram_chat_title="Active Group",
        chat_type="supergroup",
        bot_role_in_group="admin",  # Обязательное поле
        is_bot_active_in_group=True,  # Активна
        last_seen_at=recent_date,
        bot_added_timestamp=datetime.now(timezone.utc) - timedelta(days=20)
    )
    db_session.add(group)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_dead_groups(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — группа осталась
    result = await db_session.execute(
        select(ManagedGroup).where(ManagedGroup.telegram_chat_id == -222222)
    )
    active_group = result.scalar()

    assert active_group is not None, "Активная группа НЕ должна быть удалена"


# =============================================================================
# ТЕСТЫ ОЧИСТКИ ИСТОЧНИКОВ (удаление источников без подписок)
# =============================================================================

@pytest.mark.asyncio
async def test_cleanup_removes_orphan_source(db_session):
    """Очистка удаляет источники без подписок"""

    # 1️⃣ ПОДГОТОВКА — источник без подписок
    source = ContentSource(
        source_global_id="orphan_source_123",
        source_type="telegram",
        telegram_username="orphan_channel",
        created_timestamp=datetime.now(timezone.utc) - timedelta(days=1),
        last_checked_timestamp=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.add(source)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_orphan_sources(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — источник удалён
    result = await db_session.execute(
        select(ContentSource).where(ContentSource.source_global_id == "orphan_source_123")
    )
    deleted_source = result.scalar()

    assert deleted_source is None, "Источник без подписок должен быть удалён"


@pytest.mark.asyncio
async def test_cleanup_keeps_source_with_subscriptions(db_session):
    """Очистка НЕ удаляет источники с подписками"""

    # 1️⃣ ПОДГОТОВКА — источник с подпиской
    from core.models import SourceSubscription
    
    source = ContentSource(
        source_global_id="active_source_456",
        source_type="telegram",
        telegram_username="active_channel",
        created_timestamp=datetime.now(timezone.utc) - timedelta(days=1),
        last_checked_timestamp=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.add(source)
    
    subscription = SourceSubscription(
        source_global_id="active_source_456",
        telegram_chat_id=-999999,
        added_by_telegram_account_id=12345
    )
    db_session.add(subscription)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_orphan_sources(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — источник остался
    result = await db_session.execute(
        select(ContentSource).where(ContentSource.source_global_id == "active_source_456")
    )
    active_source = result.scalar()

    assert active_source is not None, "Источник с подписками НЕ должен быть удалён"


# =============================================================================
# ТЕСТЫ ОЧИСТКИ ТЕМ (удаление удалённых и старых тем)
# =============================================================================

@pytest.mark.asyncio
async def test_cleanup_removes_nonexistent_topic(db_session):
    """Очистка удаляет темы, помеченные как несуществующие в Telegram"""

    # 1️⃣ ПОДГОТОВКА — тема помечена как удалённая
    topic = GroupTopic(
        topic_identifier="topic_999",
        topic_name="Deleted Topic",
        telegram_chat_id=-111111,
        is_exists_in_tg=False,  # Помечена как удалённая
        created_timestamp=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.add(topic)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_orphan_topics(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — тема удалена
    result = await db_session.execute(
        select(GroupTopic).where(GroupTopic.topic_identifier == "topic_999")
    )
    deleted_topic = result.scalar()

    assert deleted_topic is None, "Удалённая тема должна быть очищена"


@pytest.mark.asyncio
async def test_cleanup_removes_nonexistent_topic_created_today(db_session):
    """Очистка удаляет темы, помеченные как удалённые, даже если созданы сегодня и есть назначения"""
    from core.models import SourceSubscription, TopicSourceAssignment

    # 1️⃣ ПОДГОТОВКА — тема помечена как удалённая, создана сегодня + есть назначение
    topic = GroupTopic(
        topic_identifier="topic_today_001",
        topic_name="Deleted Topic Today",
        telegram_chat_id=-111111,
        is_exists_in_tg=False,  # Помечена как удалённая
        created_timestamp=datetime.now(timezone.utc)  # Создана только что
    )
    db_session.add(topic)

    # Добавляем назначение (которое должно удалиться через CASCADE)
    subscription = SourceSubscription(
        source_global_id="test_source_123",
        telegram_chat_id=-111111,
        added_by_telegram_account_id=99999
    )
    db_session.add(subscription)
    await db_session.commit()

    assignment = TopicSourceAssignment(
        topic_identifier="topic_today_001",
        subscription_id=subscription.subscription_id
    )
    db_session.add(assignment)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_orphan_topics(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — тема удалена (даже если создана сегодня)
    result = await db_session.execute(
        select(GroupTopic).where(GroupTopic.topic_identifier == "topic_today_001")
    )
    deleted_topic = result.scalar()

    assert deleted_topic is None, "Удалённая тема должна быть очищена, даже если создана сегодня"

    # 4️⃣ ПРОВЕРКА — назначение тоже удалено (CASCADE)
    result = await db_session.execute(
        select(TopicSourceAssignment).where(
            TopicSourceAssignment.topic_identifier == "topic_today_001"
        )
    )
    deleted_assignment = result.scalar()

    assert deleted_assignment is None, "Назначение должно быть удалено через CASCADE"


@pytest.mark.asyncio
async def test_cleanup_removes_old_topic(db_session):
    """Очистка удаляет темы без активности /plus >90 дней"""

    # 1️⃣ ПОДГОТОВКА — тема без активности 91 день
    old_date = datetime.now(timezone.utc) - timedelta(days=91)
    topic = GroupTopic(
        topic_identifier="old_topic_777",
        topic_name="Old Topic",
        telegram_chat_id=-222222,
        is_exists_in_tg=True,
        last_seen_at=old_date,  # Последнее посещение 91 день назад
        created_timestamp=datetime.now(timezone.utc) - timedelta(days=100)
    )
    db_session.add(topic)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_old_topics(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — тема удалена
    result = await db_session.execute(
        select(GroupTopic).where(GroupTopic.topic_identifier == "old_topic_777")
    )
    deleted_topic = result.scalar()

    assert deleted_topic is None, "Старая тема должна быть удалена"


@pytest.mark.asyncio
async def test_cleanup_keeps_general_topic(db_session):
    """Очистка НЕ удаляет General темы"""

    # 1️⃣ ПОДГОТОВКА — General тема без активности
    old_date = datetime.now(timezone.utc) - timedelta(days=100)
    topic = GroupTopic(
        topic_identifier="general_topic_111",
        topic_name="General",  # General тема
        telegram_chat_id=-333333,
        is_exists_in_tg=True,
        last_seen_at=old_date,
        created_timestamp=datetime.now(timezone.utc) - timedelta(days=150)
    )
    db_session.add(topic)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ
    cleanup = CleanupService()
    await cleanup._cleanup_old_topics(db_session)
    await db_session.commit()

    # 3️⃣ ПРОВЕРКА — General тема осталась
    result = await db_session.execute(
        select(GroupTopic).where(GroupTopic.topic_identifier == "general_topic_111")
    )
    general_topic = result.scalar()

    assert general_topic is not None, "General тема НЕ должна быть удалена"

"""
Тесты для TopicSourceAssignment — связующего звена между подписками и темами.
Бизнес-правило: «Посты из этого источника → отправлять в эту тему»
"""
import pytest
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from core.models import (
    TelegramAccount,
    ManagedGroup,
    GroupTopic,
    ContentSource,
    SourceSubscription,
    TopicSourceAssignment
)


# =============================================================================
# HELPER-ФУНКЦИИ (для DRY)
# =============================================================================

async def create_user_group_topic_chain(db_session, user_id: int = 12345, 
                                         chat_id: int = -999999, 
                                         topic_name: str = "TestTopic"):
    """
    Создаёт цепочку: Пользователь → Группа → Тема
    
    Возвращает: (user, group, topic)
    """
    # 1. Пользователь
    user = TelegramAccount(
        telegram_account_id=user_id,
        telegram_username=f"user{user_id}",
        telegram_first_name="Test User"
    )
    db_session.add(user)
    await db_session.flush()
    
    # 2. Группа (ссылается на creator_id)
    group = ManagedGroup(
        telegram_chat_id=chat_id,
        telegram_chat_title="Test Group",
        chat_type="supergroup",
        bot_role_in_group="admin",
        creator_id=user_id
    )
    db_session.add(group)
    await db_session.flush()
    
    # 3. Тема (ссылается на группу и создателя)
    topic = GroupTopic(
        topic_identifier=f"topic_{topic_name}_{chat_id}",
        telegram_chat_id=chat_id,
        topic_name=topic_name,
        created_by_telegram_account_id=user_id
    )
    db_session.add(topic)
    await db_session.flush()
    
    return user, group, topic


async def create_source_subscription_chain(db_session, source_id: str = "test_source",
                                            chat_id: int = -999999):
    """
    Создаёт цепочку: Источник → Подписка
    
    Возвращает: (source, subscription)
    """
    # 1. Источник
    source = ContentSource(
        source_global_id=source_id,
        source_type="telegram",
        telegram_username=source_id.replace("@", ""),
        channel_title=f"Test Channel {source_id}"
    )
    db_session.add(source)
    await db_session.flush()
    
    # 2. Подписка (ссылается на группу и источник)
    subscription = SourceSubscription(
        telegram_chat_id=chat_id,
        source_global_id=source_id
    )
    db_session.add(subscription)
    await db_session.flush()
    
    return source, subscription


# =============================================================================
# 🔴 СЦЕНАРИЙ 1: БАЗОВОЕ СОЗДАНИЕ НАЗНАЧЕНИЯ
# =============================================================================

@pytest.mark.asyncio
async def test_basic_assignment_creation(db_session):
    """Базовое создание назначения: тема ← подписка"""
    
    # 1️⃣ ARRANGE — создаём цепочку объектов
    user, group, topic = await create_user_group_topic_chain(
        db_session, 
        user_id=11111,
        chat_id=-111111,
        topic_name="News"
    )
    
    source, subscription = await create_source_subscription_chain(
        db_session,
        source_id="@durov",
        chat_id=-111111
    )
    
    # 2️⃣ ACT — создаём назначение
    assignment = TopicSourceAssignment(
        topic_identifier=topic.topic_identifier,
        subscription_id=subscription.subscription_id
    )
    db_session.add(assignment)
    await db_session.commit()
    
    # 3️⃣ ASSERT — проверяем, что назначение сохранилось
    result = await db_session.execute(
        select(TopicSourceAssignment).where(
            TopicSourceAssignment.assignment_id == assignment.assignment_id
        )
    )
    saved_assignment = result.scalar()
    
    assert saved_assignment is not None, "Назначение должно сохраниться"
    assert saved_assignment.topic_identifier == topic.topic_identifier
    assert saved_assignment.subscription_id == subscription.subscription_id
    assert saved_assignment.source_global_id == "@durov"


# =============================================================================
# 🔴 СЦЕНАРИЙ 2: ОДИН ИСТОЧНИК → МНОГО ТЕМ
# =============================================================================

@pytest.mark.asyncio
async def test_one_source_multiple_topics(db_session):
    """Один источник назначен на три разные темы"""
    
    # 1️⃣ ARRANGE — создаём группу, источник и 3 темы
    user, group, topic1 = await create_user_group_topic_chain(
        db_session,
        user_id=22222,
        chat_id=-222222,
        topic_name="News"
    )
    
    topic2 = GroupTopic(
        topic_identifier="topic_Tech_-222222",
        telegram_chat_id=-222222,
        topic_name="Technology",
        created_by_telegram_account_id=22222
    )
    db_session.add(topic2)
    
    topic3 = GroupTopic(
        topic_identifier="topic_General_-222222",
        telegram_chat_id=-222222,
        topic_name="General",
        created_by_telegram_account_id=22222
    )
    db_session.add(topic3)
    await db_session.flush()
    
    source, subscription = await create_source_subscription_chain(
        db_session,
        source_id="@techcrunch",
        chat_id=-222222
    )
    
    # Создаём 3 назначения для одного источника
    for topic in [topic1, topic2, topic3]:
        assignment = TopicSourceAssignment(
            topic_identifier=topic.topic_identifier,
            subscription_id=subscription.subscription_id
        )
        db_session.add(assignment)
    
    await db_session.commit()
    
    # 2️⃣ ACT — запрашиваем все назначения для этой подписки
    result = await db_session.execute(
        select(TopicSourceAssignment).where(
            TopicSourceAssignment.subscription_id == subscription.subscription_id
        )
    )
    assignments = result.scalars().all()
    
    # 3️⃣ ASSERT — все 3 темы назначены
    assert len(assignments) == 3, "Должно быть 3 назначения"
    
    topic_identifiers = {a.topic_identifier for a in assignments}
    assert topic.topic_identifier in topic_identifiers
    assert topic2.topic_identifier in topic_identifiers
    assert topic3.topic_identifier in topic_identifiers
    
    # Все назначения имеют одинаковый subscription_id
    assert all(a.subscription_id == subscription.subscription_id for a in assignments)


# =============================================================================
# 🔴 СЦЕНАРИЙ 3: UNIQUECONSTRAINT ПРЕДОТВРАЩАЕТ ДУБЛИ
# =============================================================================

@pytest.mark.asyncio
async def test_unique_constraint_prevents_duplicates(db_session):
    """UniqueConstraint не позволяет создать дубль назначения"""
    
    # 1️⃣ ARRANGE — создаём базовую цепочку
    user, group, topic = await create_user_group_topic_chain(
        db_session,
        user_id=33333,
        chat_id=-333333,
        topic_name="UniqueTest"
    )
    
    source, subscription = await create_source_subscription_chain(
        db_session,
        source_id="@unique_source",
        chat_id=-333333
    )
    
    # Создаём первое назначение
    assignment1 = TopicSourceAssignment(
        topic_identifier=topic.topic_identifier,
        subscription_id=subscription.subscription_id
    )
    db_session.add(assignment1)
    await db_session.commit()
    
    # 2️⃣ ACT — пытаемся создать дубль
    assignment2 = TopicSourceAssignment(
        topic_identifier=topic.topic_identifier,  # Та же тема
        subscription_id=subscription.subscription_id  # Та же подписка
    )
    db_session.add(assignment2)
    
    # 3️⃣ ASSERT — IntegrityError при commit()
    with pytest.raises(IntegrityError):
        await db_session.commit()
    
    # Откатываем транзакцию для продолжения тестов
    await db_session.rollback()


# =============================================================================
# 🟡 СЦЕНАРИЙ 4: CASCADE УДАЛЕНИЕ ПРИ УДАЛЕНИИ ТЕМЫ
# =============================================================================

@pytest.mark.asyncio
async def test_cascade_delete_when_topic_deleted(db_session):
    """При удалении темы назначения удаляются автоматически (CASCADE)"""
    
    # 1️⃣ ARRANGE — создаём цепочку с назначением
    user, group, topic = await create_user_group_topic_chain(
        db_session,
        user_id=44444,
        chat_id=-444444,
        topic_name="CascadeTopic"
    )
    
    source, subscription = await create_source_subscription_chain(
        db_session,
        source_id="@cascade_source",
        chat_id=-444444
    )
    
    assignment = TopicSourceAssignment(
        topic_identifier=topic.topic_identifier,
        subscription_id=subscription.subscription_id
    )
    db_session.add(assignment)
    await db_session.commit()
    
    assignment_id = assignment.assignment_id
    
    # 2️⃣ ACT — удаляем тему
    await db_session.delete(topic)
    await db_session.commit()
    
    # 3️⃣ ASSERT — назначение удалено автоматически
    result = await db_session.execute(
        select(TopicSourceAssignment).where(
            TopicSourceAssignment.assignment_id == assignment_id
        )
    )
    deleted_assignment = result.scalar()
    
    assert deleted_assignment is None, "Назначение должно удалиться CASCADE"


# =============================================================================
# 🟡 СЦЕНАРИЙ 5: CASCADE УДАЛЕНИЕ ПРИ УДАЛЕНИИ ПОДПИСКИ
# =============================================================================

@pytest.mark.asyncio
async def test_cascade_delete_when_subscription_deleted(db_session):
    """При удалении подписки назначения удаляются автоматически (CASCADE)"""
    
    # 1️⃣ ARRANGE — создаём цепочку с назначением
    user, group, topic = await create_user_group_topic_chain(
        db_session,
        user_id=55555,
        chat_id=-555555,
        topic_name="CascadeSubTopic"
    )
    
    source, subscription = await create_source_subscription_chain(
        db_session,
        source_id="@cascade_sub",
        chat_id=-555555
    )
    
    assignment = TopicSourceAssignment(
        topic_identifier=topic.topic_identifier,
        subscription_id=subscription.subscription_id
    )
    db_session.add(assignment)
    await db_session.commit()
    
    assignment_id = assignment.assignment_id
    
    # 2️⃣ ACT — удаляем подписку
    await db_session.delete(subscription)
    await db_session.commit()
    
    # 3️⃣ ASSERT — назначение удалено автоматически
    result = await db_session.execute(
        select(TopicSourceAssignment).where(
            TopicSourceAssignment.assignment_id == assignment_id
        )
    )
    deleted_assignment = result.scalar()
    
    assert deleted_assignment is None, "Назначение должно удалиться CASCADE"


# =============================================================================
# 🟡 СЦЕНАРИЙ 6: ФИЛЬТРАЦИЯ ПО ГРУППЕ (МУЛЬТИТЕНАНТНОСТЬ)
# =============================================================================

@pytest.mark.asyncio
async def test_multitenancy_filtering_by_group(db_session):
    """Один источник в двух группах → назначения не пересекаются"""
    
    # 1️⃣ ARRANGE — Группа А
    user_a, group_a, topic_a = await create_user_group_topic_chain(
        db_session,
        user_id=66666,
        chat_id=-666666,
        topic_name="GroupA_Topic"
    )
    
    # Общий источник для обеих групп
    source, subscription_a = await create_source_subscription_chain(
        db_session,
        source_id="@shared_source",
        chat_id=-666666
    )
    
    assignment_a = TopicSourceAssignment(
        topic_identifier=topic_a.topic_identifier,
        subscription_id=subscription_a.subscription_id
    )
    db_session.add(assignment_a)
    
    # 2️⃣ ARRANGE — Группа Б (тот же источник!)
    user_b, group_b, topic_b = await create_user_group_topic_chain(
        db_session,
        user_id=77777,
        chat_id=-777777,
        topic_name="GroupB_Topic"
    )
    
    # Подписка на тот же источник, но для другой группы
    subscription_b = SourceSubscription(
        telegram_chat_id=-777777,
        source_global_id="@shared_source"
    )
    db_session.add(subscription_b)
    await db_session.flush()  # 🔥 Получаем subscription_id перед созданием назначения
    
    assignment_b = TopicSourceAssignment(
        topic_identifier=topic_b.topic_identifier,
        subscription_id=subscription_b.subscription_id
    )
    db_session.add(assignment_b)
    
    await db_session.commit()
    
    # 3️⃣ ACT — запрашиваем назначения для группы А (через subscription)
    result = await db_session.execute(
        select(TopicSourceAssignment).where(
            TopicSourceAssignment.subscription_id == subscription_a.subscription_id
        )
    )
    assignments_for_a = result.scalars().all()
    
    # 4️⃣ ASSERT — только тема из группы А
    assert len(assignments_for_a) == 1, "Группа А должна иметь 1 назначение"
    assert assignments_for_a[0].topic_identifier == topic_a.topic_identifier
    assert assignments_for_a[0].topic_identifier != topic_b.topic_identifier


# =============================================================================
# 🟢 СЦЕНАРИЙ 7: СВЯЗЬ С CONTENTSOURCE ЧЕРЕЗ SUBSCRIPTION
# =============================================================================

@pytest.mark.asyncio
async def test_relationship_with_content_source(db_session):
    """Можно получить source_global_id через relationship"""
    
    # 1️⃣ ARRANGE — создаём цепочку
    user, group, topic = await create_user_group_topic_chain(
        db_session,
        user_id=88888,
        chat_id=-888888,
        topic_name="RelationTopic"
    )
    
    source, subscription = await create_source_subscription_chain(
        db_session,
        source_id="@relation_test",
        chat_id=-888888
    )
    
    assignment = TopicSourceAssignment(
        topic_identifier=topic.topic_identifier,
        subscription_id=subscription.subscription_id
    )
    db_session.add(assignment)
    await db_session.commit()
    
    # 2️⃣ ACT — загружаем назначение с relationship
    result = await db_session.execute(
        select(TopicSourceAssignment)
        .where(TopicSourceAssignment.assignment_id == assignment.assignment_id)
    )
    loaded_assignment = result.scalar()
    
    # 3️⃣ ASSERT — relationship работает
    assert loaded_assignment is not None
    
    # Через subscription можно получить источник
    assert loaded_assignment.subscription is not None
    assert loaded_assignment.subscription.source_global_id == "@relation_test"
    
    # property source_global_id работает
    assert loaded_assignment.source_global_id == "@relation_test"


# =============================================================================
# 🟢 СЦЕНАРИЙ 8: УДАЛЕНИЕ НАЗНАЧЕНИЯ (БЕЗ CASCADE)
# =============================================================================

@pytest.mark.asyncio
async def test_delete_assignment_directly(db_session):
    """Прямое удаление назначения не влияет на тему и подписку"""
    
    # 1️⃣ ARRANGE — создаём цепочку
    user, group, topic = await create_user_group_topic_chain(
        db_session,
        user_id=99999,
        chat_id=-999999,
        topic_name="DeleteTest"
    )
    
    source, subscription = await create_source_subscription_chain(
        db_session,
        source_id="@delete_test",
        chat_id=-999999
    )
    
    assignment = TopicSourceAssignment(
        topic_identifier=topic.topic_identifier,
        subscription_id=subscription.subscription_id
    )
    db_session.add(assignment)
    await db_session.commit()
    
    assignment_id = assignment.assignment_id
    topic_identifier = topic.topic_identifier
    subscription_id = subscription.subscription_id
    
    # 2️⃣ ACT — удаляем только назначение
    await db_session.delete(assignment)
    await db_session.commit()
    
    # 3️⃣ ASSERT — назначение удалено, но тема и подписка остались
    result_assignment = await db_session.execute(
        select(TopicSourceAssignment).where(
            TopicSourceAssignment.assignment_id == assignment_id
        )
    )
    assert result_assignment.scalar() is None, "Назначение должно быть удалено"
    
    result_topic = await db_session.execute(
        select(GroupTopic).where(
            GroupTopic.topic_identifier == topic_identifier
        )
    )
    assert result_topic.scalar() is not None, "Тема должна остаться"
    
    result_subscription = await db_session.execute(
        select(SourceSubscription).where(
            SourceSubscription.subscription_id == subscription_id
        )
    )
    assert result_subscription.scalar() is not None, "Подписка должна остаться"

"""
Тесты для destination_service.
Проверяют функции работы с группами, темами, подписками и назначениями.
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from core.models import (
    TelegramAccount, ManagedGroup, GroupTopic,
    ContentSource, SourceSubscription, TopicSourceAssignment,
    UserChannelSubscription
)
from core.services.destination_service import (
    TopicUtils,
    get_or_create_content_source,
    create_user_channel_subscription,
    get_user_groups,
    get_user_destinations,
    create_or_update_topic,
    create_topic_assignment,
    check_destination_access,
    get_source_last_post_id,
    update_source_last_post_id,
)


# =============================================================================
# HELPER-ФУНКЦИИ (DRY)
# =============================================================================

async def create_user_group_topic_chain(db_session, user_id=12345, chat_id=-1001234567890):
    """
    Создать цепочку: пользователь → группа → тема.
    Возвращает dict с объектами.
    """
    user = TelegramAccount(
        telegram_account_id=user_id,
        telegram_username="test_user",
        telegram_first_name="Test"
    )
    db_session.add(user)

    group = ManagedGroup(
        telegram_chat_id=chat_id,
        telegram_chat_title="Test Group",
        chat_type="supergroup",
        bot_role_in_group="admin",
        creator_id=user_id,
        is_bot_active_in_group=True
    )
    db_session.add(group)

    topic = GroupTopic(
        topic_identifier=f"{chat_id}:42",
        telegram_chat_id=chat_id,
        telegram_thread_id=42,
        topic_name="News",
        created_by_telegram_account_id=user_id
    )
    db_session.add(topic)
    await db_session.commit()

    return {"user": user, "group": group, "topic": topic}


async def create_source_subscription_chain(db_session, chat_id=-1001234567890):
    """
    Создать цепочку: источник → подписка.
    Возвращает dict с объектами.
    """
    source = ContentSource(
        source_global_id="tg_channel_durov",
        source_type="telegram",
        telegram_username="durov"
    )
    db_session.add(source)

    subscription = SourceSubscription(
        telegram_chat_id=chat_id,
        source_global_id="tg_channel_durov",
        added_by_telegram_account_id=12345
    )
    db_session.add(subscription)
    await db_session.commit()

    return {"source": source, "subscription": subscription}


# =============================================================================
# TOPICUTILS ТЕСТЫ
# =============================================================================

class TestTopicUtils:

    def test_topic_utils_generate_identifier_with_thread(self):
        """Генерация идентификатора с thread_id"""
        identifier = TopicUtils.generate_topic_identifier(-1001234567890, 42)
        assert identifier == "-1001234567890:42"

    def test_topic_utils_generate_identifier_general(self):
        """Генерация идентификатора для General темы (без thread)"""
        identifier = TopicUtils.generate_topic_identifier(-1001234567890, None)
        assert identifier == "-1001234567890:0"

    def test_topic_utils_generate_identifier_zero_thread(self):
        """Генерация идентификатора с thread_id=0 (General)"""
        identifier = TopicUtils.generate_topic_identifier(-1001234567890, 0)
        assert identifier == "-1001234567890:0"

    def test_topic_utils_parse_identifier(self):
        """Парсинг идентификатора обратно в tuple"""
        chat_id, thread_id = TopicUtils.parse_topic_identifier("-1001234567890:42")
        assert chat_id == -1001234567890
        assert thread_id == 42

    def test_topic_utils_parse_general_identifier(self):
        """Парсинг General темы (thread_id = None)"""
        chat_id, thread_id = TopicUtils.parse_topic_identifier("-1001234567890:0")
        assert chat_id == -1001234567890
        assert thread_id is None

    def test_topic_utils_is_general_topic(self):
        """Определение General темы"""
        assert TopicUtils.is_general_topic("-1001234567890:0") == True
        assert TopicUtils.is_general_topic("-1001234567890:42") == False

    def test_topic_utils_parse_invalid_identifier(self):
        """Парсинг невалидного идентификатора вызывает ValueError"""
        with pytest.raises(ValueError):
            TopicUtils.parse_topic_identifier("invalid_format")

    def test_topic_utils_parse_empty_identifier(self):
        """Парсинг пустого идентификатора вызывает ValueError"""
        with pytest.raises(ValueError):
            TopicUtils.parse_topic_identifier("")


# =============================================================================
# GET_OR_CREATE_CONTENT_SOURCE ТЕСТЫ
# =============================================================================

@pytest.mark.asyncio
class TestGetOrCreateContentSource:

    async def test_get_or_create_source_creates_new(self, db_session):
        """Создание нового источника"""
        source, created = await get_or_create_content_source(
            session=db_session,
            source_global_id="tg_channel_durov",
            source_type="telegram",
            telegram_username="durov",
            channel_title="Durov's Channel"
        )

        assert created == True
        assert source.source_global_id == "tg_channel_durov"
        assert source.telegram_username == "durov"
        assert source.channel_title == "Durov's Channel"

    async def test_get_or_create_source_updates_existing(self, db_session):
        """Обновление существующего источника"""
        # Первое создание
        source1, created1 = await get_or_create_content_source(
            session=db_session,
            source_global_id="tg_channel_durov",
            source_type="telegram",
            telegram_username="durov"
        )
        assert created1 == True

        # Второе получение (должно обновить, а не создать)
        source2, created2 = await get_or_create_content_source(
            session=db_session,
            source_global_id="tg_channel_durov",
            source_type="telegram",
            telegram_username="durov",
            channel_title="Updated Title"
        )
        assert created2 == False
        assert source2.channel_title == "Updated Title"

    async def test_get_or_create_source_youtube(self, db_session):
        """Создание YouTube источника"""
        source, created = await get_or_create_content_source(
            session=db_session,
            source_global_id="yt_channel_test",
            source_type="youtube",
            youtube_username="testchannel",
            feed_url="https://youtube.com/feeds/test"
        )

        assert created == True
        assert source.youtube_username == "testchannel"
        assert source.feed_url == "https://youtube.com/feeds/test"


# =============================================================================
# GET_USER_GROUPS ТЕСТЫ
# =============================================================================

@pytest.mark.asyncio
class TestGetUserGroups:

    async def test_get_user_groups_by_creator_id(self, db_session):
        """Получение групп по creator_id (без GroupMembership)"""
        await create_user_group_topic_chain(db_session)

        groups = await get_user_groups(12345, db_session, only_active=True)

        assert len(groups) == 1
        assert groups[0]["chat_id"] == -1001234567890
        assert groups[0]["chat_title"] == "Test Group"

    async def test_get_user_groups_only_active(self, db_session):
        """Фильтр только активных групп"""
        # Активная группа
        active_group = ManagedGroup(
            telegram_chat_id=-111111,
            telegram_chat_title="Active Group",
            chat_type="supergroup",
            bot_role_in_group="admin",
            creator_id=12345,
            is_bot_active_in_group=True
        )
        db_session.add(active_group)

        # Неактивная группа
        inactive_group = ManagedGroup(
            telegram_chat_id=-222222,
            telegram_chat_title="Inactive Group",
            chat_type="supergroup",
            bot_role_in_group="member",
            creator_id=12345,
            is_bot_active_in_group=False
        )
        db_session.add(inactive_group)
        await db_session.commit()

        groups = await get_user_groups(12345, db_session, only_active=True)

        assert len(groups) == 1
        assert groups[0]["chat_title"] == "Active Group"

    async def test_get_user_groups_with_topics(self, db_session):
        """Получение групп с загруженными темами"""
        await create_user_group_topic_chain(db_session)

        groups = await get_user_groups(12345, db_session, only_active=True, load_topics=True)

        assert len(groups) == 1
        assert len(groups[0]["topics"]) == 1
        assert groups[0]["topics"][0]["topic_name"] == "News"

    async def test_get_user_groups_empty(self, db_session):
        """Получение групп для пользователя без групп"""
        groups = await get_user_groups(99999, db_session, only_active=True)

        assert len(groups) == 0


# =============================================================================
# CREATE_TOPIC_ASSIGNMENT ТЕСТЫ
# =============================================================================

@pytest.mark.asyncio
class TestCreateTopicAssignment:

    async def test_create_topic_assignment(self, db_session):
        """Создание назначения источника в тему"""
        await create_user_group_topic_chain(db_session)
        await create_source_subscription_chain(db_session)

        assignment = await create_topic_assignment(
            topic_identifier="-1001234567890:42",
            subscription_id=1,
            session=db_session
        )

        assert assignment is not None
        assert assignment.topic_identifier == "-1001234567890:42"
        assert assignment.subscription_id == 1

    async def test_create_topic_assignment_prevents_duplicates(self, db_session):
        """Защита от дублирования назначений"""
        await create_user_group_topic_chain(db_session)
        await create_source_subscription_chain(db_session)

        # Первое назначение
        assignment1 = await create_topic_assignment(
            topic_identifier="-1001234567890:42",
            subscription_id=1,
            session=db_session
        )

        # Второе назначение (те же параметры)
        assignment2 = await create_topic_assignment(
            topic_identifier="-1001234567890:42",
            subscription_id=1,
            session=db_session
        )

        # Должен вернуться существующий объект
        assert assignment1.assignment_id == assignment2.assignment_id


# =============================================================================
# CHECK_DESTINATION_ACCESS ТЕСТЫ
# =============================================================================

@pytest.mark.asyncio
class TestCheckDestinationAccess:

    async def test_check_destination_access_owner(self, db_session):
        """Проверка доступа: владелец группы имеет доступ"""
        await create_user_group_topic_chain(db_session)

        has_access = await check_destination_access(
            account_id=12345,
            topic_identifier="-1001234567890:42",
            session=db_session
        )

        assert has_access == True

    async def test_check_destination_access_non_owner(self, db_session):
        """Проверка доступа: не владелец не имеет доступа"""
        await create_user_group_topic_chain(db_session, user_id=99999)

        has_access = await check_destination_access(
            account_id=12345,  # Не владелец
            topic_identifier="-1001234567890:42",
            session=db_session
        )

        assert has_access == False

    async def test_check_destination_access_invalid_identifier(self, db_session):
        """Проверка доступа с невалидным идентификатором"""
        has_access = await check_destination_access(
            account_id=12345,
            topic_identifier="invalid_format",
            session=db_session
        )

        assert has_access == False


# =============================================================================
# GET/UPDATE LAST_POST_ID ТЕСТЫ
# =============================================================================

@pytest.mark.asyncio
class TestSourceLastPostId:

    async def test_get_source_last_post_id_from_db(self, db_session):
        """Получение last_post_id из БД"""
        source = ContentSource(
            source_global_id="tg_channel_test",
            source_type="telegram",
            telegram_username="test",
            last_successful_post_id=12345
        )
        db_session.add(source)
        await db_session.commit()

        last_id = await get_source_last_post_id(source, db_session, use_cache=False)

        assert last_id == 12345

    async def test_update_source_last_post_id_only_increases(self, db_session):
        """Обновление last_post_id только увеличивается"""
        source = ContentSource(
            source_global_id="tg_channel_test",
            source_type="telegram",
            telegram_username="test",
            last_successful_post_id=100
        )
        db_session.add(source)
        await db_session.commit()

        # Обновление на большее значение
        await update_source_last_post_id(source, db_session, post_id=200)
        assert source.last_successful_post_id == 200

        # Попытка обновить на меньшее (должно игнорироваться)
        await update_source_last_post_id(source, db_session, post_id=50)
        assert source.last_successful_post_id == 200  # Не изменилось

    async def test_get_source_last_post_id_none(self, db_session):
        """Получение last_post_id когда он None"""
        source = ContentSource(
            source_global_id="tg_channel_new",
            source_type="telegram",
            telegram_username="new_channel",
            last_successful_post_id=None
        )
        db_session.add(source)
        await db_session.commit()

        last_id = await get_source_last_post_id(source, db_session, use_cache=False)

        assert last_id is None

# core/services/destinations/__init__.py
"""
Сервис работы с группами, темами, подписками и назначениями.

Импорт:
    from core.services.destinations import TopicUtils, get_user_groups, ...
"""

# Topic utils
from .topic_utils import TopicUtils

# Sources
from .sources import get_or_create_content_source

# Subscriptions
from .subscriptions import (
    create_user_channel_subscription,
    get_user_channel_subscriptions,
    update_user_channel_subscription,
    get_source_subscription,
    create_source_subscription,
)

# Topics
from .topics import (
    create_or_update_topic,
    get_topic_by_identifier,
    get_topic_by_chat_and_thread,
    close_topic,
    reopen_topic,
)

# Assignments
from .assignments import (
    create_topic_assignment,
    get_source_assignments_for_user,
    delete_source_assignment,
    get_active_assignments_for_source,
    get_subscribed_sources_for_destination,
)

# Access
from .access import (
    get_user_groups,
    get_user_destinations,
    get_group_destinations,
    get_group_topics,
    check_destination_access,
    get_destination_by_display_name,
)

# Cache
from .cache import (
    get_source_last_post_id,
    update_source_last_post_id,
    invalidate_source_cache_by_username,
)

__all__ = [
    # Topic utils
    "TopicUtils",
    # Sources
    "get_or_create_content_source",
    # Subscriptions
    "create_user_channel_subscription",
    "get_user_channel_subscriptions",
    "update_user_channel_subscription",
    "get_source_subscription",
    "create_source_subscription",
    # Topics
    "create_or_update_topic",
    "get_topic_by_identifier",
    "get_topic_by_chat_and_thread",
    "close_topic",
    "reopen_topic",
    # Assignments
    "create_topic_assignment",
    "get_source_assignments_for_user",
    "delete_source_assignment",
    "get_active_assignments_for_source",
    "get_subscribed_sources_for_destination",
    # Access
    "get_user_groups",
    "get_user_destinations",
    "get_group_destinations",
    "get_group_topics",
    "check_destination_access",
    "get_destination_by_display_name",
    # Cache
    "get_source_last_post_id",
    "update_source_last_post_id",
    "invalidate_source_cache_by_username",
]

# core/services/destination_service.py
"""
Обёртка для обратной совместимости.

Импорты работают как раньше:
    from core.services.destination_service import TopicUtils, get_user_groups, ...
"""
from .destinations import (
    TopicUtils,
    get_or_create_content_source,
    create_user_channel_subscription,
    get_user_channel_subscriptions,
    update_user_channel_subscription,
    get_source_subscription,
    create_source_subscription,
    create_or_update_topic,
    get_topic_by_identifier,
    get_topic_by_chat_and_thread,
    close_topic,
    reopen_topic,
    create_topic_assignment,
    get_source_assignments_for_user,
    delete_source_assignment,
    get_active_assignments_for_source,
    get_subscribed_sources_for_destination,
    get_user_groups,
    get_user_destinations,
    get_group_destinations,
    check_destination_access,
    get_destination_by_display_name,
    get_source_last_post_id,
    update_source_last_post_id,
    invalidate_source_cache_by_username,
)

__all__ = [
    "TopicUtils",
    "get_or_create_content_source",
    "create_user_channel_subscription",
    "get_user_channel_subscriptions",
    "update_user_channel_subscription",
    "get_source_subscription",
    "create_source_subscription",
    "create_or_update_topic",
    "get_topic_by_identifier",
    "get_topic_by_chat_and_thread",
    "close_topic",
    "reopen_topic",
    "create_topic_assignment",
    "get_source_assignments_for_user",
    "delete_source_assignment",
    "get_active_assignments_for_source",
    "get_subscribed_sources_for_destination",
    "get_user_groups",
    "get_user_destinations",
    "get_group_destinations",
    "check_destination_access",
    "get_destination_by_display_name",
    "get_source_last_post_id",
    "update_source_last_post_id",
    "invalidate_source_cache_by_username",
]

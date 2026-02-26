# core/models/__init__.py
"""
Модели данных для MyAggryBot.

Экспортирует все модели для обратной совместимости:
    from core.models import TelegramAccount, ManagedGroup, ContentSource, ...
"""

from .base import Base
from .users import TelegramAccount, UserPreferences
from .groups import ManagedGroup, GroupTopic
from .sources import ContentSource, SourceSubscription
from .assignments import TopicSourceAssignment
from .subscriptions import UserChannelSubscription
from .cache import CachedMedia, UserCachedMedia

__all__ = [
    "Base",
    "TelegramAccount",
    "UserPreferences",
    "ManagedGroup",
    "GroupTopic",
    "ContentSource",
    "SourceSubscription",
    "TopicSourceAssignment",
    "UserChannelSubscription",
    "CachedMedia",
    "UserCachedMedia",
]

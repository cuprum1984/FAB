# core/models/subscriptions.py
"""
Модель личных подписок пользователей: UserChannelSubscription
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, Boolean, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserChannelSubscription(Base):
    """Личные подписки пользователей на каналы"""
    __tablename__ = "user_channel_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "source_global_id", name="uq_user_channel"),
        Index('idx_user_subscription_user', 'user_id'),
        Index('idx_user_subscription_source', 'source_global_id'),
        Index('idx_user_subscription_active', 'user_id', 'is_active'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("telegram_accounts.telegram_account_id", ondelete="CASCADE"),
        nullable=False
    )

    source_global_id: Mapped[str] = mapped_column(
        String(256),
        ForeignKey("content_sources.source_global_id", ondelete="CASCADE"),
        nullable=False
    )

    custom_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    user: Mapped["TelegramAccount"] = relationship(back_populates="channel_subscriptions")
    source: Mapped["ContentSource"] = relationship()

# core/models/assignments.py
"""
Модель назначений: TopicSourceAssignment
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, Integer, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TopicSourceAssignment(Base):
    """Назначение источника в конкретную тему"""
    __tablename__ = "topic_source_assignments"
    __table_args__ = (
        UniqueConstraint("topic_identifier", "subscription_id", name="uq_topic_subscription"),
        Index('idx_assignment_timestamp', 'assignment_timestamp'),
        Index('idx_assignment_topic_subscription', 'topic_identifier', 'subscription_id'),
        Index('idx_assignment_subscription', 'subscription_id'),
    )

    assignment_id: Mapped[int] = mapped_column(primary_key=True)

    topic_identifier: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("group_topics.topic_identifier", ondelete="CASCADE"),
        nullable=False
    )

    subscription_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("source_subscriptions.subscription_id", ondelete="CASCADE"),
        nullable=False
    )

    assignment_timestamp: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )

    topic: Mapped["GroupTopic"] = relationship(back_populates="assignments")
    subscription: Mapped["SourceSubscription"] = relationship(back_populates="assignments")

    @property
    def source_global_id(self) -> Optional[str]:
        return self.subscription.source_global_id if self.subscription else None

    @property
    def source(self) -> Optional["ContentSource"]:
        return self.subscription.source if self.subscription else None

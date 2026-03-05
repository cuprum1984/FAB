# core/models/groups.py
"""
Модели групп и тем: ManagedGroup, GroupTopic
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Integer, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ManagedGroup(Base):
    """Группы/супергруппы, куда добавлен бот"""
    __tablename__ = "managed_groups"
    __table_args__ = (
        Index('idx_group_active', 'is_bot_active_in_group'),
        Index('idx_group_chat_type', 'chat_type'),
        Index('idx_group_added_timestamp', 'bot_added_timestamp'),
        Index('idx_group_restrict', 'restrict_saving_content'),
        Index('idx_group_last_seen', 'last_seen_at'),
    )

    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_chat_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chat_type: Mapped[str] = mapped_column(String(50), nullable=False)
    bot_role_in_group: Mapped[str] = mapped_column(String(50), nullable=False)
    bot_added_timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    is_bot_active_in_group: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    restrict_saving_content: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # ✅ НОВОЕ ПОЛЕ: отслеживание последней активности
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # ✅ НОВОЕ ПОЛЕ: создатель группы (ранее было в group_memberships)
    creator_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("telegram_accounts.telegram_account_id", ondelete="SET NULL"),
        nullable=True
    )

    # Связи
    topics: Mapped[List["GroupTopic"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["SourceSubscription"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan"
    )


class GroupTopic(Base):
    """Темы внутри групп"""
    __tablename__ = "group_topics"
    __table_args__ = (
        Index('idx_topic_closed', 'is_closed'),
        Index('idx_topic_thread_id', 'telegram_thread_id'),
        Index('idx_topic_chat_thread', 'telegram_chat_id', 'telegram_thread_id'),
        Index('idx_topic_created', 'created_timestamp'),
        Index('idx_topic_exists', 'is_exists_in_tg'),
        Index('idx_topic_last_seen', 'last_seen_at'),
    )

    topic_identifier: Mapped[str] = mapped_column(String(128), primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("managed_groups.telegram_chat_id", ondelete="CASCADE"),
        nullable=False
    )
    telegram_thread_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # ✅ НОВОЕ ПОЛЕ: помечать темы, удалённые в Telegram
    is_exists_in_tg: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False
    )

    # ✅ НОВОЕ ПОЛЕ: время последнего посещения темы (команда /plus)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    created_by_telegram_account_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("telegram_accounts.telegram_account_id", ondelete="SET NULL"),
        nullable=True
    )
    created_timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    group: Mapped["ManagedGroup"] = relationship(back_populates="topics")
    created_by: Mapped["TelegramAccount"] = relationship(back_populates="created_topics")
    assignments: Mapped[List["TopicSourceAssignment"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan"
    )

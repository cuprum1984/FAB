# core/models/sources.py
"""
Модели источников и подписок: ContentSource, SourceSubscription
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, ForeignKey, String, Integer, UniqueConstraint, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ContentSource(Base):
    """Источники контента (каналы, RSS, YouTube и т.д.)"""
    __tablename__ = "content_sources"
    __table_args__ = (
        Index('idx_source_type', 'source_type'),
        Index('idx_source_username', 'telegram_username'),
        Index('idx_source_last_post', 'last_successful_post_id'),
        Index('idx_source_last_checked', 'last_checked_timestamp'),
        Index('idx_youtube_username', 'youtube_username'),
    )

    source_global_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Для Telegram
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)

    # ✅ ВОЗВРАЩАЕМ: название канала для отображения
    channel_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Для YouTube/RSS
    feed_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # username для YouTube
    youtube_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    # ===== ПОЛЯ ДЛЯ ПАРСИНГА =====
    last_successful_post_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_video_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_successful_post_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_checked_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    parsing_interval: Mapped[int] = mapped_column(Integer, server_default="300", nullable=False)

    subscriptions: Mapped[List["SourceSubscription"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        """Возвращает название для отображения."""
        if self.channel_title:
            return self.channel_title
        elif self.source_type == "telegram" and self.telegram_username:
            return f"@{self.telegram_username}"
        elif self.source_type == "youtube" and self.youtube_username:
            return self.youtube_username
        else:
            return self.source_global_id

    @property
    def parsing_url(self) -> Optional[str]:
        """URL для парсинга (не хранится в БД)"""
        if self.source_type == "telegram" and self.telegram_username:
            return f"https://t.me/s/{self.telegram_username}"
        return self.feed_url

    @property
    def public_url(self) -> Optional[str]:
        """Публичная ссылка (не хранится в БД)"""
        if self.source_type == "telegram" and self.telegram_username:
            return f"https://t.me/{self.telegram_username}"
        if self.source_type == "youtube" and self.youtube_username:
            return f"https://youtube.com/@{self.youtube_username}"
        return self.feed_url

    @property
    def effective_last_id(self) -> Optional[str]:
        """Получить эффективный ID последнего поста."""
        if self.source_type == "youtube":
            return self.last_video_id
        return str(self.last_successful_post_id) if self.last_successful_post_id else None

    @property
    def check_interval(self) -> int:
        """Интервал проверки в зависимости от типа источника"""
        if self.source_type == "youtube":
            return 1800  # 30 минут для YouTube
        return 300  # 5 минут для Telegram


class SourceSubscription(Base):
    """Подписка группы на источник"""
    __tablename__ = "source_subscriptions"
    __table_args__ = (
        UniqueConstraint("telegram_chat_id", "source_global_id", name="uq_chat_source"),
        Index('idx_subscription_timestamp', 'subscription_timestamp'),
        Index('idx_subscription_added_by', 'added_by_telegram_account_id'),
        Index('idx_subscription_chat_source', 'telegram_chat_id', 'source_global_id'),
    )

    subscription_id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("managed_groups.telegram_chat_id", ondelete="CASCADE"),
        nullable=False
    )

    source_global_id: Mapped[Optional[str]] = mapped_column(
        String(256),
        ForeignKey("content_sources.source_global_id", ondelete="SET NULL"),
        nullable=True
    )

    subscription_timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    added_by_telegram_account_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("telegram_accounts.telegram_account_id", ondelete="SET NULL"),
        nullable=True
    )

    added_by: Mapped["TelegramAccount"] = relationship(back_populates="added_subscriptions")
    group: Mapped["ManagedGroup"] = relationship(back_populates="subscriptions")
    source: Mapped["ContentSource"] = relationship(back_populates="subscriptions")
    assignments: Mapped[List["TopicSourceAssignment"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan"
    )

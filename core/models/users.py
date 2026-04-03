# core/models/users.py
"""
Модели пользователей: TelegramAccount, UserPreferences
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Integer, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TelegramAccount(Base):
    """Аккаунты пользователей Telegram"""
    __tablename__ = "telegram_accounts"
    __table_args__ = (
        Index('idx_account_last_activity', 'last_activity'),
        Index('idx_account_username', 'telegram_username'),
        Index('idx_account_language', 'language_code'),
    )

    telegram_account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    telegram_first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    telegram_last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_bot_blocked: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    registration_timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    last_activity: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # ✅ GDPR: Согласие на обработку данных
    consent_given_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)

    # Связи
    created_topics: Mapped[List["GroupTopic"]] = relationship(
        back_populates="created_by",
        cascade="save-update, merge"
    )

    added_subscriptions: Mapped[List["SourceSubscription"]] = relationship(
        back_populates="added_by",
        cascade="save-update, merge"
    )

    channel_subscriptions: Mapped[List["UserChannelSubscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class UserPreferences(Base):
    """Настройки пользователя (язык, иконки)"""
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("telegram_accounts.telegram_account_id", ondelete="CASCADE"),
        primary_key=True
    )

    language: Mapped[str] = mapped_column(String(10), server_default="en", nullable=False)
    icons_style: Mapped[str] = mapped_column(String(20), server_default="auto", nullable=False)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

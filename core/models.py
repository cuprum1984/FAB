# core/models.py
"""
Модели данных для MyAggryBot.
Версия: 4.1 (22 февраля 2026)
Изменения:
- Добавлено поле last_seen_at в ManagedGroup
- Добавлено поле is_exists_in_tg в GroupTopic
- Удалена таблица group_memberships
- Удалены поля last_video_timestamp, channel_language, title, description из ContentSource
- Добавлены новые индексы
- ✅ Добавлено поле channel_title в ContentSource для отображения названий каналов

Примечание по datetime (февраль 2026):
- Все поля datetime используют `func.now()` для server_default/onupdate (SQL уровень) ✅
- В сервисах используется `datetime.now(timezone.utc).replace(tzinfo=None)` для записи в БД
- Причина: PostgreSQL TIMESTAMP WITHOUT TIME ZONE требует naive datetime
- См. core/services/* для примеров корректного использования
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    BigInteger, Boolean, ForeignKey, String, Integer, Text, UniqueConstraint,
    func, Index, DateTime
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ========== ОСНОВНОЙ БОТ ==========

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


# ❌ ТАБЛИЦА group_memberships ПОЛНОСТЬЮ УДАЛЕНА


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
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # telegram / rss / youtube
    
    # Для Telegram
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    
    # ✅ ВОЗВРАЩАЕМ: название канала для отображения (было удалено, но нужно для красивого вывода)
    channel_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Для YouTube/RSS
    feed_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # username для YouTube
    youtube_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    
    # ===== ПОЛЯ ДЛЯ ПАРСИНГА =====
    
    # Для Telegram: числовой ID поста
    # Для RSS: числовой хеш от guid/ссылки
    # Для YouTube: числовой хеш от video_id
    last_successful_post_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Для YouTube (строковый video_id)
    last_video_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Общие поля
    last_successful_post_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_checked_timestamp: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    parsing_interval: Mapped[int] = mapped_column(Integer, server_default="300", nullable=False)
    
    subscriptions: Mapped[List["SourceSubscription"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan"
    )
    
    @property
    def display_name(self) -> str:
        """
        Возвращает название для отображения.
        Приоритет:
        1. channel_title (если есть)
        2. для Telegram: @username
        3. для YouTube: youtube_username
        4. source_global_id
        """
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
        """
        Получить эффективный ID последнего поста в зависимости от типа.
        Для YouTube возвращает last_video_id, для остальных - str(last_successful_post_id)
        """
        if self.source_type == "youtube":
            return self.last_video_id
        return str(self.last_successful_post_id) if self.last_successful_post_id else None
    
    @property
    def check_interval(self) -> int:
        """Интервал проверки в зависимости от типа источника"""
        if self.source_type == "youtube":
            return 1800  # 30 минут для YouTube
        return 300  # 5 минут для Telegram


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


# ========== ДЛЯ ОСНОВНОГО БОТА (КЕШ MEDIA) ==========

class CachedMedia(Base):
    """Кеш file_id от основного бота"""
    __tablename__ = "cached_media"
    __table_args__ = (
        UniqueConstraint("source_global_id", "post_id", name="uq_source_post"),
        Index('idx_cached_media_source', 'source_global_id'),
        Index('idx_cached_media_file_id', 'file_id'),
        Index('idx_cached_media_expires', 'expires_at'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    
    source_global_id: Mapped[str] = mapped_column(
        String(256),
        ForeignKey("content_sources.source_global_id", ondelete="CASCADE"),
        nullable=False
    )
    post_id: Mapped[str] = mapped_column(String(100), nullable=False)
    file_id: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    last_used: Mapped[Optional[datetime]] = mapped_column(nullable=True)


# ========== ДЛЯ БОТА-ПОМОЩНИКА (КЕШ ВАСИ) ==========

class UserCachedMedia(Base):
    """Личный кеш Васи (бот-помощник)"""
    __tablename__ = "user_cached_media"
    __table_args__ = (
        UniqueConstraint("user_id", "chat_id", "message_id", name="uq_user_chat_message"),
        Index('idx_user_media_user', 'user_id'),
        Index('idx_user_media_file_id', 'file_id'),
        Index('idx_user_media_expires', 'expires_at'),
        Index('idx_user_media_accessed', 'last_accessed'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("telegram_accounts.telegram_account_id", ondelete="CASCADE"),
        nullable=False
    )
    
    chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("managed_groups.telegram_chat_id", ondelete="SET NULL"),
        nullable=True
    )
    
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    file_id: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    post_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


# ========== НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ ==========

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
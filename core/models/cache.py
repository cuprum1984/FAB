# core/models/cache.py
"""
Модели кеша: CachedMedia
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, Integer, Text, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


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

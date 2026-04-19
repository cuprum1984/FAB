# bot/services
"""Пакет сервисов бота: бизнес-логика, внешние интеграции, утилиты."""

from .legal_terms import preload_legal_docs, get_legal_text, get_legal_text_for_user

__all__ = [
    "preload_legal_docs",
    "get_legal_text",
    "get_legal_text_for_user",
]

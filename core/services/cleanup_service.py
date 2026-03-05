# core/services/cleanup_service.py
"""
Обёртка для обратной совместимости.

Импорты работают как раньше:
    from core.services.cleanup_service import CleanupService
"""
from .cleanup import CleanupService

__all__ = ["CleanupService"]

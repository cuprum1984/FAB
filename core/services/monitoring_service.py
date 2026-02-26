# core/services/monitoring_service.py
"""
Обёртка для обратной совместимости.

Импорты работают как раньше:
    from core.services.monitoring_service import MonitoringService
    from core.services.monitoring_service import start_monitoring, stop_monitoring
"""
import asyncio
import logging

from .monitoring import MonitoringService

# Глобальные функции
from core.services.monitoring.base import MonitoringService as _MonitoringService

logger = logging.getLogger(__name__)

_monitoring_service = None


async def start_monitoring(bot, interval_minutes: int = 5):
    """Запустить мониторинг."""
    global _monitoring_service
    if _monitoring_service:
        logger.warning("⚠️ Мониторинг уже запущен")
        return

    _monitoring_service = _MonitoringService(bot)
    asyncio.create_task(_monitoring_service.start(interval_minutes))
    logger.info(f"🎯 Задача мониторинга создана (интервал: {interval_minutes} минут)")


async def stop_monitoring():
    """Остановить мониторинг."""
    global _monitoring_service
    if _monitoring_service:
        await _monitoring_service.stop()
        _monitoring_service = None
    else:
        logger.warning("⚠️ Мониторинг не был запущен")


__all__ = ["MonitoringService", "start_monitoring", "stop_monitoring"]

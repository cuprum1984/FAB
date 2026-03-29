# core/services/monitoring/youtube_monitor.py
"""
Проверка YouTube каналов - делегирование YouTubeSimpleMonitoringService.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource
from core.services.youtube_simple_service import YouTubeSimpleMonitoringService

logger = logging.getLogger(__name__)


class YouTubeMonitor:
    """Мониторинг YouTube каналов."""

    def __init__(self, bot, monitoring_service):
        self.bot = bot
        self.monitoring = monitoring_service
        self.youtube_service = YouTubeSimpleMonitoringService(bot)

    async def check_youtube_source(self, source: ContentSource, session: AsyncSession, downtime_seconds: float = 0):
        """
        Проверить YouTube канал и отправить новые видео.
        Делегирует YouTubeSimpleMonitoringService.
        downtime_seconds: время простоя в секундах (0 если простоя нет)
        """
        try:
            await self.youtube_service.check_source(source, session, downtime_seconds)
        except Exception as e:
            logger.error(f"❌ Ошибка проверки YouTube источника {source.source_global_id}: {e}")
            await self.monitoring._update_source_error_stats(source.source_global_id)
            # Не пробрасываем ошибку — это делается в check_all_sources

# core/services/cleanup/base.py
"""
Базовый класс для сервиса очистки данных.
Версия: 1.0 (26 февраля 2026)
"""
import logging
import sys
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session

logger = logging.getLogger(__name__)


def console_print(*args, **kwargs):
    """Принудительный вывод в консоль, минуя логирование"""
    print(*args, **kwargs)
    sys.stdout.flush()


class CleanupService:
    """Сервис для ежедневной очистки устаревших данных."""

    async def run_cleanup(self):
        """Точка входа - запуск всех процедур очистки."""
        msg = "🧹 Запуск ежедневной очистки данных..."
        logger.info(msg)
        console_print(msg)

        try:
            async with async_session() as session:
                await self._cleanup_gdpr(session)
                await self._cleanup_dead_groups(session)
                await self._cleanup_orphan_sources(session)
                await self._cleanup_expired_media(session)
                await self._cleanup_orphan_topics(session)
                await self._cleanup_old_topics(session)

                await session.commit()

            msg = "✅ Ежедневная очистка успешно завершена"
            logger.info(msg)
            console_print(msg)

        except Exception as e:
            error_msg = f"❌ Критическая ошибка при очистке данных: {e}"
            logger.error(error_msg, exc_info=True)
            console_print(error_msg)
            raise

    # ========== Обёртки для тестов (обратная совместимость) ==========

    async def _cleanup_gdpr(self, session: AsyncSession):
        """GDPR очистка пользователей."""
        from .user_cleanup import cleanup_gdpr
        await cleanup_gdpr(session)

    async def _cleanup_dead_groups(self, session: AsyncSession):
        """Очистка неактивных групп."""
        from .user_cleanup import cleanup_dead_groups
        await cleanup_dead_groups(session)

    async def _cleanup_orphan_sources(self, session: AsyncSession):
        """Очистка источников без подписок."""
        from .subscription_cleanup import cleanup_orphan_sources
        await cleanup_orphan_sources(session)

    async def _cleanup_expired_media(self, session: AsyncSession):
        """Очистка устаревшего кеша."""
        from .media_cleanup import cleanup_expired_media
        await cleanup_expired_media(session)

    async def _cleanup_orphan_topics(self, session: AsyncSession):
        """Очистка удалённых тем."""
        from .topic_cleanup import cleanup_orphan_topics
        await cleanup_orphan_topics(session)

    async def _cleanup_old_topics(self, session: AsyncSession):
        """Очистка старых тем."""
        from .topic_cleanup import cleanup_old_topics
        await cleanup_old_topics(session)

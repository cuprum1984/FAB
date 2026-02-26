# core/services/monitoring/base.py
"""
Базовый класс MonitoringService - основной цикл мониторинга.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.services.monitoring.telegram_monitor import TelegramMonitor
from core.services.monitoring.youtube_monitor import YouTubeMonitor
from core.services.monitoring.group_checker import GroupChecker

logger = logging.getLogger(__name__)


class MonitoringService:
    """Сервис мониторинга и отправки постов."""

    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.source_stats = {}
        self._processed_posts = set()
        
        # Инициализация подсервисов
        self.telegram_monitor = TelegramMonitor(bot, self)
        self.youtube_monitor = YouTubeMonitor(bot, self)
        self.group_checker = GroupChecker(bot, self)

    # ----------------------------------------------------------------------
    # 🔥 ОСНОВНОЙ ЦИКЛ
    # ----------------------------------------------------------------------

    async def start(self, interval_minutes: int = 5):
        """Запуск основного цикла мониторинга."""
        if self.is_running:
            logger.warning("⚠️ Мониторинг уже запущен")
            return

        self.is_running = True
        logger.info(f"🚀 Мониторинг запущен (базовый интервал: {interval_minutes} минут)")

        # Запускаем проверку групп в отдельной задаче
        asyncio.create_task(self.group_checker.schedule_groups_check())
        logger.info("📅 Запущена задача проверки групп (2 раза в день)")

        while self.is_running:
            try:
                async with async_session() as session:
                    await self.check_all_sources(session)
                    await session.commit()
            except Exception as e:
                logger.error(f"❌ Ошибка в мониторинге: {e}", exc_info=True)
                await asyncio.sleep(60)

            await self._smart_sleep(interval_minutes)

    async def _smart_sleep(self, base_interval_minutes: int):
        """Умное ожидание с учётом часов пик"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        hour = now.hour
        is_peak_hour = 13 <= hour <= 17

        interval = base_interval_minutes * 1 if is_peak_hour else base_interval_minutes
        logger.info(f"⏳ Следующая проверка через {interval} минут...")

        for _ in range(interval * 60):
            if not self.is_running:
                break
            await asyncio.sleep(1)

    async def stop(self):
        """Остановка мониторинга."""
        self.is_running = False
        logger.info("⏹️ Мониторинг остановлен")

    # ----------------------------------------------------------------------
    # 🔥 ПРОВЕРКА ВСЕХ ИСТОЧНИКОВ
    # ----------------------------------------------------------------------

    async def check_all_sources(self, session: AsyncSession):
        """Проверить все источники."""
        logger.info("🔍 Проверяю источники...")

        try:
            stmt = select(ContentSource)
            result = await session.execute(stmt)
            sources = result.scalars().all()

            logger.info(f"📊 Найдено источников: {len(sources)}")

            for source in sources:
                try:
                    if not await self._check_source_security(source, session):
                        logger.warning(f"⏭️ Пропускаю небезопасный источник {source.source_global_id}")
                        continue

                    if not await self._should_check_source(source):
                        continue

                    if source.source_type == 'telegram':
                        await self.telegram_monitor.check_telegram_source(source, session)
                    elif source.source_type == 'youtube':
                        await self.youtube_monitor.check_youtube_source(source, session)
                    else:
                        logger.warning(f"⚠️ Неизвестный тип источника: {source.source_type}")

                except Exception as e:
                    logger.error(f"❌ Ошибка проверки источника {source.source_global_id}: {e}")
                    await self._update_source_error_stats(source.source_global_id)
                    await session.rollback()

            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Критическая ошибка в check_all_sources: {e}")
            raise

    async def _should_check_source(self, source) -> bool:
        """
        Проверяет, пора ли проверять источник.
        Для YouTube интервал 30 минут, для Telegram 5 минут.
        """
        stats = self.source_stats.get(source.source_global_id, {})
        consecutive_errors = stats.get('consecutive_errors', 0)
        last_check = stats.get('last_check')

        if hasattr(source, 'is_active') and not source.is_active:
            logger.debug(f"⏸️ Источник {source.source_global_id} деактивирован")
            return False

        if consecutive_errors >= 3:
            if last_check and (datetime.now(timezone.utc).replace(tzinfo=None) - last_check).total_seconds() < 3600:
                logger.debug(f"⏸️ Пропускаю {source.source_global_id} (3+ ошибок подряд)")
                return False

        # Определяем интервал в зависимости от типа источника
        if source.source_type == 'youtube':
            interval = 1800  # 30 минут для YouTube
        else:
            interval = 300   # 5 минут для Telegram

        if source.last_checked_timestamp:
            seconds_since = (datetime.now(timezone.utc).replace(tzinfo=None) - source.last_checked_timestamp).total_seconds()
            if seconds_since < interval:
                logger.debug(f"⏸️ {source.source_global_id}: ещё рано (прошло {seconds_since:.0f}с, нужно {interval}с)")
                return False

        return True

    async def _update_source_error_stats(self, source_global_id: str):
        """Обновить статистику ошибок источника."""
        stats = self.source_stats.get(source_global_id, {})
        stats['consecutive_errors'] = stats.get('consecutive_errors', 0) + 1
        stats['last_check'] = datetime.now(timezone.utc).replace(tzinfo=None)
        self.source_stats[source_global_id] = stats

    async def _reset_source_error_stats(self, source_global_id: str):
        """Сбросить статистику ошибок источника."""
        if source_global_id in self.source_stats:
            self.source_stats[source_global_id]['consecutive_errors'] = 0

    async def _check_source_security(self, source, session: AsyncSession) -> bool:
        """
        Проверяет безопасность источника.
        Возвращает False, если источник небезопасен и должен быть пропущен.
        """
        from core.security import URLSecurity

        logger.debug(f"🔒 Проверка безопасности для {source.source_global_id}")

        try:
            if source.source_type == "youtube":
                # Для YouTube проверяем username и feed_url
                if source.feed_url and not URLSecurity.is_allowed_youtube(source.feed_url):
                    logger.error(f"❌ YouTube источник {source.source_global_id} имеет небезопасный URL: {source.feed_url}")
                    source.is_active = False
                    await session.flush()
                    return False

                # Проверяем username на опасные символы
                if source.youtube_username:
                    dangerous_patterns = ['../', '..\\', '%2e', '%2f', ';', '|', '`', '$', '(', ')']
                    for pattern in dangerous_patterns:
                        if pattern in source.youtube_username.lower():
                            logger.error(f"❌ YouTube источник {source.source_global_id} имеет опасный username: {source.youtube_username}")
                            source.is_active = False
                            await session.flush()
                            return False

            elif source.source_type == "telegram":
                if source.telegram_username:
                    dangerous_patterns = ['../', '..\\', '%2e', '%2f', ';', '|', '`', '$', '(', ')']
                    for pattern in dangerous_patterns:
                        if pattern in source.telegram_username.lower():
                            logger.error(f"❌ Telegram источник {source.source_global_id} имеет опасный username: {source.telegram_username}")
                            source.is_active = False
                            await session.flush()
                            return False

                    if len(source.telegram_username) < 3 or len(source.telegram_username) > 32:
                        logger.error(f"❌ Telegram источник {source.source_global_id} имеет некорректную длину username")
                        source.is_active = False
                        await session.flush()
                        return False

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при проверке безопасности {source.source_global_id}: {e}")
            return False

    async def _get_source_assignments(self, source_global_id: str, session: AsyncSession):
        """Получить все активные назначения для источника."""
        from core.models import (
            TopicSourceAssignment,
            SourceSubscription,
            GroupTopic,
            ManagedGroup
        )
        from sqlalchemy.orm import selectinload
        from sqlalchemy import and_
        
        stmt = (
            select(TopicSourceAssignment)
            .join(
                SourceSubscription,
                SourceSubscription.subscription_id == TopicSourceAssignment.subscription_id
            )
            .join(
                GroupTopic,
                GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier
            )
            .join(
                ManagedGroup,
                ManagedGroup.telegram_chat_id == GroupTopic.telegram_chat_id
            )
            .where(
                and_(
                    SourceSubscription.source_global_id == source_global_id,
                    GroupTopic.is_closed == False,
                    ManagedGroup.is_bot_active_in_group == True
                )
            )
            .options(
                selectinload(TopicSourceAssignment.topic),
                selectinload(TopicSourceAssignment.subscription)
            )
        )

        result = await session.execute(stmt)
        return result.scalars().all()


# Импорты в конце для избежания циклических зависимостей
from core.models import ContentSource

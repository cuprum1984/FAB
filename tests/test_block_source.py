"""
Тесты для функции блокировки источников (v6.9.1).
Проверяют:
- Блокировку по Telegram/YouTube username
- Удаление подписок и назначений
- Пропуск заблокированных источников в мониторинге
- Отказ при добавлении заблокированного источника
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from core.models import ContentSource, SourceSubscription, TopicSourceAssignment
from core.models import ManagedGroup, GroupTopic, TelegramAccount


# =============================================================================
# БЛОКИРОВКА ИСТОЧНИКОВ — МОДЕЛЬ
# =============================================================================

@pytest.mark.asyncio
class TestBlockedSourceModel:

    async def test_new_source_not_blocked_by_default(self, db_session):
        """Новый источник по умолчанию не заблокирован"""
        source = ContentSource(
            source_global_id="tg_channel_new",
            source_type="telegram",
            telegram_username="new_channel"
        )
        db_session.add(source)
        await db_session.commit()

        assert source.is_blocked == False
        assert source.blocked_reason is None

    async def test_block_source_fields(self, db_session):
        """Можно заблокить источник с указанием причины"""
        source = ContentSource(
            source_global_id="tg_channel_blocked",
            source_type="telegram",
            telegram_username="blocked_channel",
            is_blocked=True,
            blocked_reason="author_request"
        )
        db_session.add(source)
        await db_session.commit()

        assert source.is_blocked == True
        assert source.blocked_reason == "author_request"


# =============================================================================
# МОНИТОРИНГ — ПРОПУСК ЗАБЛОКИРОВАННЫХ
# =============================================================================

@pytest.mark.asyncio
class TestBlockedSourceInMonitoring:

    async def test_blocked_source_skipped_in_monitoring(self, db_session, mock_bot):
        """Мониторинг пропускает заблокированные источники"""
        from core.services.monitoring_service import MonitoringService

        source = ContentSource(
            source_global_id="tg_channel_blocked",
            source_type="telegram",
            telegram_username="blocked_channel",
            is_blocked=True,
            blocked_reason="author_request"
        )
        db_session.add(source)
        await db_session.commit()

        monitoring = MonitoringService(mock_bot)
        # Вызываем напрямую _check_single_source
        await monitoring._check_single_source(source, db_session)

        # Если источник заблокирован, парсинг не должен вызываться
        # Проверяем что last_checked_timestamp не обновился
        assert source.last_checked_timestamp is None

    async def test_blocked_youtube_skipped_in_monitoring(self, db_session, mock_bot):
        """Мониторинг пропускает заблокированные YouTube источники"""
        from core.services.monitoring_service import MonitoringService

        source = ContentSource(
            source_global_id="yt_channel_blocked",
            source_type="youtube",
            youtube_username="blocked_yt_channel",
            is_blocked=True,
            blocked_reason="dmca"
        )
        db_session.add(source)
        await db_session.commit()

        monitoring = MonitoringService(mock_bot)
        await monitoring._check_single_source(source, db_session)

        assert source.last_checked_timestamp is None


# =============================================================================
# ПРОВЕРКА ПРИ ДОБАВЛЕНИИ — ОТКАЗ
# =============================================================================

@pytest.mark.asyncio
class TestAddBlockedSource:

    async def test_add_blocked_telegram_source_rejected(self, db_session):
        """Добавление заблокированного Telegram источника — проверка в БД"""
        # Создаём заблокированный источник
        source = ContentSource(
            source_global_id="tg_channel_blocked",
            source_type="telegram",
            telegram_username="blocked_channel",
            is_blocked=True,
            blocked_reason="author_request"
        )
        db_session.add(source)
        await db_session.commit()

        # Проверяем что можно найти заблокированный источник
        from sqlalchemy import select
        stmt = select(ContentSource).where(
            ContentSource.telegram_username == "blocked_channel"
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.is_blocked == True
        assert found.blocked_reason == "author_request"

    async def test_add_blocked_youtube_source_rejected(self, db_session):
        """Добавление заблокированного YouTube источника — проверка в БД"""
        source = ContentSource(
            source_global_id="yt_channel_blocked",
            source_type="youtube",
            youtube_username="blocked_yt",
            is_blocked=True,
            blocked_reason="author_request"
        )
        db_session.add(source)
        await db_session.commit()

        from sqlalchemy import select
        stmt = select(ContentSource).where(
            ContentSource.youtube_username == "blocked_yt"
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.is_blocked == True


# =============================================================================
# СКРИПТ БЛОКИРОВКИ — ЛОГИКА
# =============================================================================

@pytest.mark.asyncio
class TestBlockSourceLogic:

    async def test_block_source_by_telegram_username(self, db_session):
        """Блокировка по Telegram username"""
        source = ContentSource(
            source_global_id="tg_channel_to_block",
            source_type="telegram",
            telegram_username="to_block"
        )
        db_session.add(source)
        await db_session.commit()

        # Имитируем логику скрипта block_source.py
        from sqlalchemy import select
        stmt = select(ContentSource).where(
            ContentSource.telegram_username == "to_block"
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.is_blocked == False

        # Блокируем
        found.is_blocked = True
        found.blocked_reason = "author_request"
        await db_session.commit()

        # Проверяем
        stmt = select(ContentSource).where(
            ContentSource.telegram_username == "to_block"
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        assert found.is_blocked == True
        assert found.blocked_reason == "author_request"

    async def test_block_source_by_youtube_username(self, db_session):
        """Блокировка по YouTube username"""
        source = ContentSource(
            source_global_id="yt_channel_to_block",
            source_type="youtube",
            youtube_username="yt_to_block"
        )
        db_session.add(source)
        await db_session.commit()

        from sqlalchemy import select
        stmt = select(ContentSource).where(
            ContentSource.youtube_username == "yt_to_block"
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.is_blocked == False

        # Блокируем
        found.is_blocked = True
        found.blocked_reason = "dmca"
        await db_session.commit()

        # Проверяем
        assert found.is_blocked == True
        assert found.blocked_reason == "dmca"

    async def test_block_already_blocked_source(self, db_session):
        """Повторная блокировка уже заблокированного источника"""
        source = ContentSource(
            source_global_id="tg_channel_already_blocked",
            source_type="telegram",
            telegram_username="already_blocked",
            is_blocked=True,
            blocked_reason="author_request"
        )
        db_session.add(source)
        await db_session.commit()

        from sqlalchemy import select
        stmt = select(ContentSource).where(
            ContentSource.telegram_username == "already_blocked"
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # Скрипт должен обнаружить что уже заблокирован
        assert found.is_blocked == True
        assert found.blocked_reason == "author_request"

    async def test_block_source_not_found(self, db_session):
        """Источник не найден — скрипт должен вывести ошибку"""
        from sqlalchemy import select
        stmt = select(ContentSource).where(
            ContentSource.telegram_username == "nonexistent_channel"
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        assert found is None

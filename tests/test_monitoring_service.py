"""
Тесты для MonitoringService.
Проверяют логику мониторинга источников и отправки постов.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from core.models import ContentSource, ManagedGroup
from core.services.monitoring_service import MonitoringService
from core.services.monitoring.post_sender import PostSender


# =============================================================================
# _SHOULD_CHECK_SOURCE ТЕСТЫ (интервалы проверки)
# =============================================================================

@pytest.mark.asyncio
class TestShouldCheckSource:

    async def test_should_check_source_telegram_interval(self, db_session, mock_bot):
        """Telegram проверяется каждые 5 минут"""
        monitoring = MonitoringService(mock_bot)
        
        source = ContentSource(
            source_global_id="tg_channel_test",
            source_type="telegram",
            telegram_username="test",
            last_checked_timestamp=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
        )
        db_session.add(source)
        await db_session.commit()

        should_check = await monitoring._should_check_source(source)

        assert should_check == True  # Прошло 10 минут > 5 минут

    async def test_should_check_source_youtube_interval(self, db_session, mock_bot):
        """YouTube проверяется каждые 30 минут"""
        monitoring = MonitoringService(mock_bot)
        
        source = ContentSource(
            source_global_id="yt_channel_test",
            source_type="youtube",
            youtube_username="test",
            last_checked_timestamp=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
        )
        db_session.add(source)
        await db_session.commit()

        should_check = await monitoring._should_check_source(source)

        assert should_check == False  # Прошло 20 минут < 30 минут

    async def test_should_check_source_recently_checked(self, db_session, mock_bot):
        """Источник недавно проверен — не нужно проверять"""
        monitoring = MonitoringService(mock_bot)
        
        source = ContentSource(
            source_global_id="tg_channel_recent",
            source_type="telegram",
            telegram_username="recent",
            last_checked_timestamp=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2)
        )
        db_session.add(source)
        await db_session.commit()

        should_check = await monitoring._should_check_source(source)

        assert should_check == False  # Прошло 2 минуты < 5 минут

    async def test_should_check_source_skip_on_errors(self, db_session, mock_bot):
        """Пропуск источника после 3+ ошибок подряд"""
        monitoring = MonitoringService(mock_bot)
        
        source = ContentSource(
            source_global_id="tg_channel_error",
            source_type="telegram",
            telegram_username="error_channel"
        )
        db_session.add(source)
        await db_session.commit()

        # Симуляция 3 ошибок
        monitoring.source_stats["tg_channel_error"] = {
            "consecutive_errors": 3,
            "last_check": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30)
        }

        should_check = await monitoring._should_check_source(source)

        assert should_check == False  # Пропускаем из-за ошибок


# =============================================================================
# _CHECK_SOURCE_SECURITY ТЕСТЫ (блокировка опасных URL)
# =============================================================================

@pytest.mark.asyncio
class TestCheckSourceSecurity:

    async def test_check_source_security_blocks_dangerous_url(self, db_session, mock_bot):
        """Блокировка источника с опасным username"""
        monitoring = MonitoringService(mock_bot)
        
        source = ContentSource(
            source_global_id="tg_channel_bad",
            source_type="telegram",
            telegram_username="../etc/passwd"  # Опасный паттерн
        )
        db_session.add(source)
        await db_session.commit()

        is_safe = await monitoring._check_source_security(source, db_session)

        assert is_safe == False

    async def test_check_source_security_allows_safe_url(self, db_session, mock_bot):
        """Разрешение безопасного источника"""
        monitoring = MonitoringService(mock_bot)
        
        source = ContentSource(
            source_global_id="tg_channel_good",
            source_type="telegram",
            telegram_username="durov"  # Безопасный username
        )
        db_session.add(source)
        await db_session.commit()

        is_safe = await monitoring._check_source_security(source, db_session)

        assert is_safe == True

    async def test_check_source_security_blocks_short_username(self, db_session, mock_bot):
        """Блокировка слишком короткого username"""
        monitoring = MonitoringService(mock_bot)
        
        source = ContentSource(
            source_global_id="tg_channel_short",
            source_type="telegram",
            telegram_username="ab"  # Слишком короткий (< 3)
        )
        db_session.add(source)
        await db_session.commit()

        is_safe = await monitoring._check_source_security(source, db_session)

        assert is_safe == False


# =============================================================================
# UPDATE_SOURCE_ERROR_STATS ТЕСТЫ
# =============================================================================

@pytest.mark.asyncio
class TestSourceErrorStats:

    async def test_update_source_error_stats_increments(self, mock_bot):
        """Обновление статистики ошибок увеличивает счётчик"""
        monitoring = MonitoringService(mock_bot)

        await monitoring._update_source_error_stats("tg_channel_test")

        assert monitoring.source_stats["tg_channel_test"]["consecutive_errors"] == 1

        await monitoring._update_source_error_stats("tg_channel_test")

        assert monitoring.source_stats["tg_channel_test"]["consecutive_errors"] == 2

    async def test_reset_source_error_stats(self, mock_bot):
        """Сброс статистики ошибок"""
        monitoring = MonitoringService(mock_bot)

        # Установим ошибки
        monitoring.source_stats["tg_channel_test"] = {
            "consecutive_errors": 5,
            "last_check": datetime.now(timezone.utc).replace(tzinfo=None)
        }

        await monitoring._reset_source_error_stats("tg_channel_test")

        assert monitoring.source_stats["tg_channel_test"]["consecutive_errors"] == 0

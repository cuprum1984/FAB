"""
Тесты для YouTube Simple Service (моки)
Тестируют логику сервиса без реальных запросов к YouTube
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from core.services.youtube_simple_service import YouTubeSimpleMonitoringService
from core.models import ContentSource, TopicSourceAssignment, SourceSubscription, GroupTopic, ManagedGroup


@pytest.fixture
def mock_bot():
    """Фикстура мок-бота"""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.get_me = AsyncMock()
    return bot


@pytest.fixture
def mock_session():
    """Фикстура мок-сессии БД"""
    session = AsyncMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_source():
    """Фикстура ContentSource"""
    source = MagicMock(spec=ContentSource)
    source.source_type = 'youtube'
    source.youtube_username = 'test_channel'
    source.source_global_id = 'yt_test_channel'
    source.last_video_id = 'old_video_123'
    source.last_successful_post_id = 123456789012345
    source.last_checked_timestamp = datetime.utcnow()
    return source


@pytest.fixture
def mock_assignment():
    """Фикстура TopicSourceAssignment"""
    topic = MagicMock(spec=GroupTopic)
    topic.topic_name = 'Test Topic'
    topic.topic_identifier = 'topic_123'
    topic.telegram_chat_id = -1001234567890
    topic.telegram_thread_id = 42
    topic.is_closed = False

    subscription = MagicMock(spec=SourceSubscription)
    subscription.subscription_id = 'sub_123'
    subscription.source_global_id = 'yt_test_channel'

    assignment = MagicMock(spec=TopicSourceAssignment)
    assignment.assignment_id = 'assign_123'
    assignment.topic_identifier = 'topic_123'
    assignment.subscription_id = 'sub_123'
    assignment.topic = topic
    assignment.subscription = subscription

    return assignment


@pytest.mark.asyncio
async def test_check_source_not_youtube_type(mock_bot, mock_session):
    """Тест: источник не YouTube — пропускаем"""
    with patch('core.services.youtube_simple_service.get_parser') as mock_get_parser:
        mock_parser = AsyncMock()
        mock_get_parser.return_value = mock_parser
        
        service = YouTubeSimpleMonitoringService(mock_bot)

        source = MagicMock(spec=ContentSource)
        source.source_type = 'telegram'  # Не youtube

        await service.check_source(source, mock_session)

        # Парсер не должен вызываться
        mock_parser.get_latest_video_id.assert_not_called()


@pytest.mark.asyncio
async def test_check_source_no_username(mock_bot, mock_session):
    """Тест: нет youtube_username — предупреждение"""
    with patch('core.services.youtube_simple_service.get_parser') as mock_get_parser:
        mock_parser = AsyncMock()
        mock_get_parser.return_value = mock_parser
        
        service = YouTubeSimpleMonitoringService(mock_bot)

        source = MagicMock(spec=ContentSource)
        source.source_type = 'youtube'
        source.youtube_username = None
        source.source_global_id = 'yt_no_username'

        await service.check_source(source, mock_session)

        mock_parser.get_latest_video_id.assert_not_called()


@pytest.mark.asyncio
async def test_check_source_no_new_video(mock_bot, mock_session, mock_source):
    """Тест: нет новых видео (last_video_id совпадает)"""
    with patch('core.services.youtube_simple_service.get_parser') as mock_get_parser:
        mock_parser = AsyncMock()
        mock_parser.get_latest_video_id.return_value = 'old_video_123'  # То же самое
        mock_get_parser.return_value = mock_parser
        
        service = YouTubeSimpleMonitoringService(mock_bot)

        await service.check_source(mock_source, mock_session)

        mock_parser.get_latest_video_id.assert_called_once_with('test_channel')
        mock_session.flush.assert_called()


@pytest.mark.asyncio
async def test_check_source_new_video_no_assignments(mock_bot, mock_session, mock_source):
    """Тест: новое видео, но нет назначений"""
    with patch('core.services.youtube_simple_service.get_parser') as mock_get_parser:
        mock_parser = AsyncMock()
        mock_parser.get_latest_video_id.return_value = 'new_video_456'  # Новое видео
        mock_get_parser.return_value = mock_parser
        
        service = YouTubeSimpleMonitoringService(mock_bot)

        with patch.object(service, '_get_source_assignments', new_callable=AsyncMock) as mock_assignments:
            mock_assignments.return_value = []  # Нет назначений

            await service.check_source(mock_source, mock_session)

            mock_parser.get_latest_video_id.assert_called_once_with('test_channel')
            mock_assignments.assert_called_once()
            mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_source_new_video_with_assignments(mock_bot, mock_session, mock_source, mock_assignment):
    """Тест: новое видео с назначениями — отправка"""
    with patch('core.services.youtube_simple_service.get_parser') as mock_get_parser:
        mock_parser = AsyncMock()
        mock_parser.get_latest_video_id.return_value = 'new_video_456'
        mock_get_parser.return_value = mock_parser
        
        service = YouTubeSimpleMonitoringService(mock_bot)

        with patch.object(service, '_get_source_assignments', new_callable=AsyncMock) as mock_assignments:
            mock_assignments.return_value = [mock_assignment]

            await service.check_source(mock_source, mock_session)

            mock_parser.get_latest_video_id.assert_called_once_with('test_channel')
            mock_bot.send_message.assert_called_once()

            # Проверяем аргументы отправки
            call_args = mock_bot.send_message.call_args
            assert call_args.kwargs['chat_id'] == -1001234567890
            assert call_args.kwargs['message_thread_id'] == 42
            assert 'new_video_456' in call_args.kwargs['text']
            assert call_args.kwargs['parse_mode'] == 'HTML'


@pytest.mark.asyncio
async def test_check_source_video_send_error(mock_bot, mock_session, mock_source, mock_assignment):
    """Тест: ошибка при отправке видео"""
    with patch('core.services.youtube_simple_service.get_parser') as mock_get_parser:
        mock_parser = AsyncMock()
        mock_parser.get_latest_video_id.return_value = 'new_video_456'
        mock_get_parser.return_value = mock_parser
        
        service = YouTubeSimpleMonitoringService(mock_bot)

        with patch.object(service, '_get_source_assignments', new_callable=AsyncMock) as mock_assignments:
            mock_assignments.return_value = [mock_assignment]

            # Ошибка при отправке
            mock_bot.send_message.side_effect = Exception("Telegram API error")

            # Ошибка ловится внутри _send_video, rollback не вызывается
            await service.check_source(mock_source, mock_session)

            # Проверяем, что ошибка была залогирована (отправка вызвана)
            mock_bot.send_message.assert_called_once()
            # Rollback не вызывается, т.к. ошибка обработана внутри
            mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_source_assignments(mock_bot, mock_session, mock_assignment):
    """Тест: получение назначений источника"""
    service = YouTubeSimpleMonitoringService(mock_bot)

    # Мокаем выполнение SQL запроса
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_assignment]

    mock_session.execute = AsyncMock(return_value=mock_result)

    assignments = await service._get_source_assignments('yt_test_channel', mock_session)

    assert len(assignments) == 1
    assert assignments[0] == mock_assignment
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_send_video(mock_bot, mock_session, mock_source, mock_assignment):
    """Тест: отправка видео в тему"""
    service = YouTubeSimpleMonitoringService(mock_bot)

    await service._send_video('test_video_123', mock_source, [mock_assignment], mock_session)

    mock_bot.send_message.assert_called_once()

    call_args = mock_bot.send_message.call_args
    assert call_args.kwargs['chat_id'] == -1001234567890
    assert call_args.kwargs['message_thread_id'] == 42
    assert 'youtu.be/test_video_123' in call_args.kwargs['text']


@pytest.mark.asyncio
async def test_send_video_closed_topic(mock_bot, mock_session, mock_source, mock_assignment):
    """Тест: закрытая тема — отправка пропускается"""
    service = YouTubeSimpleMonitoringService(mock_bot)

    mock_assignment.topic.is_closed = True

    await service._send_video('test_video_123', mock_source, [mock_assignment], mock_session)

    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_close_service(mock_bot):
    """Тест: закрытие сервиса"""
    with patch('core.services.youtube_simple_service.get_parser') as mock_get_parser:
        mock_parser = AsyncMock()
        mock_get_parser.return_value = mock_parser
        
        service = YouTubeSimpleMonitoringService(mock_bot)

        await service.close()
        mock_parser.close.assert_called_once()

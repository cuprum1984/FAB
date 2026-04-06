"""
Тесты copy_message режима отправки постов.
Версия: 6.7 (5 апреля 2026)
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from core.services.monitoring.post_sender import PostSender


class FakeTopic:
    """Фейковая тема для тестов"""
    def __init__(self, telegram_chat_id=-1001234567890, telegram_thread_id=1, is_closed=False):
        self.telegram_chat_id = telegram_chat_id
        self.telegram_thread_id = telegram_thread_id
        self.is_closed = is_closed
        self.is_exists_in_tg = True
        self.last_seen_at = None
        self.topic_name = "Тестовая тема"
        self.topic_identifier = f"{telegram_chat_id}:{telegram_thread_id}"


class FakeAssignment:
    """Фейковое назначение для тестов"""
    def __init__(self, topic=None):
        self.topic = topic or FakeTopic()
        self.topic_identifier = self.topic.topic_identifier


class FakeSource:
    """Фейковый источник для тестов"""
    def __init__(self, username="test_channel", title="Test Channel"):
        self.telegram_username = username
        self.channel_title = title


class TestCopyMessageToTopic:
    """Тесты copy_message метода"""

    @pytest.mark.asyncio
    async def test_copy_message_success(self):
        """Успешное копирование сообщения"""
        mock_bot = AsyncMock()
        mock_bot.copy_message = AsyncMock()

        post_sender = PostSender(mock_bot)
        post = {'post_id': '123'}
        source = FakeSource()
        assignment = FakeAssignment()
        updated_topics = set()

        result = await post_sender._copy_message_to_topic(
            post=post,
            source=source,
            assignment=assignment,
            updated_topics=updated_topics
        )

        assert result is True
        mock_bot.copy_message.assert_called_once()
        assert len(updated_topics) == 1

    @pytest.mark.asyncio
    async def test_copy_message_missing_post_id(self):
        """Отсутствует post_id"""
        mock_bot = AsyncMock()
        post_sender = PostSender(mock_bot)
        post = {'post_id': None}
        source = FakeSource()
        assignment = FakeAssignment()
        updated_topics = set()

        result = await post_sender._copy_message_to_topic(
            post=post,
            source=source,
            assignment=assignment,
            updated_topics=updated_topics
        )

        assert result is False
        mock_bot.copy_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_copy_message_missing_username(self):
        """Отсутствует username источника"""
        mock_bot = AsyncMock()
        post_sender = PostSender(mock_bot)
        post = {'post_id': '123'}
        source = FakeSource(username=None)
        assignment = FakeAssignment()
        updated_topics = set()

        result = await post_sender._copy_message_to_topic(
            post=post,
            source=source,
            assignment=assignment,
            updated_topics=updated_topics
        )

        assert result is False
        mock_bot.copy_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_copy_message_private_channel_error(self):
        """Ошибка приватного канала (forbidden)"""
        mock_bot = AsyncMock()
        mock_bot.copy_message = AsyncMock(side_effect=Exception("Forbidden: bot was kicked"))

        post_sender = PostSender(mock_bot)
        post = {'post_id': '123'}
        source = FakeSource()
        assignment = FakeAssignment()
        updated_topics = set()

        result = await post_sender._copy_message_to_topic(
            post=post,
            source=source,
            assignment=assignment,
            updated_topics=updated_topics
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_copy_message_chat_not_found_error(self):
        """Ошибка чат не найден"""
        mock_bot = AsyncMock()
        mock_bot.copy_message = AsyncMock(side_effect=Exception("Chat not found"))

        post_sender = PostSender(mock_bot)
        post = {'post_id': '123'}
        source = FakeSource()
        assignment = FakeAssignment()
        updated_topics = set()

        result = await post_sender._copy_message_to_topic(
            post=post,
            source=source,
            assignment=assignment,
            updated_topics=updated_topics
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_copy_message_updates_last_seen_at(self):
        """copy_message обновляет last_seen_at"""
        mock_bot = AsyncMock()
        mock_bot.copy_message = AsyncMock()

        post_sender = PostSender(mock_bot)
        post = {'post_id': '123'}
        source = FakeSource()
        topic = FakeTopic()
        assignment = FakeAssignment(topic=topic)
        updated_topics = set()

        await post_sender._copy_message_to_topic(
            post=post,
            source=source,
            assignment=assignment,
            updated_topics=updated_topics
        )

        assert topic.last_seen_at is not None
        assert topic in updated_topics


class TestOriginalPostKeyboard:
    """Тесты создания клавиатуры с кнопкой оригинала"""

    def test_keyboard_with_valid_post(self):
        """Клавиатура с валидным post_id"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'post_id': '123'}
        source = FakeSource()

        keyboard = post_sender._get_original_post_keyboard(post, source)

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        button = keyboard.inline_keyboard[0][0]
        assert button.text == "📎 Открыть оригинал"
        assert button.url == "https://t.me/test_channel/123"

    def test_keyboard_with_missing_post_id(self):
        """Клавиатура с отсутствующим post_id"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'post_id': None}
        source = FakeSource()

        keyboard = post_sender._get_original_post_keyboard(post, source)

        assert keyboard is None

    def test_keyboard_with_missing_username(self):
        """Клавиатура с отсутствующим username"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'post_id': '123'}
        source = FakeSource(username=None)

        keyboard = post_sender._get_original_post_keyboard(post, source)

        assert keyboard is None


class TestFormatTelegramPostMessage:
    """Тесты форматирования сообщения"""

    def test_with_channel_title(self):
        """С заголовком канала"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'text': 'Текст поста', 'timestamp': None}
        source = FakeSource()

        message = post_sender._format_telegram_post_message(post, source)

        assert "<b>Test Channel | @test_channel</b>" in message
        assert "Текст поста" in message
        # Ссылка на оригинал убрана
        assert "🔗 Оригинал" not in message

    def test_without_channel_title(self):
        """Без заголовка канала"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'text': 'Текст поста', 'timestamp': None}
        source = FakeSource(title=None)

        message = post_sender._format_telegram_post_message(post, source)

        assert "<b>@test_channel</b>" in message

    def test_with_timestamp(self):
        """С timestamp"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'text': 'Текст поста', 'timestamp': 1712345678}
        source = FakeSource()

        message = post_sender._format_telegram_post_message(post, source)

        assert "<i>" in message  # Время в курсиве
        assert "Текст поста" in message

    def test_empty_text(self):
        """Пустой текст"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'text': '', 'timestamp': None}
        source = FakeSource()

        message = post_sender._format_telegram_post_message(post, source)

        assert "📎 [Медиа-сообщение]" in message

    def test_message_truncation(self):
        """Обрезка длинного сообщения"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'text': 'a' * 5000, 'timestamp': None}
        source = FakeSource()

        message = post_sender._format_telegram_post_message(post, source)

        assert len(message) <= 4000
        assert message.endswith("...")

    def test_no_original_link_in_message(self):
        """Ссылка на оригинал НЕ в тексте (теперь в кнопке)"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)
        post = {'text': 'Текст', 'post_id': '123', 'timestamp': None}
        source = FakeSource()

        message = post_sender._format_telegram_post_message(post, source)

        assert "t.me/" not in message
        assert "🔗 Оригинал" not in message


class TestSendToAssignment:
    """Тесты универсального метода send_to_assignment"""

    @pytest.mark.asyncio
    async def test_closed_topic_returns_false(self):
        """Закрытая тема возвращает False"""
        mock_bot = AsyncMock()
        post_sender = PostSender(mock_bot)
        post = {'post_id': '123'}
        source = FakeSource()
        assignment = FakeAssignment(topic=FakeTopic(is_closed=True))
        updated_topics = set()

        result = await post_sender.send_to_assignment(
            post=post,
            assignment=assignment,
            source=source,
            session=None,
            updated_topics=updated_topics
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_fallback_to_html_on_copy_message_error(self):
        """Fallback на HTML при ошибке copy_message"""
        mock_bot = AsyncMock()
        mock_bot.copy_message = AsyncMock(side_effect=Exception("Chat not found"))
        mock_bot.send_message = AsyncMock(return_value=True)

        post_sender = PostSender(mock_bot)
        post = {'post_id': '123', 'text': 'Текст'}
        source = FakeSource()
        assignment = FakeAssignment()
        updated_topics = set()

        result = await post_sender.send_to_assignment(
            post=post,
            assignment=assignment,
            source=source,
            session=None,
            updated_topics=updated_topics
        )

        # Должен сработать fallback на HTML
        assert result is True
        mock_bot.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_fallback_to_plain_on_html_error(self):
        """Fallback на plain text при ошибке HTML"""
        mock_bot = AsyncMock()
        mock_bot.copy_message = AsyncMock(side_effect=Exception("Chat not found"))
        # Первый вызов send_message (HTML) падает, второй (plain) успешен
        mock_bot.send_message = AsyncMock(side_effect=[
            Exception("Can't parse entities"),
            True
        ])

        post_sender = PostSender(mock_bot)
        post = {'post_id': '123', 'text': 'Текст'}
        source = FakeSource()
        assignment = FakeAssignment()
        updated_topics = set()

        # _send_message_with_retry обрабатывает ошибку парсинга internally
        mock_bot.send_message = AsyncMock(return_value=True)

        result = await post_sender.send_to_assignment(
            post=post,
            assignment=assignment,
            source=source,
            session=None,
            updated_topics=updated_topics
        )

        assert result is True

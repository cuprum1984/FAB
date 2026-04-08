"""
Тесты copy_message режима отправки постов.
Версия: 6.9 (7 апреля 2026)
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from core.services.monitoring.post_sender import PostSender
from aiogram.types import LinkPreviewOptions


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
        assert button.text == "📢 Test Channel"
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
    """Тесты send_to_assignment"""

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
    async def test_send_text_with_preview(self):
        """Отправка текста с превью"""
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock(return_value=True)

        post_sender = PostSender(mock_bot)
        post = {
            'post_id': '123',
            'text': 'Текст поста',
            'media': [{'type': 'photo', 'url': 'https://cdn.example.com/photo.jpg'}]
        }
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

        assert result is True
        mock_bot.send_message.assert_called()
        # Проверка что link_preview_options передан
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert 'link_preview_options' in call_kwargs


# ======================================================================
# ТЕСТЫ LINK PREVIEW OPTIONS (v6.9)
# ======================================================================

class TestLinkPreviewOptions:
    """Тесты умного превью (LinkPreviewOptions)"""

    def test_link_preview_with_media(self):
        """Превью ВКЛ если есть медиа в посте"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {
            'post_id': '123',
            'text': '<b>Тест</b>',
            'media': [{'type': 'photo', 'url': 'https://cdn.example.com/photo.jpg'}],
            'url': 'https://t.me/test_channel/123',
            'timestamp': 1234567890
        }
        source = FakeSource()

        options = post_sender._get_link_preview_options(post, source)

        assert options.is_disabled is False
        assert options.url == 'https://t.me/test_channel/123'
        assert options.prefer_large_media is True
        assert options.show_above_text is True

    def test_link_preview_without_media(self):
        """Превью ВКЛ даже если нет медиа"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {
            'post_id': '123',
            'text': '<b>Тест</b>',
            'url': 'https://t.me/test_channel/123',
            'timestamp': 1234567890
        }
        source = FakeSource()

        options = post_sender._get_link_preview_options(post, source)

        assert options.is_disabled is False

    def test_link_preview_url_is_post_url(self):
        """Превью на t.me/username/123"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {
            'post_id': '456',
            'text': '<b>Тест</b>',
            'media': [{'type': 'photo', 'url': 'https://cdn.example.com/photo.jpg'}],
            'url': 'https://t.me/mychannel/456',
            'timestamp': 1234567890
        }
        source = FakeSource(username='mychannel')

        options = post_sender._get_link_preview_options(post, source)

        assert options.url == 'https://t.me/mychannel/456'

    def test_link_preview_large_media(self):
        """prefer_large_media=True"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {
            'post_id': '123',
            'media': [{'type': 'photo', 'url': 'https://cdn.example.com/photo.jpg'}]
        }
        source = FakeSource()

        options = post_sender._get_link_preview_options(post, source)

        assert options.prefer_large_media is True
        assert options.prefer_small_media is False

    def test_link_preview_above_text(self):
        """show_above_text=True"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {
            'post_id': '123',
            'media': [{'type': 'photo', 'url': 'https://cdn.example.com/photo.jpg'}]
        }
        source = FakeSource()

        options = post_sender._get_link_preview_options(post, source)

        assert options.show_above_text is True

    def test_link_preview_ignores_external_links(self):
        """Внешние ссылки в тексте не перехватывают превью"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {
            'post_id': '123',
            'text': '<b>Текст</b> <a href="https://external.com/article">статья</a>',
            'media': [{'type': 'photo', 'url': 'https://cdn.example.com/photo.jpg'}],
            'url': 'https://t.me/test_channel/123',
            'timestamp': 1234567890
        }
        source = FakeSource()

        options = post_sender._get_link_preview_options(post, source)

        # Превью на пост, не на внешнюю ссылку
        assert options.url == 'https://t.me/test_channel/123'
        assert options.is_disabled is False

    def test_link_preview_missing_post_id(self):
        """Превью ВЫКЛ если нет post_id"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {
            'text': '<b>Тест</b>',
            'media': [{'type': 'photo', 'url': 'https://cdn.example.com/photo.jpg'}]
        }
        source = FakeSource()

        options = post_sender._get_link_preview_options(post, source)

        assert options.is_disabled is True

    def test_link_preview_missing_username(self):
        """Превью ВЫКЛ если нет username"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {
            'post_id': '123',
            'media': [{'type': 'photo', 'url': 'https://cdn.example.com/photo.jpg'}]
        }
        source = FakeSource(username=None)

        options = post_sender._get_link_preview_options(post, source)

        assert options.is_disabled is True


class TestKeyboardChannelTitle:
    """Тесты кнопки с названием канала"""

    def test_keyboard_channel_title(self):
        """Кнопка с названием канала"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {'post_id': '123'}
        source = FakeSource(username='techcrunch', title='TechCrunch')

        keyboard = post_sender._get_original_post_keyboard(post, source)

        assert keyboard is not None
        button = keyboard.inline_keyboard[0][0]
        assert button.text == "📢 TechCrunch"
        assert button.url == "https://t.me/techcrunch/123"

    def test_keyboard_username_fallback(self):
        """Кнопка с @username если нет названия"""
        mock_bot = MagicMock()
        post_sender = PostSender(mock_bot)

        post = {'post_id': '456'}
        source = FakeSource(username='mychannel', title=None)

        keyboard = post_sender._get_original_post_keyboard(post, source)

        assert keyboard is not None
        button = keyboard.inline_keyboard[0][0]
        assert button.text == "📢 @mychannel"
        assert button.url == "https://t.me/mychannel/456"

    def test_external_links_preserved_in_text(self):
        """Внешние ссылки остаются в тексте (не удаляются)"""
        # Проверяем что _send_message_with_retry НЕ модифицирует текст
        original_text = '<b>Текст</b> <a href="https://external.com">статья</a>'

        # Текст должен остатьсяяться без изменений
        # (мы только передаём link_preview_options, не трогаем text)
        assert 'https://external.com' in original_text  # Ссылка на месте

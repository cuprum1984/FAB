"""
Тесты для YouTube Simple Parser
Интеграционные тесты — требуют подключения к интернету
"""

import pytest
import pytest_asyncio
import asyncio
from core.parser.youtube_simple import YouTubeSimpleParser, get_parser, close_parser


@pytest_asyncio.fixture
async def parser():
    """Фикстура парсера"""
    p = YouTubeSimpleParser()
    yield p
    await p.close()


@pytest.mark.asyncio
async def test_fetch_page_valid_url(parser):
    """Тест: загрузка валидной страницы YouTube"""
    html = await parser.fetch_page("https://www.youtube.com/@YouTube")
    
    assert html is not None
    assert len(html) > 0
    assert "YouTube" in html


@pytest.mark.asyncio
async def test_fetch_page_invalid_url(parser):
    """Тест: загрузка несуществующей страницы"""
    html = await parser.fetch_page("https://www.youtube.com/@nonexistent_channel_12345")
    
    # Может вернуть None или HTML с ошибкой
    assert html is None or "error" in html.lower() or html == ""


@pytest.mark.asyncio
async def test_get_channel_id_valid(parser):
    """Тест: получение channel_id для существующего канала"""
    channel_id = await parser.get_channel_id("YouTube")
    
    assert channel_id is not None
    assert channel_id.startswith("UC")
    assert len(channel_id) == 24  # Стандартная длина channel_id


@pytest.mark.asyncio
async def test_get_channel_id_invalid(parser):
    """Тест: получение channel_id для несуществующего канала"""
    channel_id = await parser.get_channel_id("nonexistent_channel_xyz_123")
    
    assert channel_id is None


@pytest.mark.asyncio
async def test_get_latest_video_id_valid(parser):
    """Тест: получение последнего видео для существующего канала"""
    video_id = await parser.get_latest_video_id("YouTube")
    
    assert video_id is not None
    assert len(video_id) == 11  # Стандартная длина video_id


@pytest.mark.asyncio
async def test_get_latest_video_id_invalid(parser):
    """Тест: получение видео для несуществующего канала"""
    video_id = await parser.get_latest_video_id("nonexistent_channel_xyz_123")
    
    assert video_id is None


@pytest.mark.asyncio
async def test_get_channel_data(parser):
    """Тест: получение полных данных канала"""
    data = await parser.get_channel_data("YouTube")
    
    assert data is not None
    assert "channel_id" in data
    assert "channel_title" in data
    assert "video_id" in data
    assert data["channel_id"].startswith("UC")
    assert len(data["video_id"]) == 11


@pytest.mark.asyncio
async def test_get_channel_data_invalid(parser):
    """Тест: данные несуществующего канала"""
    data = await parser.get_channel_data("nonexistent_channel_xyz_123")
    
    assert data is None


@pytest.mark.asyncio
async def test_parser_session_cleanup():
    """Тест: корректное закрытие сессии парсера"""
    parser = YouTubeSimpleParser()
    
    # Делаем запрос для создания сессии
    await parser.fetch_page("https://www.youtube.com/@YouTube")
    
    # Закрываем
    await parser.close()
    
    assert parser.session is None


@pytest.mark.asyncio
async def test_global_parser_functions():
    """Тест: глобальные функции get_parser/close_parser"""
    # Получаем парсер
    p1 = get_parser()
    p2 = get_parser()
    
    # Должен возвращаться тот же экземпляр
    assert p1 is p2
    
    # Закрываем
    await close_parser()
    
    # После закрытия должен создаться новый
    p3 = get_parser()
    assert p3 is not p1


# Пропущенные тесты — требуют стабильного интернета
@pytest.mark.skip(reason="Требуется стабильное подключение к YouTube")
@pytest.mark.asyncio
async def test_real_channel_russian():
    """Интеграционный тест: русский YouTube-канал"""
    parser = YouTubeSimpleParser()
    try:
        data = await parser.get_channel_data("youtuberussia")
        assert data is not None
        print(f"Канал: {data['channel_title']}, Видео: {data['video_id']}")
    finally:
        await parser.close()


@pytest.mark.skip(reason="Требуется стабильное подключение к YouTube")
@pytest.mark.asyncio
async def test_real_multiple_channels():
    """Интеграционный тест: несколько каналов подряд"""
    parser = YouTubeSimpleParser()
    channels = ["YouTube", "MrBeast", "T-Series"]
    
    try:
        for channel in channels:
            video_id = await parser.get_latest_video_id(channel)
            assert video_id is not None, f"Не удалось получить видео для {channel}"
            print(f"{channel}: {video_id}")
            await asyncio.sleep(2)  # Вежливость между запросами
    finally:
        await parser.close()

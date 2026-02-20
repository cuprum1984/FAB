"""
Тесты для RSS парсера.
"""
import asyncio
import pytest
from core.parser.rss import RSSParser, get_parser


@pytest.mark.asyncio
async def test_rss_parser_creation():
    """Тест создания парсера"""
    parser = get_parser()
    assert parser is not None
    assert hasattr(parser, 'get_latest_entries')
    assert hasattr(parser, 'download_image')


@pytest.mark.asyncio
async def test_rss_fetch():
    """Тест загрузки RSS (реальный URL)"""
    parser = RSSParser()
    
    # Тестовый RSS (BBC News)
    entries = await parser.get_latest_entries(
        "http://feeds.bbci.co.uk/news/rss.xml",
        limit=5
    )
    
    assert entries is not None
    assert len(entries) > 0
    
    entry = entries[0]
    assert 'title' in entry
    assert 'link' in entry
    assert 'entry_id_num' in entry
    
    await parser.close()


@pytest.mark.asyncio
async def test_rss_first_only():
    """Тест режима first_only"""
    parser = RSSParser()
    
    entries = await parser.get_latest_entries(
        "http://feeds.bbci.co.uk/news/rss.xml",
        first_only=True
    )
    
    assert len(entries) == 1
    
    await parser.close()


@pytest.mark.asyncio
async def test_rss_html_cleanup():
    """Тест очистки HTML"""
    parser = RSSParser()
    
    html = "<p>Hello <b>world</b>!</p><script>alert('test')</script>"
    cleaned = parser._clean_html(html)
    
    assert "Hello world!" in cleaned
    assert "<script>" not in cleaned
    assert "<b>" not in cleaned


@pytest.mark.asyncio
async def test_rss_entry_id_extraction():
    """Тест извлечения ID записи"""
    parser = RSSParser()
    
    # Создаём mock entry
    class MockEntry:
        def __init__(self, guid=None, id=None, link=None):
            if guid:
                self.guid = guid
            if id:
                self.id = id
            if link:
                self.link = link
    
    # Тест с guid
    entry1 = MockEntry(guid="12345")
    id1 = parser._extract_entry_id(entry1, "http://test.com")
    assert id1 == "12345"
    
    # Тест с id
    entry2 = MockEntry(id="67890")
    id2 = parser._extract_entry_id(entry2, "http://test.com")
    assert id2 == "67890"
    
    # Тест с link
    entry3 = MockEntry(link="http://test.com/post/1")
    id3 = parser._extract_entry_id(entry3, "http://test.com")
    assert id3 == "http://test.com/post/1"


if __name__ == "__main__":
    asyncio.run(test_rss_fetch())
    print("✅ RSS тесты пройдены")
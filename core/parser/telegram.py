# core/parser/telegram.py
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from core.settings import settings


async def check_channel_exists(username: str) -> tuple[bool, str]:
    """Проверяет, существует ли публичный канал"""
    url = f"https://t.me/s/{username}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                headers={"User-Agent": settings.USER_AGENT},
                timeout=settings.REQUEST_TIMEOUT
            ) as resp:
                if resp.status == 200:
                    return True, "Канал найден"
                elif resp.status == 404:
                    return False, "Канал не найден или приватный"
                else:
                    return False, f"Ошибка HTTP {resp.status}"
    except asyncio.TimeoutError:
        return False, "Таймаут при проверке канала"
    except Exception as e:
        return False, f"Ошибка соединения: {str(e)}"


async def get_channel_title(username: str) -> str | None:
    """Получает название канала из веб-просмотра"""
    url = f"https://t.me/s/{username}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": settings.USER_AGENT},
                timeout=settings.REQUEST_TIMEOUT
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Пробуем разные селекторы для названия канала
                    selectors = [
                        'div.tgme_channel_info_header_title',
                        'meta[property="og:title"]',
                        'title'
                    ]
                    
                    for selector in selectors:
                        if 'meta' in selector:
                            tag = soup.select_one(selector)
                            if tag and tag.get('content'):
                                return tag['content'].strip()
                        else:
                            tag = soup.select_one(selector)
                            if tag and tag.text:
                                return tag.text.strip()
                    
                    # Если не нашли через селекторы, пробуем из title
                    title_tag = soup.find('title')
                    if title_tag:
                        title = title_tag.text.strip()
                        # Убираем "Telegram: Contact @" из начала
                        if title.startswith("Telegram: Contact @"):
                            title = title.replace("Telegram: Contact @", "")
                        return title
    except Exception as e:
        print(f"Ошибка при получении названия канала: {e}")
    
    return None
# core/parser/youtube_simple.py
"""
Максимально простой парсер YouTube.
Принцип: "как видит человек" — заходим на /videos, берём первое видео.
Никакого JSON, никаких дат, никаких ID видео.

Rate limiting:
- ✅ Token Bucket: 1 запрос/сек, ведро 5 токенов
- ✅ Exponential backoff при ошибках
- ✅ Глобальный лимит: 60 запросов/мин
- ✅ Случайная задержка между запросами (вежливость)

Версия: 2.0 (28 февраля 2026)
"""

import re
import random
import asyncio
import logging
from typing import Optional
import aiohttp
from core.services.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

# Путь User-Agent для ротации
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
]

class YouTubeSimpleParser:
    """Предельно простой парсер YouTube"""

    def __init__(self):
        self.session = None
        self.rate_limiter = get_rate_limiter()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать сессию"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    def _get_headers(self) -> dict:
        """Случайный User-Agent"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'ru-RU,ru;q=0.8,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        }

    async def fetch_page(self, url: str, username: Optional[str] = None) -> Optional[str]:
        """Загрузить страницу с rate limiting"""
        headers = self._get_headers()
        
        # Определяем ключ для rate limiting
        source_key = username or url

        # Проверяем не слишком ли много ошибок для этого канала
        if self.rate_limiter.should_skip_source("youtube", source_key):
            logger.warning(f"⏭️ Пропускаем {source_key}: слишком много ошибок подряд")
            return None

        # Ждём если есть backoff после ошибок
        backoff_delay = self.rate_limiter.get_backoff_delay("youtube", source_key)
        if backoff_delay > 0:
            logger.info(f"⏳ Backoff для {source_key}: {backoff_delay:.1f}с")
            await asyncio.sleep(backoff_delay)

        # Запрашиваем токен rate limiter
        wait_time = await self.rate_limiter.acquire("youtube")
        if wait_time > 0:
            logger.debug(f"⏳ Rate limit YouTube: ждём {wait_time:.2f}с")
            await asyncio.sleep(wait_time)

        # Дополнительная "вежливая" задержка (1-2 сек)
        await asyncio.sleep(random.uniform(1, 2))

        try:
            session = await self._get_session()

            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    self.rate_limiter.record_error("youtube", source_key)
                    logger.error(f"❌ HTTP {resp.status} для {url}")
                    return None
                
                self.rate_limiter.record_success("youtube", source_key)
                return await resp.text()

        except asyncio.TimeoutError:
            self.rate_limiter.record_error("youtube", source_key)
            logger.error(f"⏱️ Таймаут при загрузке {url}")
            return None
        except aiohttp.ClientError as e:
            self.rate_limiter.record_error("youtube", source_key)
            logger.error(f"❌ Ошибка соединения при загрузке {url}: {e}")
            return None
        except Exception as e:
            self.rate_limiter.record_error("youtube", source_key)
            logger.error(f"❌ Неожиданная ошибка при загрузке {url}: {e}", exc_info=True)
            return None
    
    async def get_channel_id(self, username: str) -> Optional[str]:
        """
        Получить channel_id канала (нужно для БД)
        """
        url = f"https://www.youtube.com/@{username}"
        html = await self.fetch_page(url, username=username)

        if not html:
            return None

        # Ищем channelId в meta-тегах
        patterns = [
            r'<meta property="og:channel:id" content="(UC[^"]+)"',
            r'"channelId":"(UC[^"]+)"',
            r'"browseId":"(UC[^"]+)"',
            r'/channel/(UC[^"\'/?]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                channel_id = match.group(1)
                logger.info(f"✅ Найден channel_id для @{username}: {channel_id}")
                return channel_id

        logger.error(f"❌ Не удалось найти channel_id для @{username}")
        return None

    async def get_latest_video_id(self, username: str) -> Optional[str]:
        """
        ОСНОВНОЙ МЕТОД: берёт ПЕРВОЕ видео на вкладке /videos.
        Именно так человек видит самое новое видео.
        """
        url = f"https://www.youtube.com/@{username}/videos"
        html = await self.fetch_page(url, username=username)

        if not html:
            return None

        # Паттерн 1: data-id (самый частый)
        match = re.search(r'data-id="([a-zA-Z0-9_-]{11})"', html)
        if match:
            video_id = match.group(1)
            logger.info(f"✅ Найдено первое видео (data-id): {video_id}")
            return video_id

        # Паттерн 2: watch?v= (запасной)
        match = re.search(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
        if match:
            video_id = match.group(1)
            logger.info(f"✅ Найдено первое видео (watch): {video_id}")
            return video_id

        logger.error(f"❌ Не удалось найти видео для @{username}")
        return None

    async def get_channel_data(self, username: str) -> Optional[dict]:
        """
        Полные данные канала (для добавления)
        """
        channel_id = await self.get_channel_id(username)
        if not channel_id:
            return None

        video_id = await self.get_latest_video_id(username)
        if not video_id:
            return None

        # Пытаемся получить название канала (опционально)
        url = f"https://www.youtube.com/@{username}"
        html = await self.fetch_page(url, username=username)
        
        channel_title = None
        if html:
            match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if match:
                channel_title = match.group(1).strip()
        
        return {
            'channel_id': channel_id,
            'channel_title': channel_title or f"YouTube канал @{username}",
            'video_id': video_id,
        }
    
    async def close(self):
        """Закрыть сессию"""
        if self.session:
            await self.session.close()
            self.session = None


# Глобальный экземпляр
_parser = None

def get_parser() -> YouTubeSimpleParser:
    """Получить глобальный экземпляр парсера"""
    global _parser
    if _parser is None:
        _parser = YouTubeSimpleParser()
    return _parser

async def close_parser():
    """Закрыть парсер"""
    global _parser
    if _parser:
        await _parser.close()
        _parser = None
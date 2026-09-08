# core/parser/telegram.py
"""
Парсер Telegram-каналов через t.me/s/.

Rate limiting:
- ✅ Token Bucket: 10 запросов/сек, ведро 20 токенов
- ✅ Exponential backoff при ошибках
- ✅ Глобальный лимит: 60 запросов/мин
"""
import aiohttp
import asyncio
import logging
import ssl
import certifi
from bs4 import BeautifulSoup
from core.settings import settings
from core.services.rate_limiter import get_rate_limiter

# Доверенные корневые сертификаты (cross-platform)
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

logger = logging.getLogger(__name__)


async def check_channel_exists(username: str) -> tuple[bool, str]:
    """Проверяет, существует ли публичный канал"""
    url = f"https://t.me/s/{username}"
    rate_limiter = get_rate_limiter()

    # Проверяем не слишком ли много ошибок для этого канала
    if rate_limiter.should_skip_source("telegram", username):
        logger.warning(f"⏭️ Пропускаем @{username}: слишком много ошибок подряд")
        return False, "Пропущено из-за частых ошибок"

    # Ждём если есть backoff после ошибок
    backoff_delay = rate_limiter.get_backoff_delay("telegram", username)
    if backoff_delay > 0:
        logger.info(f"⏳ Backoff для @{username}: {backoff_delay:.1f}с")
        await asyncio.sleep(backoff_delay)

    # Запрашиваем токен rate limiter
    wait_time = await rate_limiter.acquire("telegram")
    if wait_time > 0:
        logger.debug(f"⏳ Rate limit Telegram: ждём {wait_time:.2f}с")
        await asyncio.sleep(wait_time)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": settings.USER_AGENT},
                timeout=settings.REQUEST_TIMEOUT,
                ssl=_SSL_CTX
            ) as resp:
                if resp.status == 200:
                    rate_limiter.record_success("telegram", username)
                    return True, "Канал найден"
                elif resp.status == 404:
                    rate_limiter.record_success("telegram", username)  # 404 не ошибка rate limit
                    return False, "Канал не найден или приватный"
                else:
                    rate_limiter.record_error("telegram", username)
                    return False, f"Ошибка HTTP {resp.status}"
    except asyncio.TimeoutError:
        rate_limiter.record_error("telegram", username)
        return False, "Таймаут при проверке канала"
    except aiohttp.ClientError as e:
        rate_limiter.record_error("telegram", username)
        return False, f"Ошибка соединения: {str(e)}"
    except Exception as e:
        rate_limiter.record_error("telegram", username)
        logger.error(f"❌ Неожиданная ошибка при проверке @{username}: {e}", exc_info=True)
        return False, f"Ошибка: {str(e)}"


async def get_channel_title(username: str) -> str | None:
    """Получает название канала из веб-просмотра"""
    url = f"https://t.me/s/{username}"
    rate_limiter = get_rate_limiter()

    # Проверяем не слишком ли много ошибок для этого канала
    if rate_limiter.should_skip_source("telegram", username):
        logger.warning(f"⏭️ Пропускаем @{username}: слишком много ошибок подряд")
        return None

    # Ждём если есть backoff после ошибок
    backoff_delay = rate_limiter.get_backoff_delay("telegram", username)
    if backoff_delay > 0:
        logger.info(f"⏳ Backoff для @{username}: {backoff_delay:.1f}с")
        await asyncio.sleep(backoff_delay)

    # Запрашиваем токен rate limiter
    wait_time = await rate_limiter.acquire("telegram")
    if wait_time > 0:
        logger.debug(f"⏳ Rate limit Telegram: ждём {wait_time:.2f}с")
        await asyncio.sleep(wait_time)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": settings.USER_AGENT},
                timeout=settings.REQUEST_TIMEOUT,
                ssl=_SSL_CTX
            ) as resp:
                if resp.status == 200:
                    rate_limiter.record_success("telegram", username)
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
                else:
                    rate_limiter.record_error("telegram", username)
                    logger.warning(f"⚠️ HTTP {resp.status} при получении названия @{username}")
    except asyncio.TimeoutError:
        rate_limiter.record_error("telegram", username)
        logger.warning(f"⏱️ Таймаут при получении названия @{username}")
    except aiohttp.ClientError as e:
        rate_limiter.record_error("telegram", username)
        logger.warning(f"⚠️ Ошибка соединения при получении названия @{username}: {e}")
    except Exception as e:
        rate_limiter.record_error("telegram", username)
        logger.error(f"❌ Ошибка при получении названия @{username}: {e}", exc_info=True)

    return None
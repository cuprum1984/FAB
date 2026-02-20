# core/parser/telegram_posts.py
"""
Парсер постов из Telegram веб-просмотра.
Версия: 4.1 (13 февраля 2026)
Изменения:
- Удалены дубликаты функций
- Исправлен проброс first_only
- Единая точка входа
"""
import asyncio
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
import aiohttp
from bs4 import BeautifulSoup
from core.settings import settings


class TelegramPostParser:
    """Парсер постов из Telegram веб-просмотра"""
    
    def __init__(self):
        self.session = None
        
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": settings.USER_AGENT}
            )
        return self.session
    
# 📁 core/parser/telegram_posts.py - ПРОВЕРЯЕМ first_only

    async def get_latest_posts(
        self, 
        username: str, 
        last_known_post_id: Optional[str] = None,
        last_known_timestamp: Optional[int] = None,
        first_only: bool = False  # ✅ ДОЛЖЕН БЫТЬ False ПО УМОЛЧАНИЮ!
    ) -> List[Dict[str, Any]]:
        """
        Получить посты из канала.
        
        Args:
            username: Имя канала без @
            last_known_post_id: ID последнего известного поста
            last_known_timestamp: timestamp (заглушка)
            first_only: True = только первый пост (при добавлении)
                    False = все новые посты (регулярная проверка) ⬅️ ПО УМОЛЧАНИЮ!
        """
        url = f"https://t.me/s/{username}"
        
        try:
            session = await self._get_session()
            async with session.get(url, timeout=settings.REQUEST_TIMEOUT) as resp:
                if resp.status != 200:
                    return []
                
                html = await resp.text()
                return self._parse_posts(html, last_known_post_id, first_only)
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return []

    def _parse_posts(
        self, 
        html: str, 
        last_known_post_id: Optional[str] = None,
        first_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Парсинг постов."""
        soup = BeautifulSoup(html, 'html.parser')
        post_elements = soup.find_all('div', class_='tgme_widget_message')
        
        # 🎯 РЕЖИМ 1: ТОЛЬКО ПОСЛЕДНИЙ ПОСТ (ПРИ ДОБАВЛЕНИИ)
        if first_only:
            if not post_elements:
                return []
            # ✅ БЕРЁМ ПОСЛЕДНИЙ (САМЫЙ НОВЫЙ) ПОСТ!
            post = self._parse_single_post(post_elements[-1])
            return [post] if post else []
        
        # 📦 РЕЖИМ 2: ВСЕ НОВЫЕ ПОСТЫ (РЕГУЛЯРНАЯ ПРОВЕРКА)
        posts = []
        last_id = int(last_known_post_id) if last_known_post_id else 0
        
        for element in post_elements[:50]:
            post = self._parse_single_post(element)
            if not post:
                continue
            
            post_id = int(post['post_id'])
            if post_id > last_id:
                posts.append(post)
        
        posts.sort(key=lambda x: int(x['post_id']))
        return posts


    def _parse_single_post(self, element) -> Optional[Dict[str, Any]]:
        """Парсинг одного поста."""
        try:
            post_id = self._extract_post_id(element)
            if not post_id:
                return None
            
            text_element = element.find('div', class_='tgme_widget_message_text')
            text = text_element.get_text(strip=True) if text_element else ""
            
            media = self._extract_media(element)
            timestamp = self._extract_timestamp(element)
            links = self._extract_links(element)
            is_forwarded = 'tgme_widget_message_forwarded' in element.get('class', [])
            
            return {
                'post_id': post_id,
                'text': text,
                'media': media,
                'timestamp': timestamp,
                'links': links,
                'is_forwarded': is_forwarded,
            }
            
        except Exception as e:
            print(f"❌ Ошибка парсинга поста: {e}")
            return None
    
    def _extract_post_id(self, element) -> Optional[str]:
        """Извлечь ID поста."""
        if element.has_attr('data-post'):
            data_post = element['data-post']
            parts = data_post.split('/')
            if len(parts) == 2:
                return parts[1]
        
        link_element = element.find('a', class_='tgme_widget_message_date')
        if link_element and link_element.has_attr('href'):
            href = link_element['href']
            match = re.search(r'/(\d+)$', href)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_timestamp(self, element) -> int:
        """Извлечь timestamp поста."""
        time_element = element.find('time')
        if time_element and time_element.has_attr('datetime'):
            try:
                dt_str = time_element['datetime']
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                return int(dt.timestamp())
            except (ValueError, AttributeError):
                pass
        return int(time.time())
    
    def _extract_media(self, element) -> List[Dict[str, str]]:
        """Извлечь медиа из поста."""
        media = []
        photo_elements = element.find_all('a', class_='tgme_widget_message_photo_wrap')
        for photo in photo_elements:
            if photo.has_attr('style'):
                style = photo['style']
                url_match = re.search(r'url\(\'([^\']+)\'\)', style)
                if url_match:
                    media.append({
                        'type': 'photo',
                        'url': url_match.group(1)
                    })
        return media
    
    def _extract_links(self, element) -> List[str]:
        """Извлечь ссылки."""
        links = []
        for a in element.find_all('a'):
            if a.has_attr('href'):
                href = a['href']
                if not href.startswith('https://t.me/'):
                    links.append(href)
        return links
    
    async def close(self):
        """Закрыть сессию."""
        if self.session:
            await self.session.close()
            self.session = None


# ✅ Глобальный экземпляр - ТОЛЬКО ОДИН!
parser = TelegramPostParser()


# ✅ ЕДИНСТВЕННАЯ ПУБЛИЧНАЯ ФУНКЦИЯ

async def get_new_posts(
    username: str, 
    last_post_id: Optional[str] = None,
    first_only: bool = False,
    limit: int = 50
) -> List[Dict]:
    """
    Получает новые посты из Telegram канала через t.me/s.
    
    Args:
        username: Username канала (без @)
        last_post_id: ID последнего известного поста
        first_only: если True, вернуть только последний пост
        limit: максимум постов за раз
            
    Returns:
        Список постов (от старых к новым)
    """
    # Импортируем здесь, чтобы избежать циклических зависимостей
    from core.security import URLSecurity
    import logging
    import aiohttp
    from bs4 import BeautifulSoup
    import asyncio
    import re
    
    # Создаём локальный логгер для функции
    logger = logging.getLogger(__name__)
    
    url = f"https://t.me/s/{username}"
    
    # Проверяем безопасность URL
    is_safe, reason = URLSecurity.validate_url(url, 'telegram')
    if not is_safe:
        logger.error(f"❌ Небезопасный Telegram URL для @{username}: {reason}")
        return []
    
    posts = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"❌ HTTP {response.status} для @{username}")
                    return []
                
                html = await response.text()
        
        # Парсим HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ищем все посты
        post_elements = soup.find_all('div', class_='tgme_widget_message_wrap')
        
        if not post_elements:
            logger.debug(f"📭 Нет постов в канале @{username}")
            return []
        
        # Ограничиваем количество
        post_elements = post_elements[:limit]
        
        # Если first_only, берём только последний пост
        if first_only and post_elements:
            post_elements = [post_elements[-1]]
        
        # Проходим по постам от старых к новым
        for post_element in reversed(post_elements):
            try:
                # Извлекаем ID поста
                post_id_elem = post_element.find('a', class_='tgme_widget_message_date')
                if not post_id_elem:
                    continue
                
                href = post_id_elem.get('href', '')
                post_id = href.split('/')[-1]
                
                if not post_id:
                    continue
                
                # Если указан last_post_id и это старый пост - пропускаем
                if last_post_id:
                    try:
                        if int(post_id) <= int(last_post_id):
                            continue
                    except ValueError:
                        logger.error(f"Не удалось конвертировать ID: post_id={post_id}, last_post_id={last_post_id}")
                        continue
                
                # Извлекаем текст
                text_elem = post_element.find('div', class_='tgme_widget_message_text')
                text = text_elem.get_text() if text_elem else ''
                
                # Извлекаем медиа
                media_items = []
                
                # Фото
                photo_elem = post_element.find('a', class_='tgme_widget_message_photo_wrap')
                if photo_elem and photo_elem.get('style'):
                    match = re.search(r"background-image:url\('(.+?)'\)", photo_elem['style'])
                    if match:
                        media_items.append({
                            'type': 'photo',
                            'url': match.group(1)
                        })
                
                # Видео
                video_elem = post_element.find('video', class_='tgme_widget_message_video')
                if video_elem and video_elem.get('src'):
                    media_items.append({
                        'type': 'video',
                        'url': video_elem['src']
                    })
                
                # Ссылка на оригинал
                original_url = f"https://t.me/{username}/{post_id}"
                
                post = {
                    'post_id': post_id,
                    'text': text,
                    'media': media_items,
                    'url': original_url,
                    'timestamp': None  # можно добавить парсинг времени при необходимости
                }
                
                posts.append(post)
                
                # Если first_only, берём только один пост
                if first_only:
                    break
                    
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга поста: {e}")
                continue
        
        logger.info(f"✅ Найдено {len(posts)} новых постов в @{username}")
        posts.sort(key=lambda x: int(x['post_id']))
        return posts
        
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Таймаут при загрузке @{username}")
        return []
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки @{username}: {e}")
        return []


# ✅ ЕДИНСТВЕННАЯ ФУНКЦИЯ ЗАКРЫТИЯ
async def close_parser():
    """Закрыть сессию парсера."""
    await parser.close()
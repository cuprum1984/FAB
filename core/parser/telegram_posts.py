# core/parser/telegram_posts.py
"""
Парсер постов из Telegram веб-просмотра.
Версия: 5.0 (24 февраля 2026)
Изменения:
- Удалён класс TelegramPostParser (дублировал функцию)
- Оставлена только функция get_new_posts()
- Упрощённая архитектура без дублирования
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
import aiohttp
from bs4 import BeautifulSoup
from core.settings import settings
from core.security import URLSecurity
from core.utils.html_sanitizer import sanitize_telegram_html


logger = logging.getLogger(__name__)


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

                # Извлекаем HTML текста (с сохранением форматирования)
                # ⚠️ ВАЖНО: исключаем блок цитаты (reply) — там тоже есть .tgme_widget_message_text
                # Клонируем элемент, удаляем reply, ищем основной текст
                post_clone = BeautifulSoup(str(post_element), 'html.parser')
                for reply in post_clone.find_all(class_='tgme_widget_message_reply'):
                    reply.decompose()

                text_elem = post_clone.find('div', class_='tgme_widget_message_text')
                if text_elem:
                    raw_html = str(text_elem.decode_contents())
                    text = sanitize_telegram_html(raw_html, max_length=4000)
                else:
                    text = ''

                # Извлекаем timestamp из <time> элемента
                timestamp = None
                time_elem = post_element.find('time')
                if time_elem and time_elem.get('datetime'):
                    try:
                        timestamp = int(datetime.fromisoformat(time_elem['datetime']).timestamp())
                    except Exception:
                        timestamp = None

                # Извлекаем медиа
                media_items = []

                # Фото (альбомы — ищем ВСЕ фото)
                for photo_elem in post_element.find_all('a', class_='tgme_widget_message_photo_wrap'):
                    if photo_elem and photo_elem.get('style'):
                        match = re.search(r"background-image:url\('(.+?)'\)", photo_elem['style'])
                        if match:
                            media_items.append({
                                'type': 'photo',
                                'url': match.group(1)
                            })

                # Видео (обычное)
                video_elem = post_element.find('video', class_='tgme_widget_message_video')
                if video_elem and video_elem.get('src'):
                    media_items.append({
                        'type': 'video',
                        'url': video_elem['src']
                    })

                # Видео-кружок (видеосообщение)
                round_video_elem = post_element.find('video', class_='tgme_widget_message_round_video')
                if round_video_elem and round_video_elem.get('src'):
                    media_items.append({
                        'type': 'video_note',
                        'url': round_video_elem['src']
                    })

                # GIF (анимация)
                gif_elem = post_element.find('a', class_='tgme_widget_message_gif')
                if gif_elem and gif_elem.get('data-video-src'):
                    media_items.append({
                        'type': 'animation',
                        'url': gif_elem['data-video-src']
                    })

                # Аудио / Музыка
                audio_elem = post_element.find('audio', class_='tgme_widget_message_voice')
                if audio_elem and audio_elem.get('src'):
                    media_items.append({
                        'type': 'audio',
                        'url': audio_elem['src']
                    })

                # Документ / Файл
                doc_wrap = post_element.find('a', class_='tgme_widget_message_document_wrap')
                if doc_wrap and doc_wrap.get('href'):
                    media_items.append({
                        'type': 'document',
                        'url': doc_wrap['href']
                    })

                # Ссылка-превью (link preview)
                link_image = post_element.find('img', class_='tgme_widget_message_link_image')
                if link_image and link_image.get('src'):
                    media_items.append({
                        'type': 'photo',  # Превью ссылки как фото
                        'url': link_image['src']
                    })

                # Ссылка на оригинал
                original_url = f"https://t.me/{username}/{post_id}"

                post = {
                    'post_id': post_id,
                    'text': text,
                    'media': media_items,
                    'url': original_url,
                    'timestamp': timestamp  # ✅ Теперь не None
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
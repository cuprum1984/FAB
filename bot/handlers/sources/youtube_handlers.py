"""Логика обработки YouTube каналов."""
import logging
from aiogram import Router
from aiogram.fsm.context import FSMContext

from core.parser.youtube_simple import get_parser
from core.security import URLSecurity

logger = logging.getLogger(__name__)
router = Router(name="sources_youtube")


async def process_youtube_channel(raw_input: str, state: FSMContext, get_text: callable):
    """
    Проверить YouTube канал и сохранить данные.
    
    Args:
        raw_input: Ссылка или username YouTube канала
        state: FSM context
        get_text: Функция локализации
    
    Returns:
        dict с данными канала или None при ошибке
    """
    # Проверяем безопасность URL
    is_safe, reason = URLSecurity.validate_url(raw_input, 'youtube')
    if not is_safe:
        return None, get_text(['sources', 'youtube_blocked'], reason=reason)

    # Извлекаем username из ссылки
    username = raw_input.strip()
    if 'youtube.com/@' in username:
        username = username.split('youtube.com/@')[-1].split('/')[0]
    elif 'youtube.com/c/' in username:
        username = username.split('youtube.com/c/')[-1].split('/')[0]
    elif 'youtu.be/' in username:
        return None, get_text(['sources', 'youtube_invalid_link'])

    # Используем простой парсер
    youtube_parser = get_parser()

    channel_data = await youtube_parser.get_channel_data(username)
    if not channel_data:
        import asyncio
        await asyncio.sleep(3)
        channel_data = await youtube_parser.get_channel_data(username)

    if not channel_data:
        return None, get_text(['sources', 'youtube_failed'])

    return {
        'channel_id': channel_data['channel_id'],
        'channel_title': channel_data['channel_title'],
        'video_id': channel_data['video_id'],
        'youtube_username': username,
        'feed_url': f"https://youtube.com/@{username}",
        'source_global_id': f"yt_channel_{channel_data['channel_id']}",
        'source_type': 'youtube'
    }, None


async def get_youtube_channel_data(username: str):
    """
    Получить данные канала с повторной попыткой.
    
    Args:
        username: Username YouTube канала
    
    Returns:
        dict с данными канала или None
    """
    youtube_parser = get_parser()
    
    channel_data = await youtube_parser.get_channel_data(username)
    if not channel_data:
        import asyncio
        await asyncio.sleep(3)
        channel_data = await youtube_parser.get_channel_data(username)
    
    return channel_data

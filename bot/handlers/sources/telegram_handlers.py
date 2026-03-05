"""Логика обработки Telegram каналов."""
import logging
import re
from aiogram import Router
from aiogram.fsm.context import FSMContext

from core.parser.telegram import check_channel_exists, get_channel_title
from core.parser.telegram_posts import get_new_posts as get_telegram_posts

logger = logging.getLogger(__name__)
router = Router(name="sources_telegram")

USERNAME_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$")


async def process_telegram_channel(username: str, state: FSMContext, get_text: callable):
    """
    Проверить Telegram канал и сохранить данные.
    
    Args:
        username: Username Telegram канала (без @)
        state: FSM context
        get_text: Функция локализации
    
    Returns:
        dict с данными канала или None при ошибке
    """
    if not USERNAME_REGEX.match(username):
        if len(username) == 4 and re.match(r"^[a-zA-Z][a-zA-Z0-9_]{3}$", username):
            logger.info(f"⚠️ Обнаружен короткий username (4 символа): @{username}")
        else:
            return None, get_text(['sources', 'telegram_invalid_username'])

    exists, error = await check_channel_exists(username)
    if not exists:
        return None, get_text(['sources', 'telegram_not_found'], error=error)

    posts = await get_telegram_posts(username, first_only=True)
    if not posts:
        return None, get_text(['sources', 'telegram_no_posts'], username=username)

    first_post = posts[0]
    first_post_id = int(first_post['post_id'])
    title = await get_channel_title(username) or f"Канал @{username}"

    return {
        'source_type': 'telegram',
        'source_username': username,
        'source_title': title,
        'first_post': first_post,
        'first_post_id': first_post_id,
        'source_global_id': f"tg_channel_{username}"
    }, None


async def validate_telegram_input(raw_input: str, get_text: callable):
    """
    Проверить валидность ввода для Telegram канала.
    
    Args:
        raw_input: Введённый пользователем текст
        get_text: Функция локализации
    
    Returns:
        tuple (username, error_text)
    """
    # Проверяем, не пытаются ли ввести что-то опасное
    if 'http://' in raw_input or 'https://' in raw_input:
        if 't.me' not in raw_input.lower() and 'telegram.org' not in raw_input.lower():
            return None, get_text(['sources', 'telegram_invalid_domain'])

    username = raw_input.strip('@').strip('/').split('/')[-1].lower()
    return username, None

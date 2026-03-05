# bot/middlewares/i18n.py
import logging
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as AiogramUser
from typing import Callable, Dict, Any, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import UserPreferences
from core.utils.i18n import create_i18n

logger = logging.getLogger(__name__)

class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        aiogram_user: AiogramUser = data.get('event_from_user')
        
        # 1. По умолчанию English
        # 2. Пробуем язык из Telegram (ru/en/etc)
        language_code = 'en'
        if aiogram_user and aiogram_user.language_code:
            # Ограничиваем только поддерживаемыми, если нужно, 
            # но create_i18n обычно сам справляется с fallback
            language_code = aiogram_user.language_code.split('-')[0] 

        # 3. Приоритет — настройки из БД
        session: AsyncSession = data.get('session')
        if aiogram_user and session:
            try:
                prefs = await session.get(UserPreferences, aiogram_user.id)
                if prefs and prefs.language:
                    language_code = prefs.language
            except Exception as e:
                logger.error(f"Error getting user preferences: {e}")

        i18n = create_i18n(language_code)
        data['i18n'] = i18n
        data['get_text'] = i18n.get  # Пробрасываем функцию напрямую для удобства
        
        logger.debug(f"🌐 I18nMiddleware: language={language_code}, get_text={data['get_text'] is not None}, event_type={type(event).__name__}")

        return await handler(event, data)
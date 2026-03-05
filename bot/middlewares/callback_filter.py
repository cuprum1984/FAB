# bot/middlewares/callback_filter.py
"""
Middleware для фильтрации callback query в зависимости от типа чата.
Inline-кнопки должны работать только в ЛС с ботом.
"""
import logging
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger(__name__)

class CallbackQueryFilterMiddleware(BaseMiddleware):
    """
    Middleware для фильтрации callback query.

    Правила:
    - Inline кнопки работают только в ЛС с ботом
    - В группах callback игнорируются (кроме специальных префиксов)
    """

    # Callback, которые разрешены в группах (например, админ-панель)
    ALLOWED_IN_GROUPS = {
        "admin_",
        "group_",
        "topic_",
    }

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем не-callback
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        callback_data = event.data
        chat_type = event.message.chat.type if event.message else None

        # === СЛУЧАЙ 1: ЛС с ботом — разрешаем всё ===
        if chat_type == "private":
            logger.debug(f"✅ Callback {callback_data} в ЛС — разрешён")
            return await handler(event, data)

        # === СЛУЧАЙ 2: Группа/топик ===
        elif chat_type in ("group", "supergroup"):
            # Проверяем, разрешён ли этот callback в группах
            is_allowed = any(
                callback_data.startswith(prefix)
                for prefix in self.ALLOWED_IN_GROUPS
            )

            if not is_allowed:
                # Игнорируем callback в группах
                logger.info(f"🚫 Callback {callback_data} в группе {event.message.chat.id} — заблокирован")
                await event.answer("❌ Это меню работает только в личных сообщениях с ботом", show_alert=True)
                return None

            # Разрешённый callback в группе
            logger.debug(f"✅ Callback {callback_data} в группе — разрешён (админ)")
            return await handler(event, data)

        # Не-команды пропускаем всегда
        return await handler(event, data)

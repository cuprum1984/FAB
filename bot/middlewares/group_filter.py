# bot/middlewares/group_filter.py
"""
Middleware для фильтрации команд в зависимости от типа чата.
Версия: 1.0 (21 февраля 2026)
"""
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger(__name__)

class GroupCommandFilterMiddleware(BaseMiddleware):
    """
    Middleware для фильтрации команд в зависимости от типа чата.
    
    Правила:
    - В группах разрешены только: /activ, /plus
    - В ЛС разрешены все команды, но /activ и /plus получают предупреждение
    """
    
    # Команды, разрешённые в группах
    ALLOWED_IN_GROUPS = {"/activ", "/plus"}
    
    # Команды, которые должны использоваться только в группах
    GROUP_ONLY_COMMANDS = {"/activ", "/plus"}
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем не-сообщения
        if not isinstance(event, Message):
            return await handler(event, data)
        
        # Проверяем, является ли сообщение командой
        if event.text and event.text.startswith("/"):
            # Извлекаем чистую команду (без @botusername)
            full_command = event.text.split()[0].lower()
            command = full_command.split('@')[0]
            
            # Определяем язык пользователя для ответа
            user_lang = 'en'  # по умолчанию
            get_text = None
            
            # Пытаемся получить функцию локализации из data
            # (её добавит I18nMiddleware, но он выполняется ПОСЛЕ нас)
            # Поэтому пока используем простой подход с определением языка
            try:
                # Пробуем получить язык из preferences пользователя
                if 'session' in data:
                    from sqlalchemy import select
                    from core.models import UserPreferences
                    
                    stmt = select(UserPreferences).where(
                        UserPreferences.user_id == event.from_user.id
                    )
                    result = await data['session'].execute(stmt)
                    prefs = result.scalar_one_or_none()
                    if prefs:
                        user_lang = prefs.language
                        logger.debug(f"🌐 Язык пользователя {event.from_user.id}: {user_lang}")
            except Exception as e:
                logger.debug(f"Не удалось определить язык: {e}")
            
            # === СЛУЧАЙ 1: Команда в ЛС ===
            if event.chat.type == "private":
                # Проверяем, не является ли команда "групповой"
                if command in self.GROUP_ONLY_COMMANDS:
                    # Локализованный ответ для групповых команд в ЛС
                    if user_lang == 'ru':
                        text = (
                            "⚠️ Команды /activ и /plus работают только в группах и темах!\n\n"
                            "1. Добавьте бота в группу\n"
                            "2. Сделайте его администратором\n"
                            "3. В группе введите /activ\n"
                            "4. В нужной теме введите /plus"
                        )
                    else:
                        text = (
                            "⚠️ Commands /activ and /plus only work in groups and topics!\n\n"
                            "1. Add the bot to a group\n"
                            "2. Make it administrator\n"
                            "3. In the group, enter /activ\n"
                            "4. In the desired topic, enter /plus"
                        )

                    await event.bot.send_message(
                        chat_id=event.from_user.id,
                        text=text,
                        reply_to_message_id=event.message_id
                    )
                    logger.info(f"ℹ️ Пользователь {event.from_user.id} вызвал {command} в ЛС — заблокировано")
                    return None  # Прерываем обработку

                # Все остальные команды в ЛС разрешены
                logger.debug(f"✅ Команда {command} в ЛС разрешена для пользователя {event.from_user.id}")
                return await handler(event, data)
            
            # === СЛУЧАЙ 2: Команда в группе/теме ===
            elif event.chat.type in ("group", "supergroup"):
                # Проверяем, разрешена ли команда в группах
                if command not in self.ALLOWED_IN_GROUPS:
                    # Команда не разрешена в группах
                    logger.info(f"🚫 Заблокирована команда {full_command} в группе {event.chat.id}")
                    
                    # Локализованный ответ
                    if user_lang == 'ru':
                        text = (
                            "⚠️ Эта команда доступна только в личных сообщениях с ботом.\n"
                            "Напишите мне в ЛС: @MyAggryBot"
                        )
                    else:
                        text = (
                            "⚠️ This command is only available in private messages with the bot.\n"
                            "Write to me in DM: @MyAggryBot"
                        )
                    
                    await event.bot.send_message(
                        chat_id=event.chat.id,
                        text=text,
                        reply_to_message_id=event.message_id
                    )
                    logger.info(f"🚫 Заблокирована команда {full_command} в группе {event.chat.id}")
                    return None

                # Разрешённая команда в группе
                return await handler(event, data)
        
        # Не-команды пропускаем всегда
        return await handler(event, data)
"""
Хендлеры бота-помощника.
Версия: 1.0 (14 февраля 2026)
Миссия: Молча кешировать file_id из активированных групп.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select

from core.database import async_session
from core.models import ManagedGroup, CachedMedia, UserCachedMedia
from core.services.helper.cache_service import save_media_to_cache

router = Router(name="helper")
logger = logging.getLogger(__name__)


@router.message()
async def debug_all_messages(message: Message):
    """ВРЕМЕННО — логируем ВСЁ с деталями о репостах"""
    logger.warning(f"🔥🔥🔥 ВХОДЯЩЕЕ СООБЩЕНИЕ:")
    logger.warning(f"   chat_type: {message.chat.type}")
    logger.warning(f"   chat_id: {message.chat.id}")
    logger.warning(f"   message_id: {message.message_id}")
    logger.warning(f"   from_user: {message.from_user.id if message.from_user else None}")
    logger.warning(f"   from_user_name: {message.from_user.full_name if message.from_user else None}")
    logger.warning(f"   from_user_is_bot: {message.from_user.is_bot if message.from_user else None}")
    
    # Информация о репосте
    logger.warning(f"   forward_from_chat: {message.forward_from_chat.id if message.forward_from_chat else None}")
    logger.warning(f"   forward_from_chat_title: {message.forward_from_chat.title if message.forward_from_chat else None}")
    logger.warning(f"   forward_from_message_id: {message.forward_from_message_id if message.forward_from_message_id else None}")
    logger.warning(f"   forward_date: {message.forward_date if message.forward_date else None}")
    
    # Тип контента
    logger.warning(f"   content_type: {message.content_type}")
    logger.warning(f"   text: {message.text}")
    logger.warning(f"   photo: {bool(message.photo)}")
    logger.warning(f"   video: {bool(message.video)}")
    logger.warning(f"   document: {bool(message.document)}")
    logger.warning(f"   caption: {message.caption}")
    
    # Если есть фото — логируем детали
    if message.photo:
        photo = message.photo[-1]
        logger.warning(f"   photo_file_id: {photo.file_id}")
        logger.warning(f"   photo_unique_id: {photo.file_unique_id}")

    logger.warning(f"🔥🔥🔥 Сообщение от: {message.from_user.id if message.from_user else 'None'}, is_bot: {message.from_user.is_bot if message.from_user else 'None'}")


@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Полная тишина — даже не отвечаем.
    """
    logger.debug(f"🤫 /start от {message.from_user.id} проигнорирован")
    # НИЧЕГО НЕ ОТПРАВЛЯЕМ!


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def cache_media(message: Message):
    """
    Молча кешируем медиа из групп.
    Ловит даже репосты от основного бота.
    """
    # 🔥 ЛОГ НА ВХОДЕ
    logger.warning(f"📥 cache_media получил сообщение:")
    logger.warning(f"   from_user: {message.from_user.id if message.from_user else None}")
    logger.warning(f"   from_user_is_bot: {message.from_user.is_bot if message.from_user else None}")
    logger.warning(f"   chat_id: {message.chat.id}")
    logger.warning(f"   content_type: {message.content_type}")
    logger.warning(f"   photo: {bool(message.photo)}")
    
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    
    # Проверяем, активирована ли группа основным ботом
    async with async_session() as session:
        logger.warning(f"🔍 Проверка группы {chat_id} в БД...")
        group = await session.get(ManagedGroup, chat_id)
        
        if not group:
            logger.warning(f"❌ Группа {chat_id} не найдена в БД")
            return
        
        if not group.is_bot_active_in_group:
            logger.warning(f"⏭️ Группа {chat_id} не активирована, пропускаю")
            return
        
        logger.warning(f"✅ Группа {chat_id} активирована, ищем медиа...")
        
        media_items = []
        
        # Фото
        if message.photo:
            photo = message.photo[-1]  # самое большое
            media_items.append({
                'type': 'photo',
                'file_id': photo.file_id,
                'file_unique_id': photo.file_unique_id,
                'file_size': photo.file_size
            })
            logger.warning(f"📸 Найдено фото: {photo.file_id}")
        
        # Видео
        if message.video:
            media_items.append({
                'type': 'video',
                'file_id': message.video.file_id,
                'file_unique_id': message.video.file_unique_id,
                'file_size': message.video.file_size,
                'duration': message.video.duration
            })
            logger.warning(f"🎥 Найдено видео: {message.video.file_id}")
        
        # Документы
        if message.document:
            media_items.append({
                'type': 'document',
                'file_id': message.document.file_id,
                'file_unique_id': message.document.file_unique_id,
                'file_size': message.document.file_size,
                'file_name': message.document.file_name
            })
            logger.warning(f"📎 Найден документ: {message.document.file_id}")
        
        # Если есть медиа — сохраняем
        for media in media_items:
            logger.warning(f"💾 Сохраняю медиа: {media['type']} / {media['file_id']}")
            await save_media_to_cache(
                session=session,
                user_id=user_id,
                chat_id=chat_id,
                message_id=message.message_id,
                media=media,
                caption=message.caption,
                post_url=None
            )
        
        if media_items:
            logger.warning(f"✅ Сохранено {len(media_items)} медиа для user {user_id} из чата {chat_id}")
        else:
            logger.warning(f"📭 Сообщение без медиа (chat_id={chat_id})")
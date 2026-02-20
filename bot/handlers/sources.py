# bot/handlers/sources.py
"""
Хендлеры для управления источниками контента (каналами).
Версия: 6.0 (17 февраля 2026)
Изменения:
- Полный переход на YouTube HTML парсер (вместо RSS)
- Добавлены новые поля: youtube_username, channel_language, last_video_timestamp
- Улучшена обработка кириллических URL
- Добавлено определение языка канала
- Оптимизирована отправка первого видео (одним сообщением)
"""

import urllib.parse
import asyncio
import re
import html
import logging
import hashlib
import random
from typing import Optional
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    ContentSource, 
    SourceSubscription, 
    TopicSourceAssignment,
    ManagedGroup,
    GroupTopic
)
from core.parser.telegram import check_channel_exists, get_channel_title
from core.parser.telegram_posts import get_new_posts as get_telegram_posts
from core.parser.youtube_simple import get_parser
from core.services.destination_service import (
    get_user_destinations, 
    get_user_groups,
    get_source_subscription,
    create_source_subscription,
    create_topic_assignment,
    get_or_create_content_source,
    create_user_channel_subscription
)
from core.redis_client import set_cached_last_post
from core.security import URLSecurity
from bot.states import AddChannel
from bot.keyboards import (
    get_main_menu,
    get_source_list_kb,
    get_destinations_menu,
    get_cancel_kb_reply,
    get_confirm_channel_kb,
    get_cancel_kb
)


# Настройка логгера
logger = logging.getLogger(__name__)

router = Router(name="sources")


USERNAME_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$")


@router.message(Command("add"))
@router.message(F.text == "📥 Добавить канал")
@router.message(F.text == "Добавить канал")
async def cmd_add_channel(message: Message, state: FSMContext, session: AsyncSession): 
    """Начать процесс добавления канала."""
    
    logger.info(f"📥 Пользователь {message.from_user.id} начал добавление канала")
    
    groups = await get_user_groups(message.from_user.id, session)
    if not groups:
        await message.answer(
            "<b>❌ Сначала добавьте хотя бы одну группу через Админ-панель.</b>\n\n"
            "1. Добавьте бота в группу\n"
            "2. Сделайте его администратором\n"
            "3. В группе введите команду /activ",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    await message.answer(
        "<b>📥 Добавление канала</b>\n\n"
        "<b>Введите username канала или ссылку:</b>\n\n"
        "<b>📌 Примеры:</b>\n"
        "• @durov\n"
        "• durov\n"
        "• https://t.me/durov\n"
        "• https://youtube.com/@TheBrainDit\n"
        "• @ОбманутыйРоссиянин (кириллица)\n\n"
        "<i>YouTube каналы — по ссылке или @username</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_kb_reply()
    )
    await state.set_state(AddChannel.waiting_for_username)




@router.message(AddChannel.waiting_for_username)
async def process_channel_username(message: Message, state: FSMContext, session: AsyncSession):
    """Обработать ввод username канала или ссылки."""
    raw_input = URLSecurity.sanitize_input(message.text.strip())
    
    # Декодируем URL-encoded символы (для кириллицы)
    try:
        raw_input = urllib.parse.unquote(raw_input)
        logger.debug(f"🔤 Декодировано: {raw_input}")
    except:
        pass
    
    if raw_input == "❌ Отмена":
        await message.answer("❌ Добавление отменено.", parse_mode="HTML", reply_markup=get_main_menu())
        await state.clear()
        return
    
    # ========== 🔍 ПРОВЕРЯЕМ, НЕ YOUTUBE ЛИ ЭТО ==========
    # YouTube ТОЛЬКО по ссылкам, не по @username!
    is_youtube = False
    
    # Проверяем наличие youtube.com или youtu.be в ссылке
    if 'youtube.com/' in raw_input or 'youtu.be/' in raw_input:
        is_youtube = True
        logger.info(f"📺 Обнаружен YouTube по ссылке: {raw_input}")
    elif raw_input.startswith('@'):
        # Если это просто @username - это Telegram!
        logger.info(f"📱 Обнаружен Telegram username: {raw_input}")
        # is_youtube остаётся False
    
    if is_youtube:
        # Проверяем безопасность URL
        is_safe, reason = URLSecurity.validate_url(raw_input, 'youtube')
        if not is_safe:
            await message.answer(
                f"<b>❌ YouTube канал заблокирован</b>\n\nПричина: {reason}",
                parse_mode="HTML",
                reply_markup=get_cancel_kb_reply()
            )
            return
        
        await message.answer("<b>🔍 Проверяю YouTube канал...</b>", parse_mode="HTML")
        
        # Извлекаем username из ссылки
        username = raw_input.strip()
        if 'youtube.com/@' in username:
            username = username.split('youtube.com/@')[-1].split('/')[0]
        elif 'youtube.com/c/' in username:
            username = username.split('youtube.com/c/')[-1].split('/')[0]
        elif 'youtu.be/' in username:
            # Это ссылка на видео, а не на канал
            await message.answer(
                "<b>❌ Это ссылка на видео, а не на канал</b>\n\n"
                "Введите ссылку на канал, например:\n"
                "https://youtube.com/@TheBrainDit",
                parse_mode="HTML",
                reply_markup=get_cancel_kb_reply()
            )
            return
        
        # Используем НОВЫЙ простой парсер
        from core.parser.youtube_simple import get_parser
        youtube_parser = get_parser()
        
        # ===== ПЕРВАЯ ПОПЫТКА =====
        channel_data = await youtube_parser.get_channel_data(username)
        
        # ===== ЕСЛИ НЕ ПОЛУЧИЛОСЬ - ПОВТОР ЧЕРЕЗ 3 СЕКУНДЫ =====
        if not channel_data:
            logger.info(f"⚠️ Первая попытка не удалась для @{username}, пробую через 3 сек...")
            await asyncio.sleep(3)
            channel_data = await youtube_parser.get_channel_data(username)
        
        # ===== ЕСЛИ ВСЁ ЕЩЁ НЕТ - ОШИБКА =====
        if not channel_data:
            await message.answer(
                "<b>❌ Не удалось получить данные канала</b>\n\n"
                "⏳ <i>YouTube может тормозить при первом обращении.\n"
                "Если не получится сразу — бот повторит попытку автоматически.</i>"
                "Проверьте ссылку. Пример: https://youtube.com/@TheBrainDit",
                parse_mode="HTML",
                reply_markup=get_cancel_kb_reply()
            )
            return
        
        channel_id = channel_data['channel_id']
        channel_title = channel_data['channel_title']
        video_id = channel_data['video_id']
        
        # Сохраняем все данные
        await state.update_data(
            source_type="youtube",
            channel_id=channel_id,
            source_title=channel_title,
            youtube_username=username,
            feed_url=f"https://youtube.com/@{username}",
            last_video_id=video_id,
        )
        
        await message.answer(
            f"<b>✅ Найден YouTube канал!</b>\n\n"
            f"• <b>Название:</b> {channel_title}\n"
            f"• <b>Username:</b> @{username}\n"
            f"• <b>Последнее видео:</b> {video_id}\n"
            f"• <b>Ссылка:</b> https://youtu.be/{video_id}\n\n"
            f"<b>Добавить этот канал?</b>",
            parse_mode="HTML",
            reply_markup=get_confirm_channel_kb()
        )
        await state.set_state(AddChannel.confirm_channel)
        return
    
    # ========== ТЕЛЕГРАМ КАНАЛ ==========
    # Проверяем, не пытаются ли ввести что-то опасное
    if 'http://' in raw_input or 'https://' in raw_input:
        # Если это ссылка - проверяем, что это Telegram
        if 't.me' not in raw_input.lower() and 'telegram.org' not in raw_input.lower():
            await message.answer(
                "<b>❌ Недопустимая ссылка</b>\n\n"
                "Разрешены только ссылки на Telegram каналы.",
                parse_mode="HTML",
                reply_markup=get_cancel_kb_reply()
            )
            return
    
    username = raw_input.strip('@').strip('/').split('/')[-1].lower()
    
    if not USERNAME_REGEX.match(username):
        # Проверяем на короткие имена (как @mash - 4 символа)
        if len(username) == 4 and re.match(r"^[a-zA-Z][a-zA-Z0-9_]{3}$", username):
            logger.info(f"⚠️ Обнаружен короткий username (4 символа): @{username}")
            # Разрешаем, но логируем
        else:
            await message.answer(
                "<b>❌ Неверный формат username</b>\n\n"
                "Требования: 5-32 символа, буквы a-z, цифры 0-9, подчёркивание\n"
                "Пример: @durov, durov, https://t.me/durov",
                parse_mode="HTML",
                reply_markup=get_cancel_kb_reply()
            )
            return
    
    await message.answer("<b>🔍 Проверяю Telegram канал...</b>", parse_mode="HTML")
    
    exists, error = await check_channel_exists(username)
    if not exists:
        await message.answer(
            f"<b>❌ Канал не найден</b>\n\nОшибка: {html.escape(error)}",
            parse_mode="HTML",
            reply_markup=get_cancel_kb_reply()
        )
        return
    
    posts = await get_telegram_posts(username, first_only=True)
    if not posts:
        await message.answer(
            f"<b>❌ Не удалось получить пост из канала @{username}</b>",
            parse_mode="HTML",
            reply_markup=get_cancel_kb_reply()
        )
        return
    
    first_post = posts[0]
    first_post_id = int(first_post['post_id'])
    title = await get_channel_title(username) or f"Канал @{username}"
    
    await state.update_data(
        source_type="telegram",
        source_username=username,
        source_title=title,
        first_post=first_post,
        first_post_id=first_post_id
    )
    
    await message.answer(
        f"<b>✅ Информация о канале</b>\n\n"
        f"• Username: @{username}\n"
        f"• Название: {html.escape(title)}\n"
        f"• Последний пост ID: {first_post_id}\n\n"
        f"<b>Добавить этот канал?</b>",
        parse_mode="HTML",
        reply_markup=get_confirm_channel_kb()
    )
    await state.set_state(AddChannel.confirm_channel)


@router.callback_query(AddChannel.confirm_channel, F.data == "confirm_add_channel")
async def confirm_add_channel(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтвердить добавление канала - для Telegram и YouTube"""
    
    await callback.answer()
    
    data = await state.get_data()
    source_type = data.get("source_type")
    
    if not source_type:
        await callback.message.edit_text("❌ Ошибка: тип источника не определён", parse_mode="HTML")
        await state.clear()
        return
    
    try:
        # ========== ОБЩАЯ ИНФОРМАЦИЯ ==========
        source_title = data.get("source_title")
        
        if source_type == "telegram":
            username = data.get("source_username")
            if not username:
                await callback.message.edit_text("❌ Ошибка: username не найден", parse_mode="HTML")
                await state.clear()
                return
            
            source_global_id = f"tg_channel_{username}"
            first_post_id = data.get("first_post_id")
            first_post = data.get("first_post")
            
            await callback.message.edit_text(
                f"✅ Канал @{username} найден!\n"
                f"📥 Последний пост ID: {first_post_id}\n\n"
                f"⏳ Сохраняю...",
                parse_mode="HTML"
            )
            
        elif source_type == "youtube":
            channel_id = data.get("channel_id")
            username = data.get("youtube_username")
            channel_language = data.get("channel_language", 'en')
            
            if not channel_id:
                await callback.message.edit_text("❌ Ошибка: channel_id не найден", parse_mode="HTML")
                await state.clear()
                return
            
            source_global_id = f"yt_channel_{channel_id}"
            feed_url = data.get("feed_url")
            last_video_id = data.get("last_video_id")
            last_video_timestamp = data.get("last_video_timestamp")
            last_video = data.get("last_video")
            
            await callback.message.edit_text(
                f"✅ YouTube канал @{username} найден!\n"
                f"📥 Последнее видео ID: {last_video_id}\n\n"
                f"⏳ Сохраняю...",
                parse_mode="HTML"
            )
        
        # ========== 2. СОЗДАЁМ ИСТОЧНИК ==========
        if source_type == "telegram":
            source, created = await get_or_create_content_source(
                session=session,
                source_global_id=source_global_id,
                source_type="telegram",
                telegram_username=username,
                title=source_title
            )
            
            source.last_successful_post_id = first_post_id
            source.last_successful_post_timestamp = datetime.utcnow()
            
        elif source_type == "youtube":
            source, created = await get_or_create_content_source(
                session=session,
                source_global_id=source_global_id,
                source_type="youtube",
                feed_url=feed_url,
                title=source_title
            )
            
            # Сохраняем новые поля для YouTube HTML парсера
            source.youtube_username = username
            source.channel_language = channel_language
            source.last_video_id = last_video_id
            source.last_video_timestamp = last_video_timestamp
            
            # Числовой хеш для обратной совместимости
            video_id_num = int(hashlib.md5(last_video_id.encode()).hexdigest()[:15], 16) % (10**15)
            source.last_successful_post_id = video_id_num
            source.last_successful_post_timestamp = datetime.utcnow()
        
        source.last_checked_timestamp = datetime.utcnow()
        
        # 🔥 КОММИТИМ В БД
        await session.commit()
        logger.info(f"✅ Установлен last_successful_post_id для {source_global_id}")
        
        # 🔥 ОБНОВЛЯЕМ REDIS (только для Telegram)
        if source_type == "telegram":
            await set_cached_last_post(username, first_post_id)
            logger.info(f"✅ Redis кеш обновлён для @{username}: {first_post_id}")
        
        # ========== 3. ЛИЧНАЯ ПОДПИСКА ==========
        await create_user_channel_subscription(
            session=session,
            user_id=callback.from_user.id,
            source_global_id=source_global_id,
            custom_title=source_title,
            is_active=True
        )
        
        # ========== 4. ВЫБОР ГРУППЫ/ТЕМЫ ==========
        destinations = await get_user_destinations(callback.from_user.id, session)
        
        if not destinations:
            await callback.message.edit_text("❌ Нет подключённых групп", parse_mode="HTML")
            await state.clear()
            return
        
        # Сохраняем данные для следующего шага
        if source_type == "telegram":
            await state.update_data(
                source_global_id=source_global_id,
                destinations=destinations,
                first_post=first_post,
                first_post_id=first_post_id,
                source_title=source_title,
                source_username=username,
                source_type="telegram"
            )
        elif source_type == "youtube":
            await state.update_data(
                source_global_id=source_global_id,
                destinations=destinations,
                first_video=last_video,
                first_video_id=last_video_id,
                source_title=source_title,
                channel_id=channel_id,
                youtube_username=username,
                source_type="youtube"
            )
        
        # ✅ ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ С КЛАВИАТУРОЙ
        await callback.message.answer(
            "📌 Теперь выберите группу/тему для отправки последнего поста:",
            parse_mode="HTML",
            reply_markup=get_destinations_menu(destinations)
        )
        
        await state.set_state(AddChannel.choose_destination)
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка добавления канала: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)[:100]}", 
            parse_mode="HTML"
        )
        await state.clear()


@router.callback_query(AddChannel.confirm_channel, F.data == "cancel_add_channel")
async def cancel_add_channel(callback: CallbackQuery, state: FSMContext):
    """Отменить добавление канала."""
    await callback.answer()
    await callback.message.edit_text("❌ Добавление отменено.", parse_mode="HTML")
    await state.clear()
    await callback.message.answer(
        "Главное меню:", 
        parse_mode="HTML", 
        reply_markup=get_main_menu()
    )


@router.message(AddChannel.choose_destination)
async def process_destination_choice(message: Message, state: FSMContext, session: AsyncSession):
    """Обработать выбор группы/темы и ОТПРАВИТЬ ТОЛЬКО 1 ПОСТ"""
    
    data = await state.get_data()
    destinations = data.get("destinations", [])
    source_global_id = data.get("source_global_id")
    source_type = data.get("source_type", "telegram")
    
    if message.text == "❌ Отмена":
        await message.answer("❌ Отменено", reply_markup=get_main_menu())
        await state.clear()
        return

    # Получаем текст кнопки как есть
    user_input = message.text.strip()
    
    logger.info(f"🔍 Пользователь выбрал: '{user_input}'")
    logger.debug(f"📋 Доступные destinations: {[d['display_name'] for d in destinations]}")
    
    # Ищем выбранный destination
    chosen = None
    
    # Сначала ищем по точному совпадению
    for d in destinations:
        button_text = user_input
        if button_text[:2] in ["💬 ", "🗨️ ", "👥 ", "📰 ", "🎯 "]:
            clean_input = button_text[2:].strip()
        else:
            clean_input = button_text
            
        if d['display_name'] == clean_input or d['display_name'] == user_input:
            chosen = d
            logger.info(f"✅ Найдено совпадение: {d['display_name']}")
            break
    
    # Если не нашли, ищем по вхождению
    if not chosen:
        for d in destinations:
            if d['display_name'] in user_input:
                chosen = d
                logger.info(f"✅ Найдено по частичному совпадению: {d['display_name']}")
                break
    
    if not chosen:
        await message.answer(
            "❌ Не удалось распознать выбор. Пожалуйста, выберите из списка:",
            parse_mode="HTML",
            reply_markup=get_destinations_menu(destinations)
        )
        return

    try:
        chat_id = chosen["chat_id"]
        topic_identifier = chosen["topic_identifier"]
        
        logger.info(f"🔄 Добавление {source_type} канала в {chosen['display_name']}")
        
        # ========== 1. ПРОВЕРЯЕМ ИСТОЧНИК ==========
        source_stmt = select(ContentSource).where(ContentSource.source_global_id == source_global_id)
        source_result = await session.execute(source_stmt)
        source = source_result.scalar_one_or_none()
        
        if not source:
            # Создаём, если вдруг не создался
            if source_type == "telegram":
                username = data.get("source_username")
                title = data.get("source_title")
                source, _ = await get_or_create_content_source(
                    session=session,
                    source_global_id=source_global_id,
                    source_type="telegram",
                    telegram_username=username,
                    title=title
                )
            elif source_type == "youtube":
                channel_id = data.get("channel_id")
                username = data.get("youtube_username")
                title = data.get("source_title")
                feed_url = data.get("feed_url")
                channel_language = data.get("channel_language", 'en')
                
                source, _ = await get_or_create_content_source(
                    session=session,
                    source_global_id=source_global_id,
                    source_type="youtube",
                    feed_url=feed_url,
                    title=title
                )
                # Добавляем специфичные поля
                source.youtube_username = username
                source.channel_language = channel_language
            
            logger.info(f"✅ Создан источник в процессе добавления: {source_global_id}")
        
        # ========== 2. ПОДПИСКА ГРУППЫ ==========
        subscription = await get_source_subscription(chat_id, source_global_id, session)
        if not subscription:
            subscription = await create_source_subscription(
                chat_id=chat_id,
                source_global_id=source_global_id,
                added_by_id=message.from_user.id,
                session=session
            )
            logger.info(f"✅ Создана подписка ID: {subscription.subscription_id}")
        else:
            logger.info(f"✅ Подписка уже существует ID: {subscription.subscription_id}")
        
        # ========== 3. НАЗНАЧЕНИЕ В ТЕМУ ==========
        existing_stmt = select(TopicSourceAssignment).where(
            and_(
                TopicSourceAssignment.topic_identifier == topic_identifier,
                TopicSourceAssignment.subscription_id == subscription.subscription_id
            )
        )
        existing_result = await session.execute(existing_stmt)
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment:
            await message.answer(
                f"✅ Этот канал уже добавлен в {chosen['display_name']}.",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            await state.clear()
            return
        
        assignment = await create_topic_assignment(
            topic_identifier=topic_identifier,
            subscription_id=subscription.subscription_id,
            session=session
        )
        logger.info(f"✅ Создано назначение ID: {assignment.assignment_id}")
        
        # ========== 4. СОХРАНЯЕМ ВСЁ ==========
        await session.commit()
        
        # ========== 5. 🎯 ОТПРАВЛЯЕМ ТОЛЬКО 1 ПОСТ! ==========
        if source_type == "telegram":
            first_post = data.get("first_post")
            first_post_id = data.get("first_post_id")
            username = data.get("source_username")
            
            if first_post:
                try:
                    source_name = source.title or f"@{username}"
                    text = first_post.get('text', '').strip()
                    if not text:
                        text = "📎 [Медиа-сообщение]"
                    
                    message_text = f"<b>{source_name}</b>\n\n{text}"
                    
                    if first_post.get('post_id'):
                        message_text += f"\n\n<a href='https://t.me/{username}/{first_post_id}'>🔗 Оригинал</a>"
                    
                    await message.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=chosen.get('thread_id'),
                        text=message_text,
                        parse_mode="HTML",
                        disable_web_page_preview=False
                    )
                    logger.info(f"✅ Отправлен первый пост ID: {first_post_id}")
                    
                except Exception as send_error:
                    logger.error(f"❌ Ошибка отправки первого поста: {send_error}")
        
        elif source_type == "youtube":
            first_video_id = data.get("first_video_id")
            username = data.get("youtube_username") or data.get("channel_id", "")[:8]
            
            if first_video_id:
                try:
                    source_name = source.title or f"YouTube канал @{username}"
                    video_url = f"https://youtu.be/{first_video_id}"
                    
                    # Формируем одно сообщение со ссылкой
                    message_text = f"{video_url}\n\n<b>{source_name}</b>"
                    
                    await message.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=chosen.get('thread_id'),
                        text=message_text,
                        parse_mode="HTML",
                        disable_web_page_preview=False
                    )
                    
                    logger.info(f"✅ Отправлено первое видео: {first_video_id}")
                    
                except Exception as send_error:
                    logger.error(f"❌ Ошибка отправки первого видео: {send_error}")
        
        # ========== 6. УСПЕХ! ==========
        if source_type == "telegram":
            username = data.get("source_username")
            first_post_id = data.get("first_post_id")
            await message.answer(
                f"✅ Канал @{username} успешно добавлен!\n\n"
                f"📥 Отправлен последний пост (ID: {first_post_id})\n"
                f"🎯 Назначение: {chosen['display_name']}\n\n"
                f"⏳ Следующие посты будут приходить автоматически каждые 5 минут.",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            logger.info(f"✅ Канал @{username} добавлен, отправлен 1 пост (ID: {first_post_id})")
        
        elif source_type == "youtube":
            username = data.get("youtube_username")
            first_video_id = data.get("first_video_id")
            await message.answer(
                f"✅ YouTube канал @{username} успешно добавлен!\n\n"
                f"📥 Отправлено последнее видео (ID: {first_video_id})\n"
                f"🎯 Назначение: {chosen['display_name']}\n\n"
                f"⏳ Следующие видео будут приходить автоматически (каждые 30 минут).",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            logger.info(f"✅ YouTube канал @{username} добавлен, отправлено 1 видео")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка в process_destination_choice: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при добавлении канала: {str(e)[:200]}",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    
    finally:
        await state.clear()
        logger.info(f"✅ Состояние очищено")



@router.message(Command(commands=["list", "mysources"]))
@router.message(F.text.in_({"📚 Мои источники", "Мои источники"}))
async def cmd_my_sources(message: Message, session: AsyncSession):
    """Показать источники пользователя сгруппированные по группам и темам"""
    user_id = message.from_user.id
    
    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session)
    if not groups:
        await message.answer(
            "<b>❌ Нет активных групп</b>\n\n"
            "<i>Сначала добавьте группу через Админ-панель или командой /activ</i>",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    group_ids = [group["chat_id"] for group in groups]
    
    # Получаем все подписки для групп пользователя
    stmt = (
        select(
            ManagedGroup.telegram_chat_id,
            ManagedGroup.telegram_chat_title,
            ContentSource,
            SourceSubscription,
            GroupTopic,
            TopicSourceAssignment
        )
        .join(SourceSubscription, SourceSubscription.telegram_chat_id == ManagedGroup.telegram_chat_id)
        .join(ContentSource, ContentSource.source_global_id == SourceSubscription.source_global_id)
        .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
        .join(GroupTopic, GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier)
        .where(ManagedGroup.telegram_chat_id.in_(group_ids))
        .order_by(ManagedGroup.telegram_chat_title, GroupTopic.topic_name, ContentSource.title)
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    if not rows:
        await message.answer(
            "<b>📭 Список источников пуст</b>\n\n"
            "<i>Вы ещё не добавили ни одного источника.</i>\n\n"
            "<b>📌 Как добавить:</b>\n"
            "1. Нажмите '📥 Добавить канал'\n"
            "2. Введите username канала\n"
            "3. Выберите группу для отправки",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    # Группируем по чатам и темам
    grouped_data = {}
    
    for row in rows:
        chat_id = row.telegram_chat_id
        chat_title = row.telegram_chat_title or f"Группа {chat_id}"
        source = row[2]  # ContentSource
        topic = row[4]   # GroupTopic
        
        if chat_id not in grouped_data:
            grouped_data[chat_id] = {
                "title": chat_title,
                "topics": {}
            }
        
        if topic.topic_identifier not in grouped_data[chat_id]["topics"]:
            grouped_data[chat_id]["topics"][topic.topic_identifier] = {
                "name": topic.topic_name,
                "thread_id": topic.telegram_thread_id,
                "sources": []
            }
        
        # Определяем иконку для источника
        source_icon = "📺" if source.source_type == "youtube" else "📰"
        source_name = source.title or (
            f"@{source.telegram_username}" if source.telegram_username 
            else source.youtube_username or "Без названия"
        )
        
        # Добавляем источник с source_global_id
        grouped_data[chat_id]["topics"][topic.topic_identifier]["sources"].append({
            "icon": source_icon,
            "name": source_name,
            "type": source.source_type,
            "url": source.public_url,
            "source_global_id": source.source_global_id
        })
    
    # Формируем текст
    text = "<b>📚 Ваши подписки по группам</b>\n\n"
    total_sources = 0
    
    # Сначала посчитаем общее количество
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            total_sources += len(topic_data["sources"])
    
    # Показываем с ограничением
    max_sources_to_show = 5
    sources_shown = 0
    shown_all = True
    
    for chat_id, chat_data in grouped_data.items():
        if sources_shown >= max_sources_to_show:
            shown_all = False
            break
            
        text += f"👥Группа - <b>{html.escape(chat_data['title'])}</b>\n"
        
        for topic_id, topic_data in chat_data["topics"].items():
            if sources_shown >= max_sources_to_show:
                shown_all = False
                break
                
            text += "    ─────────────────\n"
            topic_icon = "💬Топик - " if topic_data["thread_id"] is None else "🗨️Топик - "
            text += f"    {topic_icon} <b>{html.escape(topic_data['name'])}</b>\n"
            
            for source in topic_data["sources"]:
                if sources_shown >= max_sources_to_show:
                    shown_all = False
                    break
                    
                # Добавляем ссылку на источник
                if source['type'] == 'telegram' and source.get('url'):
                    source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                elif source['type'] == 'youtube' and source.get('url'):
                    source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                else:
                    source_link = html.escape(source['name'])
                
                text += f"        {source['icon']} {source_link}\n"
                sources_shown += 1
        
        text += "\n"
        text += "    ─────────────────\n"
    
    # Если показали не всё, добавляем сообщение
    if not shown_all:
        text += f"<i>... и ещё {total_sources - sources_shown} источников</i>\n\n"
    
    text += f"<b>📊 Всего подписок:</b> {total_sources}\n"
    text += f"<b>👥 Всего групп:</b> {len(grouped_data)}\n\n"
    text += "<b>🔧 Управление:</b> Выберите источник для управления"
    
    # Собираем плоский список для кнопок
    flat_sources = []
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            for source in topic_data["sources"]:
                flat_sources.append(source)
    
    # Отправляем сообщение
    await message.answer(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_source_list_kb(flat_sources)
    )

###############################################

@router.callback_query(F.data.startswith("src_page:"))
async def navigate_sources(callback: CallbackQuery, session: AsyncSession):
    """Навигация по страницам источников - обновляет ВСЁ сообщение"""
    page = int(callback.data.split(":")[1])
    
    # Получаем все источники пользователя
    user_id = callback.from_user.id
    groups = await get_user_groups(user_id, session)
    
    if not groups:
        await callback.message.edit_text("❌ Нет активных групп")
        await callback.answer()
        return
    
    group_ids = [group["chat_id"] for group in groups]
    
    # Получаем все подписки
    stmt = (
        select(
            ManagedGroup.telegram_chat_id,
            ManagedGroup.telegram_chat_title,
            ContentSource,
            SourceSubscription,
            GroupTopic,
            TopicSourceAssignment
        )
        .join(SourceSubscription, SourceSubscription.telegram_chat_id == ManagedGroup.telegram_chat_id)
        .join(ContentSource, ContentSource.source_global_id == SourceSubscription.source_global_id)
        .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
        .join(GroupTopic, GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier)
        .where(ManagedGroup.telegram_chat_id.in_(group_ids))
        .order_by(ManagedGroup.telegram_chat_title, GroupTopic.topic_name, ContentSource.title)
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    # Группируем по чатам и темам
    grouped_data = {}
    
    for row in rows:
        chat_id = row.telegram_chat_id
        chat_title = row.telegram_chat_title or f"Группа {chat_id}"
        source = row[2]
        topic = row[4]
        
        if chat_id not in grouped_data:
            grouped_data[chat_id] = {
                "title": chat_title,
                "topics": {}
            }
        
        if topic.topic_identifier not in grouped_data[chat_id]["topics"]:
            grouped_data[chat_id]["topics"][topic.topic_identifier] = {
                "name": topic.topic_name,
                "thread_id": topic.telegram_thread_id,
                "sources": []
            }
        
        source_icon = "📺" if source.source_type == "youtube" else "📰"
        source_name = source.title or (
            f"@{source.telegram_username}" if source.telegram_username 
            else source.youtube_username or "Без названия"
        )
        
        grouped_data[chat_id]["topics"][topic.topic_identifier]["sources"].append({
            "icon": source_icon,
            "name": source_name,
            "type": source.source_type,
            "url": source.public_url,
            "source_global_id": source.source_global_id
        })
    
    # ===== ФОРМИРУЕМ ТЕКСТ (как в cmd_my_sources) =====
    text = "<b>📚 Ваши подписки по группам</b>\n\n"
    total_sources = 0
    
    # Считаем общее количество
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            total_sources += len(topic_data["sources"])
    
    # Показываем с учётом страницы
    sources_per_page = 5
    sources_shown = 0
    start_source = page * sources_per_page
    end_source = start_source + sources_per_page
    shown_anything = False
    
    for chat_id, chat_data in grouped_data.items():
        if sources_shown >= end_source:
            break
            
        # Показываем группу только если в ней есть источники на этой странице
        group_has_sources = False
        group_text = f"👥Группа - <b>{html.escape(chat_data['title'])}</b>\n"
        
        for topic_id, topic_data in chat_data["topics"].items():
            if sources_shown >= end_source:
                break
                
            topic_has_sources = False
            topic_text = "    ─────────────────\n"
            topic_icon = "💬Топик - " if topic_data["thread_id"] is None else "🗨️Топик - "
            topic_text += f"    {topic_icon} <b>{html.escape(topic_data['name'])}</b>\n"
            
            for source in topic_data["sources"]:
                if sources_shown >= end_source:
                    break
                    
                if sources_shown >= start_source:
                    # Добавляем ссылку на источник
                    if source['type'] == 'telegram' and source.get('url'):
                        source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                    elif source['type'] == 'youtube' and source.get('url'):
                        source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                    else:
                        source_link = html.escape(source['name'])
                    
                    topic_text += f"        {source['icon']} {source_link}\n"
                    topic_has_sources = True
                    shown_anything = True
                
                sources_shown += 1
            
            if topic_has_sources:
                text += group_text if not group_has_sources else ""
                text += topic_text
                group_has_sources = True
        
        if group_has_sources:
            text += "\n"
    
    if not shown_anything:
        text += "<i>Нет источников на этой странице</i>\n\n"
    
    # Если показали не всё, добавляем сообщение
    if sources_shown < total_sources:
        text += f"<i>... и ещё {total_sources - sources_shown} источников</i>\n\n"
    
    text += f"<b>📊 Всего подписок:</b> {total_sources}\n"
    text += f"<b>👥 Всего групп:</b> {len(grouped_data)}\n\n"
    text += "<b>🔧 Управление:</b> Выберите источник для управления"
    
    # Собираем плоский список для кнопок
    flat_sources = []
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            for source in topic_data["sources"]:
                flat_sources.append(source)
    
    # Обновляем ВСЁ сообщение
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_source_list_kb(flat_sources, page=page)
    )
    await callback.answer()

##############################################################################
@router.callback_query(F.data == "close_sources")
async def close_sources(callback: CallbackQuery):
    """Закрыть список источников"""
    await callback.message.delete()
    await callback.answer("Список закрыт")


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустышка для неактивных кнопок"""
    await callback.answer()




@router.callback_query(F.data.startswith("del_source:"))
async def delete_source_subscription(callback: CallbackQuery, session: AsyncSession):
    """Удалить подписку на источник для пользователя/группы (но не из общей БД)"""
    source_global_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    try:
        # Находим подписки пользователя на этот источник
        # (только для его групп, не удаляем из глобального каталога)
        
        # Получаем группы пользователя
        groups = await get_user_groups(user_id, session)
        group_ids = [group["chat_id"] for group in groups]
        
        # Находим все подписки на этот источник в группах пользователя
        stmt = select(SourceSubscription).where(
            and_(
                SourceSubscription.source_global_id == source_global_id,
                SourceSubscription.telegram_chat_id.in_(group_ids)
            )
        )
        result = await session.execute(stmt)
        subscriptions = result.scalars().all()
        
        if not subscriptions:
            await callback.answer("❌ Подписка не найдена")
            return
        
        # Удаляем назначения в темах (TopicSourceAssignment)
        for sub in subscriptions:
            # Удаляем все назначения для этой подписки
            del_assignments = select(TopicSourceAssignment).where(
                TopicSourceAssignment.subscription_id == sub.subscription_id
            )
            assignments_result = await session.execute(del_assignments)
            for assignment in assignments_result.scalars().all():
                await session.delete(assignment)
            
            # Удаляем саму подписку
            await session.delete(sub)
        
        await session.commit()
        
        # Показываем обновленный список
        await callback.answer("✅ Подписка удалена")
        
        # Обновляем список источников (переходим на первую страницу)
        # Можно вызвать navigate_sources с page=0 или просто обновить сообщение
        await update_sources_list(callback.message, session, user_id, page=0)
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка удаления подписки: {e}")
        await callback.answer("❌ Ошибка при удалении")


async def update_sources_list(message: Message, session: AsyncSession, user_id: int, page: int = 0):
    """Вспомогательная функция для обновления списка источников"""
    
    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session)
    if not groups:
        await message.edit_text("❌ Нет активных групп")
        return
    
    group_ids = [group["chat_id"] for group in groups]
    
    # Получаем все подписки
    stmt = (
        select(
            ManagedGroup.telegram_chat_id,
            ManagedGroup.telegram_chat_title,
            ContentSource,
            SourceSubscription,
            GroupTopic,
            TopicSourceAssignment
        )
        .join(SourceSubscription, SourceSubscription.telegram_chat_id == ManagedGroup.telegram_chat_id)
        .join(ContentSource, ContentSource.source_global_id == SourceSubscription.source_global_id)
        .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
        .join(GroupTopic, GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier)
        .where(ManagedGroup.telegram_chat_id.in_(group_ids))
        .order_by(ManagedGroup.telegram_chat_title, GroupTopic.topic_name, ContentSource.title)
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    # Группируем по чатам и темам
    grouped_data = {}
    
    for row in rows:
        chat_id = row.telegram_chat_id
        chat_title = row.telegram_chat_title or f"Группа {chat_id}"
        source = row[2]
        topic = row[4]
        
        if chat_id not in grouped_data:
            grouped_data[chat_id] = {
                "title": chat_title,
                "topics": {}
            }
        
        if topic.topic_identifier not in grouped_data[chat_id]["topics"]:
            grouped_data[chat_id]["topics"][topic.topic_identifier] = {
                "name": topic.topic_name,
                "thread_id": topic.telegram_thread_id,
                "sources": []
            }
        
        source_icon = "📺" if source.source_type == "youtube" else "📰"
        source_name = source.title or (
            f"@{source.telegram_username}" if source.telegram_username 
            else source.youtube_username or "Без названия"
        )
        
        grouped_data[chat_id]["topics"][topic.topic_identifier]["sources"].append({
            "icon": source_icon,
            "name": source_name,
            "type": source.source_type,
            "url": source.public_url,
            "source_global_id": source.source_global_id
        })
    
    # ===== ФОРМИРУЕМ ТЕКСТ =====
    text = "<b>📚 Ваши подписки по группам</b>\n\n"
    total_sources = 0
    
    # Считаем общее количество
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            total_sources += len(topic_data["sources"])
    
    # Показываем с учётом страницы
    sources_per_page = 5
    sources_shown = 0
    start_source = page * sources_per_page
    end_source = start_source + sources_per_page
    shown_anything = False
    
    for chat_id, chat_data in grouped_data.items():
        if sources_shown >= end_source:
            break
            
        group_has_sources = False
        group_text = f"👥Группа - <b>{html.escape(chat_data['title'])}</b>\n"
        
        for topic_id, topic_data in chat_data["topics"].items():
            if sources_shown >= end_source:
                break
                
            topic_has_sources = False
            topic_text = "    ─────────────────\n"
            topic_icon = "💬Топик - " if topic_data["thread_id"] is None else "🗨️Топик - "
            topic_text += f"    {topic_icon} <b>{html.escape(topic_data['name'])}</b>\n"
            
            for source in topic_data["sources"]:
                if sources_shown >= end_source:
                    break
                    
                if sources_shown >= start_source:
                    # Добавляем ссылку на источник
                    if source['type'] == 'telegram' and source.get('url'):
                        source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                    elif source['type'] == 'youtube' and source.get('url'):
                        source_link = f"<a href='{source['url']}'>{html.escape(source['name'])}</a>"
                    else:
                        source_link = html.escape(source['name'])
                    
                    topic_text += f"        {source['icon']} {source_link}\n"
                    topic_has_sources = True
                    shown_anything = True
                
                sources_shown += 1
            
            if topic_has_sources:
                text += group_text if not group_has_sources else ""
                text += topic_text
                group_has_sources = True
        
        if group_has_sources:
            text += "\n"
    
    if not shown_anything:
        text += "<i>Нет источников на этой странице</i>\n\n"
    
    # Если показали не всё, добавляем сообщение
    if sources_shown < total_sources:
        text += f"<i>... и ещё {total_sources - sources_shown} источников</i>\n\n"
    
    text += f"<b>📊 Всего подписок:</b> {total_sources}\n"
    text += f"<b>👥 Всего групп:</b> {len(grouped_data)}\n\n"
    text += "<b>🔧 Управление:</b> Выберите источник для управления"
    
    # ===== СОБИРАЕМ flat_sources =====
    flat_sources = []
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            for source in topic_data["sources"]:
                flat_sources.append(source)
    
    # Обновляем сообщение
    await message.edit_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_source_list_kb(flat_sources, page=page)
    )
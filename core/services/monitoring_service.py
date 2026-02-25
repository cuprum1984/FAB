# core/services/monitoring_service.py
"""
Сервис мониторинга и отправки постов из источников.
Версия: 4.0 (17 февраля 2026)
Изменения:
- Полный переход на YouTube HTML парсинг (вместо RSS)
- Добавлены интервалы: 5 мин для Telegram, 30 мин для YouTube
- Улучшена обработка ошибок для YouTube
- Добавлены случайные задержки между проверками YouTube каналов
- Интеграция с новыми полями БД (youtube_username, last_video_timestamp, channel_language)
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import (
    ContentSource, 
    SourceSubscription, 
    TopicSourceAssignment, 
    GroupTopic,
    ManagedGroup,
    CachedMedia
)
from core.parser.telegram_posts import get_new_posts as get_telegram_posts
from core.services.youtube_simple_service import YouTubeSimpleMonitoringService
#from core.services.youtube_html_service import YouTubeHTMLMonitoringService
from core.database import async_session
from core.redis_client import get_cached_last_post, set_cached_last_post
from core.services.destination_service import (
    get_source_last_post_id,
    update_source_last_post_id,
    invalidate_source_cache_by_username
)

logger = logging.getLogger(__name__)


class MonitoringService:
    """Сервис мониторинга и отправки постов."""
    
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.source_stats = {}
        self._processed_posts = set()
        self.youtube_service = YouTubeSimpleMonitoringService(bot)
        # Используем новый HTML сервис для YouTube
        #self.youtube_service = YouTubeHTMLMonitoringService(bot)
    
    # ----------------------------------------------------------------------
    # 🔥 ОСНОВНОЙ ЦИКЛ
    # ----------------------------------------------------------------------
    
    async def start(self, interval_minutes: int = 5):
        if self.is_running:
            logger.warning("⚠️ Мониторинг уже запущен")
            return
        
        self.is_running = True
        logger.info(f"🚀 Мониторинг запущен (базовый интервал: {interval_minutes} минут)")
        
        # Запускаем проверку групп в отдельной задаче
        asyncio.create_task(self.schedule_groups_check())
        logger.info("📅 Запущена задача проверки групп (2 раза в день)")
        
        while self.is_running:
            try:
                async with async_session() as session:
                    await self.check_all_sources(session)
                    await session.commit()
            except Exception as e:
                logger.error(f"❌ Ошибка в мониторинге: {e}", exc_info=True)
                await asyncio.sleep(60)
            
            await self._smart_sleep(interval_minutes)
    
    async def _smart_sleep(self, base_interval_minutes: int):
        """Умное ожидание с учётом часов пик"""
        now = datetime.utcnow()
        hour = now.hour
        is_peak_hour = 13 <= hour <= 17
        
        interval = base_interval_minutes * 1 if is_peak_hour else base_interval_minutes
        logger.info(f"⏳ Следующая проверка через {interval} минут...")
        
        for _ in range(interval * 60):
            if not self.is_running:
                break
            await asyncio.sleep(1)
    
    async def stop(self):
        self.is_running = False
        logger.info("⏹️ Мониторинг остановлен")
    
    # ----------------------------------------------------------------------
    # 🔥 ПРОВЕРКА БЕЗОПАСНОСТИ ИСТОЧНИКОВ
    # ----------------------------------------------------------------------
    
    async def _check_source_security(self, source: ContentSource, session: AsyncSession) -> bool:
        """
        Проверяет безопасность источника.
        Возвращает False, если источник небезопасен и должен быть пропущен.
        """
        from core.security import URLSecurity
        
        logger.debug(f"🔒 Проверка безопасности для {source.source_global_id}")
        
        try:
            if source.source_type == "youtube":
                # Для YouTube проверяем username и feed_url
                if source.feed_url and not URLSecurity.is_allowed_youtube(source.feed_url):
                    logger.error(f"❌ YouTube источник {source.source_global_id} имеет небезопасный URL: {source.feed_url}")
                    source.is_active = False
                    await session.flush()
                    return False
                
                # Проверяем username на опасные символы
                if source.youtube_username:
                    dangerous_patterns = ['../', '..\\', '%2e', '%2f', ';', '|', '`', '$', '(', ')']
                    for pattern in dangerous_patterns:
                        if pattern in source.youtube_username.lower():
                            logger.error(f"❌ YouTube источник {source.source_global_id} имеет опасный username: {source.youtube_username}")
                            source.is_active = False
                            await session.flush()
                            return False
                
            elif source.source_type == "telegram":
                if source.telegram_username:
                    dangerous_patterns = ['../', '..\\', '%2e', '%2f', ';', '|', '`', '$', '(', ')']
                    for pattern in dangerous_patterns:
                        if pattern in source.telegram_username.lower():
                            logger.error(f"❌ Telegram источник {source.source_global_id} имеет опасный username: {source.telegram_username}")
                            source.is_active = False
                            await session.flush()
                            return False
                    
                    if len(source.telegram_username) < 3 or len(source.telegram_username) > 32:
                        logger.error(f"❌ Telegram источник {source.source_global_id} имеет некорректную длину username")
                        source.is_active = False
                        await session.flush()
                        return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке безопасности {source.source_global_id}: {e}")
            return False
    
    # ----------------------------------------------------------------------
    # 🔥 ПРОВЕРКА ВСЕХ ИСТОЧНИКОВ
    # ----------------------------------------------------------------------
    
    async def check_all_sources(self, session: AsyncSession):
        logger.info("🔍 Проверяю источники...")
        
        try:
            stmt = select(ContentSource)
            result = await session.execute(stmt)
            sources = result.scalars().all()
            
            logger.info(f"📊 Найдено источников: {len(sources)}")
            
            for source in sources:
                try:
                    if not await self._check_source_security(source, session):
                        logger.warning(f"⏭️ Пропускаю небезопасный источник {source.source_global_id}")
                        continue
                    
                    if not await self._should_check_source(source):
                        continue
                    
                    if source.source_type == 'telegram':
                        await self._check_telegram_source(source, session)
                    elif source.source_type == 'youtube':
                        await self.youtube_service.check_source(source, session)
                    else:
                        logger.warning(f"⚠️ Неизвестный тип источника: {source.source_type}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки источника {source.source_global_id}: {e}")
                    await self._update_source_error_stats(source.source_global_id)
                    await session.rollback()
            
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Критическая ошибка в check_all_sources: {e}")
            raise
    
    async def _should_check_source(self, source: ContentSource) -> bool:
        """
        Проверяет, пора ли проверять источник.
        Для YouTube интервал 30 минут, для Telegram 5 минут.
        """
        stats = self.source_stats.get(source.source_global_id, {})
        consecutive_errors = stats.get('consecutive_errors', 0)
        last_check = stats.get('last_check')
        
        if hasattr(source, 'is_active') and not source.is_active:
            logger.debug(f"⏸️ Источник {source.source_global_id} деактивирован")
            return False
        
        if consecutive_errors >= 3:
            if last_check and (datetime.utcnow() - last_check).total_seconds() < 3600:
                logger.debug(f"⏸️ Пропускаю {source.source_global_id} (3+ ошибок подряд)")
                return False
        
        # Определяем интервал в зависимости от типа источника
        if source.source_type == 'youtube':
            interval = 1800  # 30 минут для YouTube
        else:
            interval = 300   # 5 минут для Telegram
        
        if source.last_checked_timestamp:
            seconds_since = (datetime.utcnow() - source.last_checked_timestamp).total_seconds()
            if seconds_since < interval:
                logger.debug(f"⏸️ {source.source_global_id}: ещё рано (прошло {seconds_since:.0f}с, нужно {interval}с)")
                return False
        
        return True
    
    async def _update_source_error_stats(self, source_global_id: str):
        stats = self.source_stats.get(source_global_id, {})
        stats['consecutive_errors'] = stats.get('consecutive_errors', 0) + 1
        stats['last_check'] = datetime.utcnow()
        self.source_stats[source_global_id] = stats
    
    async def _reset_source_error_stats(self, source_global_id: str):
        if source_global_id in self.source_stats:
            self.source_stats[source_global_id]['consecutive_errors'] = 0
    
    # ----------------------------------------------------------------------
    # 🔥 ПРОВЕРКА TELEGRAM ИСТОЧНИКА
    # ----------------------------------------------------------------------

    async def _check_telegram_source(self, source: ContentSource, session: AsyncSession):
        """
        Проверить Telegram канал и отправить новые посты.
        """
        if not source.telegram_username:
            logger.warning(f"⚠️ Источник {source.source_global_id} не имеет telegram_username")
            return
        
        username = source.telegram_username
        source_name = f"@{username}"
        
        logger.info(f"🔍 Проверяю Telegram канал: {source_name}")
        logger.info(f"   📦 В БД last_successful_post_id = {source.last_successful_post_id}")
        
        try:
            from core.redis_client import get_cached_last_post, set_cached_last_post
            
            cached_id = await get_cached_last_post(username)
            logger.info(f"   📦 В Redis cached_id = {cached_id}")
            
            if source.last_successful_post_id:
                if cached_id != source.last_successful_post_id:
                    logger.warning(
                        f"⚠️ Redis устарел для @{username}: "
                        f"в Redis={cached_id}, в БД={source.last_successful_post_id}. Чиним..."
                    )
                    await set_cached_last_post(username, source.last_successful_post_id)
                    logger.info(f"✅ Redis обновлён: {source.last_successful_post_id}")
            
            if source.last_successful_post_id is None:
                logger.info(f"🆕 Первый запуск для {source_name}, новых постов нет (уже отправили при добавлении)")
                source.last_checked_timestamp = datetime.utcnow()
                await session.flush()
                await self._reset_source_error_stats(source.source_global_id)
                return
            
            logger.info(f"✅ В БД есть ID={source.last_successful_post_id}, проверяю новые посты...")
            
            last_post_id = await get_source_last_post_id(source, session, use_cache=True)
            logger.info(f"   🔍 last_post_id для проверки = {last_post_id}")
            
            assignments = await self._get_source_assignments(source.source_global_id, session)
            
            if not assignments:
                logger.debug(f"📭 Нет активных назначений для источника {source_name}")
                source.last_checked_timestamp = datetime.utcnow()
                await session.flush()
                await self._reset_source_error_stats(source.source_global_id)
                return
            
            logger.info(f"   📋 Найдено назначений: {len(assignments)}")
            
            new_posts = await get_telegram_posts(
                username, 
                str(last_post_id) if last_post_id else None,
                first_only=False
            )
            
            logger.info(f"   📬 Парсер вернул {len(new_posts)} постов")
            
            if not new_posts:
                logger.debug(f"📭 Нет новых постов в {source_name}")
                source.last_checked_timestamp = datetime.utcnow()
                await session.flush()
                await self._reset_source_error_stats(source.source_global_id)
                return
            
            logger.info(f"✅ Найдено {len(new_posts)} новых постов в {source_name}")
            
            # Сохраняем текущий last_post_id для проверок во время цикла
            current_last_id = source.last_successful_post_id
            last_successful_id = None  # Будет хранить ID последнего успешно обработанного поста
            
            for i, post in enumerate(new_posts, 1):
                post_id = post.get('post_id')
                logger.info(f"   📝 Обработка поста {i}/{len(new_posts)}: ID={post_id}")
                
                try:
                    # Передаём current_last_id в функцию обработки
                    await self._process_telegram_post(
                        post, 
                        source, 
                        assignments, 
                        session,
                        current_last_id  # ← передаём исходный last_id для проверок
                    )
                    
                    # Запоминаем последний успешно обработанный ID
                    if post_id:
                        last_successful_id = post_id
                    
                    # Пауза между постами (кроме последнего)
                    if i < len(new_posts):
                        await asyncio.sleep(2.0)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки поста {post_id}: {e}")
                    await session.rollback()
                    await asyncio.sleep(2.0)
                    continue
            
            # ✅ ОБНОВЛЯЕМ БД ТОЛЬКО ОДИН РАЗ - САМЫМ ПОСЛЕДНИМ УСПЕШНЫМ ID
            if last_successful_id:
                try:
                    last_id_int = int(last_successful_id)
                    logger.info(f"   💾 ФИНАЛЬНОЕ обновление last_post_id в БД: {last_id_int}")
                    await update_source_last_post_id(source, session, last_id_int)
                except (ValueError, TypeError) as e:
                    logger.error(f"   ❌ Ошибка конвертации финального ID {last_successful_id}: {e}")

            source.last_checked_timestamp = datetime.utcnow()
            await session.flush()
            await self._reset_source_error_stats(source.source_global_id)
            
            logger.info(f"✅ Обработано {len(new_posts)} постов из {source_name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в _check_telegram_source для {source_name}: {e}", exc_info=True)
            await session.rollback()
            raise

    # ----------------------------------------------------------------------
    # 🔥 ПОЛУЧЕНИЕ НАЗНАЧЕНИЙ
    # ----------------------------------------------------------------------
    
    async def _get_source_assignments(
        self, 
        source_global_id: str, 
        session: AsyncSession
    ) -> List[TopicSourceAssignment]:
        stmt = (
            select(TopicSourceAssignment)
            .join(
                SourceSubscription,
                SourceSubscription.subscription_id == TopicSourceAssignment.subscription_id
            )
            .join(
                GroupTopic, 
                GroupTopic.topic_identifier == TopicSourceAssignment.topic_identifier
            )
            .join(
                ManagedGroup,
                ManagedGroup.telegram_chat_id == GroupTopic.telegram_chat_id
            )
            .where(
                and_(
                    SourceSubscription.source_global_id == source_global_id,
                    GroupTopic.is_closed == False,
                    ManagedGroup.is_bot_active_in_group == True
                )
            )
            .options(
                selectinload(TopicSourceAssignment.topic),
                selectinload(TopicSourceAssignment.subscription)
            )
        )
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    # ----------------------------------------------------------------------
    # 🔥 ОБРАБОТКА TELEGRAM ПОСТА
    # ----------------------------------------------------------------------
    
    async def _process_telegram_post(
        self, 
        post: Dict, 
        source: ContentSource,
        assignments: List[TopicSourceAssignment],
        session: AsyncSession,
        current_last_id: Optional[int] = None
    ):
        """Обработать один Telegram пост"""
        post_id = post.get('post_id')
        if not post_id:
            return
        
        try:
            post_id_int = int(post_id)
        except:
            return
        
        post_key = f"{source.source_global_id}:{post_id_int}"
        if post_key in self._processed_posts:
            logger.warning(f"⚠️ Пост {post_id_int} уже обработан")
            return
        
        self._processed_posts.add(post_key)
        
        # Используем current_last_id для проверки, а не source.last_successful_post_id
        if current_last_id and post_id_int <= current_last_id:
            logger.debug(f"⏭️ Пропускаю старый пост {post_id_int} (<= {current_last_id})")
            return
        
        logger.info(f"📝 Новый пост {post_id_int} из {source.telegram_username}")
        
        media_items = post.get('media', [])
        logger.debug(f"📸 Медиа в посте: {len(media_items)} шт.")
        
        file_id = None
        
        if media_items and len(media_items) > 0:
            media = media_items[0]
            media_url = media.get('url')
            
            if media_url:
                logger.debug(f"🔍 Ищу file_id для source={source.source_global_id}, post_id={post_id}")
                
                stmt = select(CachedMedia).where(
                    CachedMedia.source_global_id == source.source_global_id,
                    CachedMedia.post_id == post_id
                )
                result = await session.execute(stmt)
                cached = result.scalar_one_or_none()
                
                if cached:
                    file_id = cached.file_id
                    logger.info(f"✅ Найден file_id в кеше: {file_id}")
                else:
                    logger.debug(f"❌ file_id НЕ НАЙДЕН в кеше")
        
        for assignment in assignments:
            try:
                if file_id:
                    await self._send_media_to_assignment(
                        post=post,
                        file_id=file_id,
                        assignment=assignment,
                        source=source
                    )
                else:
                    await self._send_text_to_assignment(post, assignment, source)
                
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"❌ Ошибка отправки поста {post_id_int}: {e}")

    # ----------------------------------------------------------------------
    # 🔥 ОТПРАВКА В ТЕМЫ
    # ----------------------------------------------------------------------


    async def _send_media_to_assignment(
        self,
        post: Dict,
        file_id: str,
        assignment: TopicSourceAssignment,
        source: ContentSource
    ):
        """Отправить медиа с file_id"""
        try:
            topic = assignment.topic
            
            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта или не существует: {assignment.topic_identifier}")
                return
            
            text = post.get('text', '').strip()
            
            # 🔥 ИСПРАВЛЕНО: используем channel_title для отображения
            if source.channel_title:
                source_name = f"{source.channel_title} | @{source.telegram_username}"
            else:
                source_name = f"@{source.telegram_username}"
            
            caption = f"<b>{source_name}</b>\n\n{text}"
            if len(caption) > 1024:
                caption = caption[:1021] + "..."
            
            logger.info(f"📤 Отправляю медиа в тему '{topic.topic_name}' (chat_id={topic.telegram_chat_id}, thread_id={topic.telegram_thread_id})")
            
            try:
                await self.bot.send_photo(
                    chat_id=topic.telegram_chat_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    message_thread_id=topic.telegram_thread_id
                )
                logger.info(f"✅ Медиа отправлено в тему '{topic.topic_name}'")
                return
                
            except Exception as photo_error:
                logger.warning(f"⚠️ Не удалось отправить как фото: {photo_error}")
                
                try:
                    await self.bot.send_document(
                        chat_id=topic.telegram_chat_id,
                        document=file_id,
                        caption=caption,
                        parse_mode="HTML",
                        message_thread_id=topic.telegram_thread_id
                    )
                    logger.info(f"✅ Документ отправлен в тему '{topic.topic_name}'")
                    return
                    
                except Exception as doc_error:
                    logger.error(f"❌ Не удалось отправить медиа: {doc_error}")
                    await self._send_text_to_assignment(post, assignment, source)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки медиа: {e}", exc_info=True)
            raise


    async def _send_text_to_assignment(
        self, 
        post: Dict, 
        assignment: TopicSourceAssignment,
        source: ContentSource
    ):
        """Отправить только текст"""
        try:
            topic = assignment.topic
            
            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта или не существует: {assignment.topic_identifier}")
                return
            
            message_text = self._format_telegram_post_message(post, source)
            
            logger.info(f"📤 Отправляю текст в тему '{topic.topic_name}' (chat_id={topic.telegram_chat_id}, thread_id={topic.telegram_thread_id})")
            
            await self._send_message_with_retry(
                chat_id=topic.telegram_chat_id,
                text=message_text,
                thread_id=topic.telegram_thread_id
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}", exc_info=True)
            raise


    async def _send_message_with_retry(
        self,
        chat_id: int,
        text: str,
        thread_id: Optional[int] = None,
        max_retries: int = 3
    ):
        """Отправить сообщение с повторными попытками и подробным логированием ошибок"""
        for attempt in range(max_retries):
            try:
                logger.info(f"📤 Попытка {attempt + 1}/{max_retries}: отправка в chat_id={chat_id}, thread_id={thread_id}")
                
                await self.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
                
                logger.info(f"✅ Сообщение успешно отправлено в chat_id={chat_id}, thread_id={thread_id}")
                return

            except Exception as e:
                error = str(e).lower()
                error_type = type(e).__name__
                
                logger.error(f"❌ Ошибка отправки (попытка {attempt + 1}): {error_type} - {e}")
                
                # ===== НОВАЯ ЛОГИКА ОБРАБОТКИ СПЕЦИФИЧЕСКИХ ОШИБОК =====
                
                # Если бота кикнули из группы или запретили отправку
                if "forbidden" in error or "bot was kicked" in error or "not enough rights" in error:
                    logger.error(f"👢 Бот потерял доступ к группе {chat_id}, помечаю неактивной")
                    
                    # Получаем группу из БД и обновляем
                    try:
                        from core.models import ManagedGroup
                        from sqlalchemy import select
                        
                        async with async_session() as cleanup_session:
                            stmt = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
                            result = await cleanup_session.execute(stmt)
                            group = result.scalar_one_or_none()
                            
                            if group:
                                group.is_bot_active_in_group = False
                                group.last_seen_at = datetime.utcnow()
                                await cleanup_session.commit()
                                logger.info(f"✅ Группа {chat_id} помечена как неактивная")
                    except Exception as db_error:
                        logger.error(f"❌ Не удалось обновить статус группы: {db_error}")
                    
                    return  # Прерываем отправку
                
                # Если тема удалена в Telegram
                elif "message thread not found" in error:
                    logger.error(f"❌ Тема {thread_id} не найдена в чате {chat_id}")
                    
                    # Помечаем тему как несуществующую
                    try:
                        from core.models import GroupTopic
                        from sqlalchemy import select
                        
                        topic_identifier = f"{chat_id}:{thread_id}" if thread_id else f"{chat_id}:0"
                        
                        async with async_session() as cleanup_session:
                            stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
                            result = await cleanup_session.execute(stmt)
                            topic = result.scalar_one_or_none()
                            
                            if topic:
                                topic.is_exists_in_tg = False
                                await cleanup_session.commit()
                                logger.info(f"✅ Тема {topic_identifier} помечена как удалённая")
                    except Exception as db_error:
                        logger.error(f"❌ Не удалось обновить статус темы: {db_error}")
                    
                    return  # Прерываем отправку
                
                # Стандартная обработка остальных ошибок
                elif "too many requests" in error or "flood" in error:
                    wait = 5 * (attempt + 1)
                    logger.warning(f"⏳ Flood control, жду {wait}с...")
                    await asyncio.sleep(wait)
                
                elif "chat not found" in error:
                    logger.error(f"❌ Чат {chat_id} не найден! Бот удалён из группы?")
                    return
                
                elif "message is too long" in error:
                    logger.warning(f"⚠️ Сообщение слишком длинное, обрезаю...")
                    text = text[:3000] + "...\n\n[сообщение обрезано]"
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error(f"❌ Не удалось отправить даже после обрезания")
                        return
                
                else:
                    if attempt < max_retries - 1:
                        wait = 2 * (attempt + 1)
                        logger.warning(f"⏳ Неизвестная ошибка, жду {wait}с...")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"❌ Все попытки исчерпаны: {e}")
                        return
                    


    def _format_telegram_post_message(self, post: Dict, source: ContentSource) -> str:
        """Форматирование текста Telegram поста"""
        text = post.get('text', '').strip()
        if not text:
            text = "📎 [Медиа-сообщение]"
        
        # 🔥 ИСПРАВЛЕНО: используем channel_title для отображения
        if source.channel_title:
            source_name = f"{source.channel_title} | @{source.telegram_username}"
        else:
            source_name = f"@{source.telegram_username}"
        
        timestamp = post.get('timestamp')
        time_str = ""
        if timestamp:
            try:
                time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M")
            except:
                pass
        
        message = f"<b>{source_name}</b>\n"
        if time_str:
            message += f"<i>{time_str}</i>\n\n"
        
        message += text
        
        if post.get('post_id') and source.telegram_username:
            message += f"\n\n<a href='https://t.me/{source.telegram_username}/{post['post_id']}'>🔗 Оригинал</a>"
        
        if len(message) > 4000:
            message = message[:3997] + "..."
        
        return message


    # ===== ПРОВЕРКА ГРУПП 2 РАЗА В ДЕНЬ =====

    async def check_groups_status(self, session: AsyncSession):
        """Проверить статус всех активных групп (доступны ли они)"""
        logger.info("🏢 Проверяю статус групп...")
        
        try:
            # Получаем все активные группы
            stmt = select(ManagedGroup).where(ManagedGroup.is_bot_active_in_group == True)
            result = await session.execute(stmt)
            groups = result.scalars().all()
            
            logger.info(f"📊 Найдено активных групп: {len(groups)}")
            
            for group in groups:
                try:
                    # Пробуем получить информацию о группе
                    await self.bot.get_chat(group.telegram_chat_id)
                    logger.debug(f"✅ Группа {group.telegram_chat_id} доступна")
                    
                except Exception as e:
                    error_text = str(e).lower()
                    
                    # Если группа не найдена - помечаем как неактивную
                    if "chat not found" in error_text or "group not found" in error_text:
                        logger.warning(f"🏚️ Группа {group.telegram_chat_id} не найдена (удалена?), помечаю неактивной")
                        group.is_bot_active_in_group = False
                        
                    elif "bot was kicked" in error_text or "forbidden" in error_text:
                        logger.warning(f"👢 Бот удалён из группы {group.telegram_chat_id}, помечаю неактивной")
                        group.is_bot_active_in_group = False
                        
                    else:
                        logger.error(f"❌ Ошибка при проверке группы {group.telegram_chat_id}: {e}")
            
            await session.commit()
            logger.info(f"✅ Проверка групп завершена, обновлено групп: {len(groups)}")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка при проверке групп: {e}")


    async def schedule_groups_check(self):
        """Запускать проверку групп 2 раза в день (каждые 12 часов)"""
        while self.is_running:
            try:
                async with async_session() as session:
                    await self.check_groups_status(session)
                
                # Ждём 12 часов до следующей проверки
                logger.info("⏳ Следующая проверка групп через 12 часов")
                for _ in range(12 * 3600):  # 12 часов в секундах
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в schedule_groups_check: {e}")
                await asyncio.sleep(3600)  # Если ошибка, ждём час и пробуем снова


# ----------------------------------------------------------------------
# 🔥 ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ----------------------------------------------------------------------

_monitoring_service = None


async def start_monitoring(bot, interval_minutes: int = 5):
    global _monitoring_service
    if _monitoring_service:
        logger.warning("⚠️ Мониторинг уже запущен")
        return
    
    _monitoring_service = MonitoringService(bot)
    asyncio.create_task(_monitoring_service.start(interval_minutes))
    logger.info(f"🎯 Задача мониторинга создана (интервал: {interval_minutes} минут)")


async def stop_monitoring():
    global _monitoring_service
    if _monitoring_service:
        await _monitoring_service.stop()
        _monitoring_service = None
    else:
        logger.warning("⚠️ Мониторинг не был запущен")
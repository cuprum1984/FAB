# core/services/monitoring/post_sender.py
"""
Отправка постов в темы (copy_message + fallback).
Версия: 6.7 — Copy Message + HTML форматирование + Inline кнопка
Изменения:
- Добавлен copy_message() как приоритет №1
- HTML санитизация для fallback режима
- InlineKeyboardButton "📎 Открыть оригинал"
- 3-уровневый fallback: copy_message → HTML текст → Plain text
"""
import asyncio
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

import aiohttp
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ContentSource, ManagedGroup, GroupTopic
from core.database import async_session
from core.utils.html_sanitizer import html_to_plain_text
from sqlalchemy import select

logger = logging.getLogger(__name__)


class PostSender:
    """
    Отправка постов в темы.
    Версия 6.7: copy_message + HTML + Inline кнопка.
    """

    def __init__(self, bot):
        self.bot = bot

        # ✅ КЭШ СТАТУСОВ ТЕМ (LRU-like, 5 минут)
        self._topic_cache: Dict[str, datetime] = {}
        self._group_cache: Dict[int, datetime] = {}
        self._cache_ttl = 300  # 5 минут

    def _is_topic_cached_inactive(self, topic_identifier: str) -> bool:
        """Проверить, есть ли тема в кэше неактивных."""
        if topic_identifier in self._topic_cache:
            last_check = self._topic_cache[topic_identifier]
            if (datetime.now(timezone.utc).replace(tzinfo=None) - last_check).total_seconds() < self._cache_ttl:
                return True
        return False

    def _is_group_cached_inactive(self, chat_id: int) -> bool:
        """Проверить, есть ли группа в кэше неактивных."""
        if chat_id in self._group_cache:
            last_check = self._group_cache[chat_id]
            if (datetime.now(timezone.utc).replace(tzinfo=None) - last_check).total_seconds() < self._cache_ttl:
                return True
        return False

    # ======================================================================
    # УНИВЕРСАЛЬНЫЙ МЕТОД (v6.7)
    # ======================================================================

    async def send_to_assignment(
        self,
        post: Dict,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ) -> bool:
        """
        Отправка поста:
        1. HTML текст + медиа по URL + кнопка
        2. Plain text + кнопка (последний fallback)
        """
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта: {assignment.topic_identifier}")
                return False

            # ПРИОРИТЕТ 1: HTML текст + медиа + кнопка
            success = await self._send_html_text_to_assignment(
                post=post,
                assignment=assignment,
                source=source,
                session=session,
                updated_topics=updated_topics
            )
            if success:
                return True

            # ПРИОРИТЕТ 2: Plain text + кнопка
            logger.warning(f"⚠️ HTML текст не сработал, fallback на plain text")
            return await self._send_plain_text_to_assignment(
                post=post,
                assignment=assignment,
                source=source,
                session=session,
                updated_topics=updated_topics
            )

        except Exception as e:
            logger.error(f"❌ Ошибка отправки поста: {e}", exc_info=False)
            return False

    # ======================================================================
    # COPY MESSAGE (оставлен на случай если когда-нибудь понадобится)
    # ======================================================================

    async def _copy_message_to_topic(
        self,
        post: Dict,
        source: ContentSource,
        assignment,
        updated_topics: Set
    ) -> bool:
        """
        Копировать сообщение из канала в тему.
        Работает только с публичными каналами.
        """
        try:
            topic = assignment.topic
            post_id = post.get('post_id')
            username = source.telegram_username

            if not post_id or not username:
                logger.debug(f"⏭️ Нет post_id или username для copy_message")
                return False

            logger.info(f"📋 Копирую пост {post_id} из @{username} в тему '{topic.topic_name}'")

            # Копируем сообщение (без метки "forwarded")
            await self.bot.copy_message(
                chat_id=topic.telegram_chat_id,
                from_chat_id=f"@{username}",
                message_id=int(post_id),
                message_thread_id=topic.telegram_thread_id
            )

            # ✅ Обновляем last_seen_at
            topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
            updated_topics.add(topic)

            logger.info(f"✅ Пост скопирован в тему '{topic.topic_name}'")
            return True

        except Exception as e:
            error_str = str(e).lower()
            from_chat_id = f"@{source.telegram_username}"
            post_id = post.get('post_id')
            chat_id = assignment.topic.telegram_chat_id
            thread_id = assignment.topic.telegram_thread_id

            # Если канал приватный или бот не имеет доступа
            if "chat not found" in error_str or "forbidden" in error_str:
                logger.warning(
                    f"⚠️ copy_message не сработал (приватный канал/нет доступа): {e}\n"
                    f"   from_chat_id={from_chat_id}, message_id={post_id}\n"
                    f"   chat_id={chat_id}, thread_id={thread_id}"
                )
            elif "message to copy not found" in error_str:
                logger.warning(
                    f"⚠️ copy_message: сообщение не найдено (post_id={post_id} в @{source.telegram_username})\n"
                    f"   Возможные причины:\n"
                    f"   • Пост удалён или скрыт\n"
                    f"   • Пост ещё не проиндексирован Telegram API\n"
                    f"   • Канал не публичный (нужен @username)\n"
                    f"   • from_chat_id={from_chat_id}, message_id={post_id}\n"
                    f"   • chat_id={chat_id}, thread_id={thread_id}\n"
                    f"   Полный текст ошибки: {type(e).__name__}: {e}",
                    exc_info=False
                )
            else:
                logger.warning(
                    f"⚠️ copy_message не сработал: {type(e).__name__}: {e}\n"
                    f"   from_chat_id={from_chat_id}, message_id={post_id}\n"
                    f"   chat_id={chat_id}, thread_id={thread_id}"
                )

            return False

    # ======================================================================
    # ПРИОРИТЕТ 2: HTML ТЕКСТ + МЕДИА ПО URL + КНОПКА
    # ======================================================================

    async def _send_html_text_to_assignment(
        self,
        post: Dict,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ) -> bool:
        """Отправить HTML текст с медиа по URL и кнопкой"""
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                return False

            # Форматируем сообщение
            message_text = self._format_telegram_post_message(post, source)
            keyboard = self._get_original_post_keyboard(post, source)

            # Проверяем медиа
            media_items = post.get('media', [])

            if media_items:
                # Сначала отправляем первое медиа, остальные — группой
                logger.info(f"📤 Отправляю медиа по URL в тему '{topic.topic_name}' ({len(media_items)} объектов)")
                success = await self._send_media_by_url(
                    chat_id=topic.telegram_chat_id,
                    thread_id=topic.telegram_thread_id,
                    media_items=media_items,
                    caption=message_text,
                    keyboard=keyboard,
                    post_url=post.get('url', '')
                )
            else:
                # Без медиа — только текст
                logger.info(f"📤 Отправляю HTML текст в тему '{topic.topic_name}'")
                success = await self._send_message_with_retry(
                    chat_id=topic.telegram_chat_id,
                    text=message_text,
                    thread_id=topic.telegram_thread_id,
                    keyboard=keyboard
                )

            if success:
                topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                updated_topics.add(topic)
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка отправки HTML текста: {e}", exc_info=False)
            return False

    async def _send_media_by_url(
        self,
        chat_id: int,
        thread_id: int,
        media_items: list,
        caption: str,
        keyboard,
        post_url: str
    ) -> bool:
        """
        Отправить медиа по URL (без скачивания в память).
        Скачивает во временный файл, отправляет, удаляет.
        """
        temp_path = None
        media_type = 'photo'

        try:
            main_media = media_items[0]
            media_type = main_media.get('type', 'photo')
            media_url = main_media.get('url', '')

            if not media_url:
                return await self._send_message_with_retry(
                    chat_id=chat_id,
                    text=caption,
                    thread_id=thread_id,
                    keyboard=keyboard
                )

            # ⚠️ Лимит Telegram: caption для медиа — макс. 1024 символа
            caption_suffix = ""
            if len(media_items) > 1:
                caption_suffix = f"\n\n📎 Ещё {len(media_items) - 1} медиафайл(ов) в оригинале"

            full_caption = caption + caption_suffix
            if len(full_caption) > 1024:
                full_caption = full_caption[:1021] + "..."

            logger.info(f"📎 Скачиваю {media_type} и отправляю: {media_url[:80]}... (caption: {len(full_caption)} символов)")

            # Скачиваем во временный файл
            temp_path = await self._download_media(media_url)
            if not temp_path:
                logger.warning(f"⚠️ Не удалось скачать {media_type}, fallback на текст")
                full_caption = caption + caption_suffix
                return await self._send_message_with_retry(
                    chat_id=chat_id,
                    text=full_caption,
                    thread_id=thread_id,
                    keyboard=keyboard
                )

            try:
                # Отправляем медиа из файла через FSInputFile (aiogram 3.x)
                if media_type == 'photo':
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=FSInputFile(temp_path),
                        caption=full_caption,
                        parse_mode="HTML",
                        message_thread_id=thread_id,
                        reply_markup=keyboard
                    )
                elif media_type == 'video':
                    await self.bot.send_video(
                        chat_id=chat_id,
                        video=FSInputFile(temp_path),
                        caption=full_caption,
                        parse_mode="HTML",
                        message_thread_id=thread_id,
                        reply_markup=keyboard
                    )
                elif media_type == 'video_note':
                    await self.bot.send_video_note(
                        chat_id=chat_id,
                        video_note=FSInputFile(temp_path),
                        message_thread_id=thread_id
                    )
                    await self._send_message_with_retry(
                        chat_id=chat_id,
                        text=full_caption,
                        thread_id=thread_id,
                        keyboard=keyboard
                    )
                elif media_type == 'animation':
                    await self.bot.send_animation(
                        chat_id=chat_id,
                        animation=FSInputFile(temp_path),
                        caption=full_caption,
                        parse_mode="HTML",
                        message_thread_id=thread_id,
                        reply_markup=keyboard
                    )
                elif media_type == 'audio':
                    await self.bot.send_audio(
                        chat_id=chat_id,
                        audio=FSInputFile(temp_path),
                        caption=full_caption,
                        parse_mode="HTML",
                        message_thread_id=thread_id,
                        reply_markup=keyboard
                    )
                elif media_type == 'document':
                    await self.bot.send_document(
                        chat_id=chat_id,
                        document=FSInputFile(temp_path),
                        caption=full_caption,
                        parse_mode="HTML",
                        message_thread_id=thread_id,
                        reply_markup=keyboard
                    )
                else:
                    logger.warning(f"⚠️ Неизвестный тип медиа: {media_type}")
                    return await self._send_message_with_retry(
                        chat_id=chat_id,
                        text=caption,
                        thread_id=thread_id,
                        keyboard=keyboard
                    )

                logger.info(f"✅ Медиа успешно отправлено ({media_type}, {len(media_items)} файлов)")
                return True

            finally:
                # Всегда удаляем временный файл
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                        logger.debug(f"🗑️ Удалён временный файл: {temp_path}")
                    except OSError:
                        pass

        except Exception as e:
            error_str = str(e).lower()

            # Если ошибка парсинга HTML — fallback на plain text
            if "can't parse entities" in error_str or "bad request" in error_str:
                logger.warning(f"⚠️ Ошибка парсинга HTML в медиа, fallback на plain text")
                # Удаляем теги, оставляем текст
                safe_caption = html_to_plain_text(full_caption)
                try:
                    if temp_path and os.path.exists(temp_path):
                        if 'photo' in error_str or media_type == 'photo':
                            await self.bot.send_photo(
                                chat_id=chat_id,
                                photo=FSInputFile(temp_path),
                                caption=safe_caption,
                                message_thread_id=thread_id,
                                reply_markup=keyboard
                            )
                        else:
                            await self.bot.send_document(
                                chat_id=chat_id,
                                document=FSInputFile(temp_path),
                                caption=safe_caption,
                                message_thread_id=thread_id,
                                reply_markup=keyboard
                            )
                        return True
                    else:
                        return await self._send_message_with_retry(
                            chat_id=chat_id,
                            text=safe_caption,
                            thread_id=thread_id,
                            keyboard=keyboard
                        )
                except Exception as e2:
                    logger.error(f"❌ Ошибка отправки медиа: {e2}")
                    return False

            logger.error(f"❌ Ошибка отправки медиа ({media_type}): {e}", exc_info=False)
            return False

    async def _download_media(self, url: str) -> Optional[str]:
        """
        Скачать медиа во временный файл.
        Возвращает путь к файлу или None при ошибке.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://t.me/',
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.error(f"❌ HTTP {resp.status} при скачивании {url}")
                        return None

                    # Определяем расширение
                    content_type = resp.content_type or ''
                    ext_map = {
                        'image/jpeg': '.jpg',
                        'image/png': '.png',
                        'image/webp': '.webp',
                        'image/gif': '.gif',
                        'video/mp4': '.mp4',
                        'audio/mpeg': '.mp3',
                        'audio/ogg': '.ogg',
                        'application/pdf': '.pdf',
                        'application/zip': '.zip',
                    }
                    ext = ext_map.get(content_type, '')

                    # Создаём временный файл
                    fd, temp_path = tempfile.mkstemp(suffix=ext, prefix='aggry_media_')
                    os.close(fd)

                    # Скачиваем чанками (не в память)
                    with open(temp_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            f.write(chunk)

                    file_size = os.path.getsize(temp_path)
                    logger.debug(f"📥 Скачано: {file_size / 1024:.0f} KB → {temp_path}")
                    return temp_path

        except asyncio.TimeoutError:
            logger.error(f"⏱️ Таймаут скачивания: {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания {url}: {e}", exc_info=False)
            return None

    # ======================================================================
    # ПРИОРИТЕТ 3: PLAIN TEXT + КНОПКА
    # ======================================================================

    async def _send_plain_text_to_assignment(
        self,
        post: Dict,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ) -> bool:
        """Отправить plain текст с кнопкой (последний fallback)"""
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                return False

            # Форматируем plain текст
            message_text = self._format_telegram_post_message(post, source)

            # Удаляем HTML-теги, оставляем текст
            safe_text = html_to_plain_text(message_text)

            keyboard = self._get_original_post_keyboard(post, source)

            logger.info(f"📤 Отправляю plain текст в тему '{topic.topic_name}'")

            await self.bot.send_message(
                chat_id=topic.telegram_chat_id,
                message_thread_id=topic.telegram_thread_id,
                text=safe_text,
                disable_web_page_preview=True,
                reply_markup=keyboard
            )

            topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
            updated_topics.add(topic)

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки plain текста: {e}", exc_info=False)
            return False

    # ======================================================================
    # КЛАВИАТУРА
    # ======================================================================

    def _get_original_post_keyboard(self, post: Dict, source: ContentSource) -> Optional[InlineKeyboardMarkup]:
        """Создать InlineKeyboardButton на оригинал поста"""
        post_id = post.get('post_id')
        username = source.telegram_username

        if not post_id or not username:
            return None

        url = f"https://t.me/{username}/{post_id}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📎 Открыть оригинал", url=url)]
        ])

        return keyboard

    # ======================================================================
    # СТАРЫЕ МЕТОДЫ (для обратной совместимости, если ещё используются)
    # ======================================================================

    async def send_media_to_assignment(
        self,
        post: Dict,
        file_id: str,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ):
        """
        Отправить медиа с file_id.
        updated_topics: множество topic_id для последующего bulk update
        """
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта или не существует: {assignment.topic_identifier}")
                return False

            # ✅ ПРОВЕРКА КЭША
            topic_key = f"{topic.telegram_chat_id}:{topic.telegram_thread_id}"
            if self._is_topic_cached_inactive(topic_key):
                logger.debug(f"⏭️ Тема {topic_key} в кэше неактивных, пропускаем")
                return False

            text = post.get('text', '').strip()

            if source.channel_title:
                source_name = f"{source.channel_title} | @{source.telegram_username}"
            else:
                source_name = f"@{source.telegram_username}"

            caption = f"<b>{source_name}</b>\n\n{text}"
            if len(caption) > 1024:
                caption = caption[:1021] + "..."

            logger.info(f"📤 Отправляю медиа в тему '{topic.topic_name}' (chat_id={topic.telegram_chat_id}, thread_id={topic.telegram_thread_id})")

            success = False

            # Попытка отправить как фото
            try:
                await self.bot.send_photo(
                    chat_id=topic.telegram_chat_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    message_thread_id=topic.telegram_thread_id
                )
                logger.info(f"✅ Медиа отправлено в тему '{topic.topic_name}'")
                success = True

            except Exception as photo_error:
                logger.warning(f"⚠️ Не удалось отправить как фото: {photo_error}")

                # Попытка отправить как документ
                try:
                    await self.bot.send_document(
                        chat_id=topic.telegram_chat_id,
                        document=file_id,
                        caption=caption,
                        parse_mode="HTML",
                        message_thread_id=topic.telegram_thread_id
                    )
                    logger.info(f"✅ Документ отправлен в тему '{topic.topic_name}'")
                    success = True

                except Exception as doc_error:
                    logger.error(f"❌ Не удалось отправить медиа: {doc_error}")
                    # Пробуем отправить текст
                    success = await self._send_text_only(post, assignment, source, session, updated_topics)

            # ✅ ОБНОВЛЯЕМ last_seen_at (только标记, без flush!)
            if success:
                topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                updated_topics.add(topic)  # Добавляем в множество для bulk update
                return True

            return False

        except Exception as e:
            # ✅ ИЗОЛЯЦИЯ ОШИБОК — не прерываем поток, логируем
            logger.error(f"❌ Ошибка отправки медиа: {e}", exc_info=False)  # exc_info=False для краткости
            return False

    async def _send_text_only(
        self,
        post: Dict,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ) -> bool:
        """Отправить только текст (вспомогательный метод)"""
        try:
            topic = assignment.topic
            if not topic or topic.is_closed:
                return False

            message_text = self._format_telegram_post_message(post, source)

            success = await self._send_message_with_retry(
                chat_id=topic.telegram_chat_id,
                text=message_text,
                thread_id=topic.telegram_thread_id
            )

            if success:
                topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                updated_topics.add(topic)
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}", exc_info=False)
            return False

    async def send_text_to_assignment(
        self,
        post: Dict,
        assignment,
        source: ContentSource,
        session: AsyncSession,
        updated_topics: Set
    ):
        """
        Отправить только текст.
        updated_topics: множество topic_id для последующего bulk update
        """
        try:
            topic = assignment.topic

            if not topic or topic.is_closed:
                logger.warning(f"⚠️ Тема закрыта или не существует: {assignment.topic_identifier}")
                return False

            # ✅ ПРОВЕРКА КЭША
            topic_key = f"{topic.telegram_chat_id}:{topic.telegram_thread_id}"
            if self._is_topic_cached_inactive(topic_key):
                logger.debug(f"⏭️ Тема {topic_key} в кэше неактивных, пропускаем")
                return False

            message_text = self._format_telegram_post_message(post, source)

            logger.info(f"📤 Отправляю текст в тему '{topic.topic_name}' (chat_id={topic.telegram_chat_id}, thread_id={topic.telegram_thread_id})")

            success = await self._send_message_with_retry(
                chat_id=topic.telegram_chat_id,
                text=message_text,
                thread_id=topic.telegram_thread_id
            )

            # ✅ ОБНОВЛЯЕМ last_seen_at (только标记, без flush!)
            if success:
                topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                updated_topics.add(topic)  # Добавляем в множество для bulk update
                return True

            return False

        except Exception as e:
            # ✅ ИЗОЛЯЦИЯ ОШИБОК — не прерываем поток
            logger.error(f"❌ Ошибка отправки текста: {e}", exc_info=False)
            return False

    # ======================================================================
    # ОБЩИЕ МЕТОДЫ
    # ======================================================================

    async def _send_message_with_retry(
        self,
        chat_id: int,
        text: str,
        thread_id: Optional[int] = None,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        max_retries: int = 3
    ) -> bool:
        """Отправить сообщение с повторными попытками. Возвращает True при успехе."""

        for attempt in range(max_retries):
            try:
                logger.info(f"📤 Попытка {attempt + 1}/{max_retries}: отправка в chat_id={chat_id}, thread_id={thread_id}")

                await self.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,  # ✅ Отключаем превью
                    reply_markup=keyboard  # ✅ Добавляем клавиатуру
                )

                logger.info(f"✅ Сообщение успешно отправлено в chat_id={chat_id}, thread_id={thread_id}")
                return True

            except Exception as e:
                error = str(e).lower()
                error_type = type(e).__name__

                logger.error(f"❌ Ошибка отправки (попытка {attempt + 1}): {error_type} - {e}")

                # Если бота кикнули из группы или запретили отправку
                if "forbidden" in error or "bot was kicked" in error or "not enough rights" in error:
                    logger.error(f"👢 Бот потерял доступ к группе {chat_id}")

                    # ✅ КЭШИРУЕМ неактивную группу
                    self._group_cache[chat_id] = datetime.now(timezone.utc).replace(tzinfo=None)

                    # ✅ ОТДЕЛЬНАЯ СЕССИЯ для cleanup (не конфликтует с основной)
                    await self._mark_group_inactive(chat_id)
                    return False

                # Если тема удалена в Telegram
                elif "message thread not found" in error:
                    logger.error(f"❌ Тема {thread_id} не найдена в чате {chat_id}")

                    # ✅ КЭШИРУЕМ удалённую тему
                    topic_key = f"{chat_id}:{thread_id}"
                    self._topic_cache[topic_key] = datetime.now(timezone.utc).replace(tzinfo=None)

                    # ✅ ОТДЕЛЬНАЯ СЕССИЯ для cleanup
                    await self._mark_topic_deleted(chat_id, thread_id)
                    return False

                # Flood control
                elif "too many requests" in error or "flood" in error:
                    wait = 5 * (attempt + 1)
                    logger.warning(f"⏳ Flood control, жду {wait}с...")
                    await asyncio.sleep(wait)

                # Чат не найден
                elif "chat not found" in error:
                    logger.error(f"❌ Чат {chat_id} не найден!")
                    self._group_cache[chat_id] = datetime.now(timezone.utc).replace(tzinfo=None)
                    return False

                # Если ошибка парсинга HTML — fallback на plain text
                elif "can't parse entities" in error or "bad request" in error:
                    logger.warning(f"⚠️ Ошибка парсинга HTML, fallback на plain text")

                    safe_text = html_to_plain_text(text)

                    await self.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=thread_id,
                        text=safe_text,
                        disable_web_page_preview=True,
                        reply_markup=keyboard
                    )
                    return True

                # Сообщение слишком длинное
                elif "message is too long" in error:
                    logger.warning(f"⚠️ Сообщение слишком длинное, обрезаю...")
                    text = text[:3000] + "...\n\n[сообщение обрезано]"
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error(f"❌ Не удалось отправить даже после обрезания")
                        return False

                # Остальные ошибки
                else:
                    if attempt < max_retries - 1:
                        wait = 2 * (attempt + 1)
                        logger.warning(f"⏳ Неизвестная ошибка, жду {wait}с...")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"❌ Все попытки исчерпаны: {e}")
                        return False

        return False

    # ----------------------------------------------------------------------
    # ✅ CLEANUP МЕТОДЫ С ОТДЕЛЬНЫМИ СЕССИЯМИ
    # ----------------------------------------------------------------------

    async def _mark_group_inactive(self, chat_id: int):
        """Пометить группу как неактивную (отдельная сессия)"""
        try:
            async with async_session() as cleanup_session:
                stmt = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
                result = await cleanup_session.execute(stmt)
                group = result.scalar_one_or_none()

                if group:
                    group.is_bot_active_in_group = False
                    group.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    await cleanup_session.commit()
                    logger.info(f"✅ Группа {chat_id} помечена как неактивная")
        except Exception as db_error:
            logger.error(f"❌ Не удалось обновить статус группы: {db_error}")

    async def _mark_topic_deleted(self, chat_id: int, thread_id: int):
        """Пометить тему как удалённую (отдельная сессия)"""
        try:
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

    def _format_telegram_post_message(self, post: Dict, source: ContentSource) -> str:
        """Форматирование текста Telegram поста (ссылка убрана — теперь в кнопке)"""
        text = post.get('text', '').strip()
        if not text:
            text = "📎 [Медиа-сообщение]"

        if source.channel_title:
            source_name = f"{source.channel_title} | @{source.telegram_username}"
        else:
            source_name = f"@{source.telegram_username}"

        timestamp = post.get('timestamp')
        time_str = ""
        if timestamp:
            try:
                time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M")
            except Exception:
                pass

        message = f"<b>{source_name}</b>\n"
        if time_str:
            message += f"<i>{time_str}</i>\n\n"

        message += text

        # ❌ УБРАНО: Ссылка на оригинал (теперь в кнопке)

        if len(message) > 4000:
            message = message[:3997] + "..."

        return message

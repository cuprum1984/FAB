# core/services/monitoring/telegram_monitor.py
"""
Проверка Telegram каналов и отправка постов.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.settings import settings
from core.models import ContentSource, CachedMedia
from core.parser.telegram_posts import get_new_posts as get_telegram_posts
from core.redis_client import get_cached_last_post, set_cached_last_post
from core.services.destination_service import (
    get_source_last_post_id,
    update_source_last_post_id,
)

logger = logging.getLogger(__name__)


class TelegramMonitor:
    """Мониторинг Telegram каналов."""

    def __init__(self, bot, monitoring_service):
        self.bot = bot
        self.monitoring = monitoring_service

    async def check_telegram_source(self, source: ContentSource, session: AsyncSession, downtime_seconds: float = 0):
        """
        Проверить Telegram канал и отправить новые посты.
        downtime_seconds: время простоя в секундах (0 если простоя нет)
        """
        if not source.telegram_username:
            logger.warning(f"⚠️ Источник {source.source_global_id} не имеет telegram_username")
            return

        username = source.telegram_username
        source_name = f"@{username}"

        logger.info(f"🔍 Проверяю Telegram канал: {source_name}")
        logger.info(f"   📦 В БД last_successful_post_id = {source.last_successful_post_id}")

        try:
            cached_id = await get_cached_last_post(username)
            logger.info(f"   📦 В Redis cached_id = {cached_id}")

            # ===== СИНХРОНИЗАЦИЯ БД И REDIS =====
            if source.last_successful_post_id is None and cached_id is not None:
                # Redis есть, БД пустая — восстанавливаем из Redis
                logger.info(f"🔄 Восстанавливаю last_successful_post_id из Redis: {cached_id}")
                source.last_successful_post_id = cached_id

            elif source.last_successful_post_id is not None and cached_id is None:
                # БД есть, Redis пустой — восстанавливаем из БД
                logger.info(f"🔄 Восстанавливаю Redis из БД: {source.last_successful_post_id}")
                await set_cached_last_post(username, source.last_successful_post_id)

            elif source.last_successful_post_id is not None and cached_id is not None:
                # Оба есть, проверяем расхождения
                if cached_id != source.last_successful_post_id:
                    logger.warning(
                        f"⚠️ Расхождение Redis/БД для @{username}: "
                        f"Redis={cached_id}, БД={source.last_successful_post_id}. Используем БД..."
                    )
                    await set_cached_last_post(username, source.last_successful_post_id)
                    logger.info(f"✅ Redis обновлён: {source.last_successful_post_id}")

            # ===== ПЕРВЫЙ ЗАПУСК: ни БД ни Redis не содержат ID =====
            if source.last_successful_post_id is None:
                # ПЕРВЫЙ ЗАПУСК: нужно получить последний пост и сохранить его ID
                logger.info(f"🆕 Первый запуск для {source_name}, получаю последний пост...")

                # Получаем последний пост (только один)
                new_posts = await get_telegram_posts(
                    username,
                    last_post_id=None,  # Получаем все посты
                    first_only=True     # Но берём только последний
                )

                if new_posts:
                    last_post = new_posts[-1]  # Берём самый новый
                    last_post_id = last_post.get('post_id')

                    if last_post_id:
                        try:
                            last_post_id_int = int(last_post_id)
                            logger.info(f"✅ Получен последний пост ID={last_post_id_int} для @{username}")

                            # Сохраняем в БД и Redis
                            source.last_successful_post_id = last_post_id_int
                            source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                            await set_cached_last_post(username, last_post_id_int)

                            await self.monitoring._reset_source_error_stats(source.source_global_id)

                            logger.info(f"💾 last_successful_post_id сохранён: {last_post_id_int}")
                            return  # Новые посты не отправляем (уже отправлены при добавлении)

                        except (ValueError, TypeError) as e:
                            logger.error(f"❌ Ошибка конвертации post_id {last_post_id}: {e}")
                    else:
                        logger.warning(f"⚠️ Пост найден, но post_id отсутствует")
                else:
                    logger.warning(f"⚠️ Не удалось получить посты из @{username}")

                # Если не удалось получить посты, всё равно обновляем timestamp
                source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                await self.monitoring._reset_source_error_stats(source.source_global_id)
                return

            logger.info(f"✅ В БД есть ID={source.last_successful_post_id}, проверяю новые посты...")

            last_post_id = await get_source_last_post_id(source, session, use_cache=True)
            logger.info(f"   🔍 last_post_id для проверки = {last_post_id}")

            assignments = await self.monitoring._get_source_assignments(source.source_global_id, session)

            if not assignments:
                logger.debug(f"📭 Нет активных назначений для источника {source_name}")
                source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                await self.monitoring._reset_source_error_stats(source.source_global_id)
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
                source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                await self.monitoring._reset_source_error_stats(source.source_global_id)
                return

            logger.info(f"✅ Найдено {len(new_posts)} новых постов в {source_name}")

            # ✅ ЗАЩИТА ОТ СПАМА ПОСЛЕ ПРОСТОЯ
            if downtime_seconds > 0:
                max_posts = settings.DOWNTIME_MAX_POSTS
                original_count = len(new_posts)

                if len(new_posts) > max_posts:
                    # Оставляем только последние N постов
                    new_posts = new_posts[-max_posts:]
                    logger.warning(
                        f"⚠️ ПРОСТОЙ: пропущено {original_count - max_posts} старых постов, "
                        f"отправлено только {len(new_posts)} последних"
                    )

            # ✅ ОПТИМИЗАЦИЯ: пакетная загрузка file_id для всех постов
            post_ids = [p['post_id'] for p in new_posts if p.get('post_id')]
            cached_media_map = {}

            if post_ids:
                logger.debug(f"📦 Пакетная загрузка file_id для {len(post_ids)} постов...")
                stmt = select(CachedMedia).where(
                    CachedMedia.source_global_id == source.source_global_id,
                    CachedMedia.post_id.in_(post_ids)
                )
                result = await session.execute(stmt)
                cached_media_list = result.scalars().all()
                cached_media_map = {cm.post_id: cm.file_id for cm in cached_media_list}
                logger.info(f"✅ Загружено {len(cached_media_map)} file_id из кеша")

            # Сохраняем текущий last_post_id для проверок во время цикла
            current_last_id = source.last_successful_post_id
            last_successful_id = None

            for i, post in enumerate(new_posts, 1):
                post_id = post.get('post_id')
                logger.info(f"   📝 Обработка поста {i}/{len(new_posts)}: ID={post_id}")

                try:
                    # ✅ Передаём file_id из кеша
                    file_id = cached_media_map.get(post_id)

                    await self._process_telegram_post(
                        post=post,
                        source=source,
                        assignments=assignments,
                        session=session,
                        current_last_id=current_last_id,
                        cached_file_id=file_id
                    )

                    if post_id:
                        last_successful_id = post_id

                except Exception as e:
                    logger.error(f"❌ Ошибка обработки поста {post_id}: {e}")
                    # Не делаем rollback в цикле — продолжаем обработку
                    await asyncio.sleep(2.0)
                    continue

                if i < len(new_posts):
                    await asyncio.sleep(2.0)

            if last_successful_id:
                try:
                    last_id_int = int(last_successful_id)
                    logger.info(f"   💾 ФИНАЛЬНОЕ обновление last_post_id в БД: {last_id_int}")
                    await update_source_last_post_id(source, session, last_id_int)
                except (ValueError, TypeError) as e:
                    logger.error(f"   ❌ Ошибка конвертации финального ID {last_successful_id}: {e}")

            source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            await self.monitoring._reset_source_error_stats(source.source_global_id)

            # ✅ ФИКСАЦИЯ изменений в БД
            await session.commit()

            logger.info(f"✅ Обработано {len(new_posts)} постов из {source_name}")

        except Exception as e:
            logger.error(f"❌ Ошибка в _check_telegram_source для {source_name}: {e}", exc_info=True)
            # Не делаем rollback и не пробрасываем ошибку — это делается в check_all_sources

    async def _process_telegram_post(
        self,
        post: Dict,
        source: ContentSource,
        assignments: List,
        session: AsyncSession,
        current_last_id: Optional[int] = None,
        cached_file_id: Optional[str] = None
    ):
        """Обработать один Telegram пост"""
        from core.services.monitoring.post_sender import PostSender

        post_id = post.get('post_id')
        if not post_id:
            return

        try:
            post_id_int = int(post_id)
        except:
            return

        post_key = f"{source.source_global_id}:{post_id_int}"
        if post_key in self.monitoring._processed_posts:
            logger.warning(f"⚠️ Пост {post_id_int} уже обработан")
            return

        self.monitoring._processed_posts.add(post_key)

        if current_last_id and post_id_int <= current_last_id:
            logger.debug(f"⏭️ Пропускаю старый пост {post_id_int} (<= {current_last_id})")
            return

        logger.info(f"📝 Новый пост {post_id_int} из {source.telegram_username}")

        # ✅ Используем file_id из кеша (передан извне)
        file_id = cached_file_id

        if file_id:
            logger.info(f"✅ Используем file_id из кеша: {file_id}")
        else:
            logger.debug(f"❌ file_id НЕ НАЙДЕН в кеше")

        post_sender = PostSender(self.bot)

        for assignment in assignments:
            try:
                if file_id:
                    await post_sender.send_media_to_assignment(
                        post=post,
                        file_id=file_id,
                        assignment=assignment,
                        source=source,
                        session=session
                    )
                else:
                    await post_sender.send_text_to_assignment(
                        post=post,
                        assignment=assignment,
                        source=source,
                        session=session
                    )

                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"❌ Ошибка отправки поста {post_id_int}: {e}")


# Импорты в конце для избежания циклических зависимостей
from sqlalchemy import select

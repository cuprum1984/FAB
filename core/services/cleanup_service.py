# core/services/cleanup_service.py
"""
Сервис ежедневной очистки данных.
Запускается раз в сутки через scheduler.
Версия: 1.2 (22 февраля 2026)
Изменения:
- Добавлены подробные принты удаляемых объектов
- Каждый метод теперь выводит список того, что удалил
- Добавлен принудительный вывод в консоль (console_print)
"""
import logging
import sys
from datetime import datetime, timedelta
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    TelegramAccount,
    ManagedGroup,
    ContentSource,
    SourceSubscription,
    CachedMedia,
    UserCachedMedia,
    GroupTopic,
    TopicSourceAssignment
)
from core.database import async_session

logger = logging.getLogger(__name__)

# 🔥 Функция для принудительного вывода в консоль
def console_print(*args, **kwargs):
    """Принудительный вывод в консоль, минуя логирование"""
    print(*args, **kwargs)
    sys.stdout.flush()  # Принудительный сброс буфера


class CleanupService:
    """Сервис для ежедневной очистки устаревших данных."""
    
    async def run_cleanup(self):
        """Точка входа - запуск всех процедур очистки."""
        msg = "🧹 Запуск ежедневной очистки данных..."
        logger.info(msg)
        console_print(msg)
        
        try:
            async with async_session() as session:
                await self._cleanup_gdpr(session)
                await self._cleanup_dead_groups(session)
                await self._cleanup_orphan_sources(session)
                await self._cleanup_expired_media(session)
                await self._cleanup_orphan_topics(session)
                await session.commit()
                
            msg = "✅ Ежедневная очистка успешно завершена"
            logger.info(msg)
            console_print(msg)
            
        except Exception as e:
            error_msg = f"❌ Критическая ошибка при очистке данных: {e}"
            logger.error(error_msg, exc_info=True)
            console_print(error_msg)
    
    async def _cleanup_gdpr(self, session: AsyncSession):
        """
        Удалить пользователей, заблокировавших бота >30 дней назад.
        
        Условия:
        - is_bot_blocked = True
        - last_activity < 30 дней назад
        """
        msg = "🔍 Проверка пользователей для GDPR очистки..."
        logger.info(msg)
        console_print(msg)
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Находим пользователей для удаления
            stmt = select(TelegramAccount).where(
                and_(
                    TelegramAccount.is_bot_blocked == True,
                    TelegramAccount.last_activity < cutoff_date
                )
            )
            result = await session.execute(stmt)
            users_to_delete = result.scalars().all()
            
            if not users_to_delete:
                msg = "✅ Нет пользователей для GDPR очистки"
                logger.info(msg)
                console_print(msg)
                return
            
            msg = f"📊 Найдено {len(users_to_delete)} пользователей для удаления:"
            logger.info(msg)
            console_print(msg)
            
            # Удаляем пользователей с подробной информацией
            for user in users_to_delete:
                user_info = f"ID: {user.telegram_account_id}"
                if user.telegram_username:
                    user_info += f", @{user.telegram_username}"
                if user.telegram_first_name:
                    user_info += f", {user.telegram_first_name}"
                
                log_msg = f"   🗑️ Удаляется пользователь: {user_info}"
                logger.info(log_msg)
                console_print(log_msg)
                
                logger.info(f"      • Заблокирован: {user.is_bot_blocked}")
                logger.info(f"      • Последняя активность: {user.last_activity}")
                logger.info(f"      • Зарегистрирован: {user.registration_timestamp}")
                
                await session.delete(user)
            
            msg = f"✅ GDPR очистка завершена: удалено {len(users_to_delete)} пользователей"
            logger.info(msg)
            console_print(msg)
            
        except Exception as e:
            error_msg = f"❌ Ошибка при GDPR очистке: {e}"
            logger.error(error_msg)
            console_print(error_msg)
            raise
    
    async def _cleanup_dead_groups(self, session: AsyncSession):
        """
        Удалить неактивные группы (>90 дней).
        
        Условия:
        - is_bot_active_in_group = False
        - last_seen_at < 90 дней назад
        """
        msg = "🔍 Проверка неактивных групп..."
        logger.info(msg)
        console_print(msg)
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            # Находим группы для удаления
            stmt = select(ManagedGroup).where(
                and_(
                    ManagedGroup.is_bot_active_in_group == False,
                    ManagedGroup.last_seen_at < cutoff_date
                )
            )
            result = await session.execute(stmt)
            groups_to_delete = result.scalars().all()
            
            if not groups_to_delete:
                msg = "✅ Нет неактивных групп для удаления"
                logger.info(msg)
                console_print(msg)
                return
            
            msg = f"📊 Найдено {len(groups_to_delete)} неактивных групп:"
            logger.info(msg)
            console_print(msg)
            
            # Удаляем группы
            for group in groups_to_delete:
                log_msg = f"   🗑️ Удаляется группа:"
                logger.info(log_msg)
                console_print(log_msg)
                
                logger.info(f"      • ID: {group.telegram_chat_id}")
                logger.info(f"      • Название: {group.telegram_chat_title or 'Без названия'}")
                logger.info(f"      • Тип: {group.chat_type}")
                logger.info(f"      • Добавлена: {group.bot_added_timestamp}")
                logger.info(f"      • Последняя активность: {group.last_seen_at}")
                logger.info(f"      • Статус: {'Активна' if group.is_bot_active_in_group else 'Неактивна'}")
                
                await session.delete(group)
            
            msg = f"✅ Очистка групп завершена: удалено {len(groups_to_delete)} групп"
            logger.info(msg)
            console_print(msg)
            
        except Exception as e:
            error_msg = f"❌ Ошибка при очистке групп: {e}"
            logger.error(error_msg)
            console_print(error_msg)
            raise
    
    async def _cleanup_orphan_sources(self, session: AsyncSession):
        """
        Удалить источники без подписок.
        
        Условия:
        - нет записей в source_subscriptions с этим source_global_id
        - источник создан >0 дней назад (сразу)
        """
        msg = "🔍 Проверка источников без подписок..."
        logger.info(msg)
        console_print(msg)
        
        try:
            # Находим все source_global_id, у которых есть подписки
            subquery = select(SourceSubscription.source_global_id).distinct()
            subscribed_sources = await session.execute(subquery)
            subscribed_ids = {row[0] for row in subscribed_sources if row[0]}
            
            # Находим все источники
            stmt = select(ContentSource)
            result = await session.execute(stmt)
            all_sources = result.scalars().all()
            
            orphan_sources = []
            cutoff_date = datetime.utcnow() - timedelta(days=0)  # Сразу удаляем
            
            for source in all_sources:
                if source.source_global_id not in subscribed_ids:
                    # Проверяем возраст источника
                    if source.created_timestamp < cutoff_date:
                        orphan_sources.append(source)
            
            if not orphan_sources:
                msg = "✅ Нет источников-сирот для удаления"
                logger.info(msg)
                console_print(msg)
                return
            
            msg = f"📊 Найдено {len(orphan_sources)} источников без подписок:"
            logger.info(msg)
            console_print(msg)
            
            # Удаляем источники
            for source in orphan_sources:
                source_info = f"ID: {source.source_global_id}"
                if source.source_type == "telegram" and source.telegram_username:
                    source_info += f", @{source.telegram_username}"
                elif source.source_type == "youtube" and source.youtube_username:
                    source_info += f", YouTube: {source.youtube_username}"
                
                log_msg = f"   🗑️ Удаляется источник: {source_info}"
                logger.info(log_msg)
                console_print(log_msg)
                
                logger.info(f"      • Тип: {source.source_type}")
                logger.info(f"      • Создан: {source.created_timestamp}")
                logger.info(f"      • Последняя проверка: {source.last_checked_timestamp}")
                logger.info(f"      • Последний пост: {source.last_successful_post_timestamp}")
                
                await session.delete(source)
            
            msg = f"✅ Очистка источников завершена: удалено {len(orphan_sources)}"
            logger.info(msg)
            console_print(msg)
            
        except Exception as e:
            error_msg = f"❌ Ошибка при очистке источников: {e}"
            logger.error(error_msg)
            console_print(error_msg)
            raise
    
    async def _cleanup_expired_media(self, session: AsyncSession):
        """
        Удалить устаревший кеш медиа.
        
        Условия:
        - expires_at < текущего времени
        """
        msg = "🔍 Проверка устаревшего кеша медиа..."
        logger.info(msg)
        console_print(msg)
        
        try:
            now = datetime.utcnow()
            
            # Очищаем основной кеш
            stmt_main = select(CachedMedia).where(CachedMedia.expires_at < now)
            result_main = await session.execute(stmt_main)
            expired_main = result_main.scalars().all()
            
            if expired_main:
                msg = f"📊 Найдено {len(expired_main)} устаревших записей в основном кеше:"
                logger.info(msg)
                console_print(msg)
                
                for media in expired_main[:5]:  # Показываем первые 5
                    log_msg = f"   🗑️ {media.source_global_id}: пост {media.post_id}, истёк {media.expires_at}"
                    logger.info(log_msg)
                    console_print(log_msg)
                    
                if len(expired_main) > 5:
                    log_msg = f"      ... и ещё {len(expired_main) - 5} записей"
                    logger.info(log_msg)
                    console_print(log_msg)
                
                # Удаляем
                del_main = delete(CachedMedia).where(CachedMedia.expires_at < now)
                await session.execute(del_main)
            
            # Очищаем пользовательский кеш
            stmt_user = select(UserCachedMedia).where(UserCachedMedia.expires_at < now)
            result_user = await session.execute(stmt_user)
            expired_user = result_user.scalars().all()
            
            if expired_user:
                msg = f"📊 Найдено {len(expired_user)} устаревших записей в пользовательском кеше:"
                logger.info(msg)
                console_print(msg)
                
                for media in expired_user[:5]:
                    log_msg = f"   🗑️ Пользователь {media.user_id}: файл {media.file_id[:20]}..., истёк {media.expires_at}"
                    logger.info(log_msg)
                    console_print(log_msg)
                    
                if len(expired_user) > 5:
                    log_msg = f"      ... и ещё {len(expired_user) - 5} записей"
                    logger.info(log_msg)
                    console_print(log_msg)
                
                # Удаляем
                del_user = delete(UserCachedMedia).where(UserCachedMedia.expires_at < now)
                await session.execute(del_user)
            
            msg = f"✅ Очистка кеша: удалено {len(expired_main)} основных, {len(expired_user)} пользовательских записей"
            logger.info(msg)
            console_print(msg)
            
        except Exception as e:
            error_msg = f"❌ Ошибка при очистке кеша медиа: {e}"
            logger.error(error_msg)
            console_print(error_msg)
            raise
    
    async def _cleanup_orphan_topics(self, session: AsyncSession):
        """
        Удалить темы, помеченные как несуществующие в Telegram (is_exists_in_tg=False),
        которые не используются в назначениях и созданы >30 дней назад.
        """
        msg = "🔍 Проверка удалённых тем..."
        logger.info(msg)
        console_print(msg)
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=0)
            
            # Находим темы с is_exists_in_tg=False
            stmt = select(GroupTopic).where(
                and_(
                    GroupTopic.is_exists_in_tg == False,
                    GroupTopic.created_timestamp < cutoff_date
                )
            )
            result = await session.execute(stmt)
            dead_topics = result.scalars().all()
            
            if not dead_topics:
                msg = "✅ Нет удалённых тем для очистки"
                logger.info(msg)
                console_print(msg)
                return
            
            msg = f"📊 Найдено {len(dead_topics)} потенциально удалённых тем"
            logger.info(msg)
            console_print(msg)
            
            # Проверяем, используются ли темы в назначениях
            topics_to_delete = []
            for topic in dead_topics:
                assign_stmt = select(TopicSourceAssignment).where(
                    TopicSourceAssignment.topic_identifier == topic.topic_identifier
                )
                assign_result = await session.execute(assign_stmt)
                if not assign_result.first():
                    topics_to_delete.append(topic)
            
            if not topics_to_delete:
                msg = "✅ Нет неиспользуемых удалённых тем"
                logger.info(msg)
                console_print(msg)
                return
            
            msg = f"📊 Найдено {len(topics_to_delete)} удалённых тем для очистки:"
            logger.info(msg)
            console_print(msg)
            
            # Удаляем темы
            for topic in topics_to_delete:
                log_msg = f"   🗑️ Удаляется тема:"
                logger.info(log_msg)
                console_print(log_msg)
                
                logger.info(f"      • ID: {topic.topic_identifier}")
                logger.info(f"      • Название: {topic.topic_name}")
                logger.info(f"      • Группа: {topic.telegram_chat_id}")
                logger.info(f"      • Создана: {topic.created_timestamp}")
                logger.info(f"      • Помечена как удалённая: {topic.is_exists_in_tg}")
                
                await session.delete(topic)
            
            msg = f"✅ Очистка тем завершена: удалено {len(topics_to_delete)}"
            logger.info(msg)
            console_print(msg)
            
        except Exception as e:
            error_msg = f"❌ Ошибка при очистке тем: {e}"
            logger.error(error_msg)
            console_print(error_msg)
            raise
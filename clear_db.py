#!/usr/bin/env python
"""
Скрипт для очистки базы данных MyAggryBot.
Оставляет только аккаунт пользователя.
Версия: 2.2 (17 февраля 2026)
Изменения:
- Добавлена поддержка новых полей YouTube (youtube_username, channel_language, last_video_timestamp)
- Обновлён порядок удаления таблиц
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete, func, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from core.models import (
    TelegramAccount,
    ManagedGroup,
    GroupMembership,
    ContentSource,
    UserChannelSubscription,
    GroupTopic,
    SourceSubscription,
    TopicSourceAssignment,
    CachedMedia,
    UserCachedMedia,
    UserPreferences
)
from core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_table_counts(session: AsyncSession) -> dict:
    """Получить количество записей во всех таблицах"""
    tables = [
        ('TopicSourceAssignment', TopicSourceAssignment),
        ('SourceSubscription', SourceSubscription),
        ('UserChannelSubscription', UserChannelSubscription),
        ('GroupTopic', GroupTopic),
        ('GroupMembership', GroupMembership),
        ('ManagedGroup', ManagedGroup),
        ('CachedMedia', CachedMedia),
        ('UserCachedMedia', UserCachedMedia),
        ('UserPreferences', UserPreferences),
        ('ContentSource', ContentSource),
        ('TelegramAccount', TelegramAccount),
    ]
    
    counts = {}
    for name, model in tables:
        try:
            result = await session.execute(select(func.count()).select_from(model))
            counts[name] = result.scalar() or 0
        except Exception as e:
            logger.error(f"❌ Ошибка подсчёта {name}: {e}")
            counts[name] = -1
    
    return counts


async def verify_user_exists(session: AsyncSession, user_id: int) -> bool:
    """Проверить, существует ли пользователь в БД"""
    result = await session.execute(
        select(TelegramAccount).where(TelegramAccount.telegram_account_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        logger.info(f"👤 Найден пользователь: @{user.telegram_username or 'без username'} (ID: {user_id})")
        return True
    else:
        logger.warning(f"⚠️ Пользователь {user_id} НЕ найден в БД")
        return False


async def clear_database(keep_user_id: int = None, dry_run: bool = False):
    """
    Очищает базу данных, оставляя только указанного пользователя.
    """
    
    engine = create_async_engine(
        settings.database_url_async,
        echo=False,
        pool_pre_ping=True
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    logger.info("=" * 70)
    logger.info("🧹 ОЧИСТКА БАЗЫ ДАННЫХ")
    if dry_run:
        logger.info("🔍 РЕЖИМ ПРОСМОТРА (dry-run) — изменения не будут сохранены")
    logger.info("=" * 70)
    
    async with async_session() as session:
        try:
            if not dry_run:
                await session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            
            logger.info("\n📊 ТЕКУЩЕЕ СОСТОЯНИЕ БД:")
            before_counts = await get_table_counts(session)
            for table, count in before_counts.items():
                if count > 0:
                    logger.info(f"  • {table}: {count}")
            
            user_exists = False
            if keep_user_id:
                user_exists = await verify_user_exists(session, keep_user_id)
                if not user_exists and not dry_run:
                    logger.warning("⚠️ Пользователь не найден, будет очищена ВСЯ БД")
                    response = input("\nПользователь не найден. Всё равно очистить БД? (y/N): ").strip().lower()
                    if response not in ('y', 'yes', 'д', 'да'):
                        logger.info("❌ Очистка отменена")
                        return
            
            if dry_run:
                logger.info("\n🔍 РЕЖИМ ПРОСМОТРА — ничего не удалено")
                return
            
            deleted_counts = {}
            
            # 1. Назначения
            stmt = delete(TopicSourceAssignment)
            result = await session.execute(stmt)
            deleted_counts['TopicSourceAssignment'] = result.rowcount
            logger.info(f"  ✅ TopicSourceAssignment: {result.rowcount}")
            
            # 2. Подписки групп
            stmt = delete(SourceSubscription)
            result = await session.execute(stmt)
            deleted_counts['SourceSubscription'] = result.rowcount
            logger.info(f"  ✅ SourceSubscription: {result.rowcount}")
            
            # 3. Личные подписки пользователей
            if keep_user_id and user_exists:
                stmt = delete(UserChannelSubscription).where(
                    UserChannelSubscription.user_id != keep_user_id
                )
            else:
                stmt = delete(UserChannelSubscription)
            result = await session.execute(stmt)
            deleted_counts['UserChannelSubscription'] = result.rowcount
            logger.info(f"  ✅ UserChannelSubscription: {result.rowcount}")
            
            # 4. Темы
            stmt = delete(GroupTopic)
            result = await session.execute(stmt)
            deleted_counts['GroupTopic'] = result.rowcount
            logger.info(f"  ✅ GroupTopic: {result.rowcount}")
            
            # 5. Членства в группах
            if keep_user_id and user_exists:
                stmt = delete(GroupMembership).where(
                    GroupMembership.telegram_account_id != keep_user_id
                )
            else:
                stmt = delete(GroupMembership)
            result = await session.execute(stmt)
            deleted_counts['GroupMembership'] = result.rowcount
            logger.info(f"  ✅ GroupMembership: {result.rowcount}")
            
            # 6. Группы
            stmt = delete(ManagedGroup)
            result = await session.execute(stmt)
            deleted_counts['ManagedGroup'] = result.rowcount
            logger.info(f"  ✅ ManagedGroup: {result.rowcount}")
            
            # 7. Кеш медиа
            stmt = delete(CachedMedia)
            result = await session.execute(stmt)
            deleted_counts['CachedMedia'] = result.rowcount
            logger.info(f"  ✅ CachedMedia: {result.rowcount}")
            
            # 8. Личный кеш
            if keep_user_id and user_exists:
                stmt = delete(UserCachedMedia).where(
                    UserCachedMedia.user_id != keep_user_id
                )
            else:
                stmt = delete(UserCachedMedia)
            result = await session.execute(stmt)
            deleted_counts['UserCachedMedia'] = result.rowcount
            logger.info(f"  ✅ UserCachedMedia: {result.rowcount}")
            
            # 9. Настройки пользователей
            if keep_user_id and user_exists:
                stmt = delete(UserPreferences).where(
                    UserPreferences.user_id != keep_user_id
                )
            else:
                stmt = delete(UserPreferences)
            result = await session.execute(stmt)
            deleted_counts['UserPreferences'] = result.rowcount
            logger.info(f"  ✅ UserPreferences: {result.rowcount}")
            
            # 10. Источники (включая все новые поля YouTube)
            stmt = delete(ContentSource)
            result = await session.execute(stmt)
            deleted_counts['ContentSource'] = result.rowcount
            logger.info(f"  ✅ ContentSource: {result.rowcount}")
            
            # 11. Пользователи
            if keep_user_id and user_exists:
                stmt = delete(TelegramAccount).where(
                    TelegramAccount.telegram_account_id != keep_user_id
                )
                result = await session.execute(stmt)
                deleted_counts['TelegramAccount_other'] = result.rowcount
                logger.info(f"  ✅ Другие пользователи: {result.rowcount}")
                
                remaining = await session.execute(
                    select(TelegramAccount).where(
                        TelegramAccount.telegram_account_id == keep_user_id
                    )
                )
                remaining_users = remaining.scalars().all()
                if remaining_users:
                    logger.info(f"  👤 Сохранён пользователь: @{remaining_users[0].telegram_username or 'без username'}")
                else:
                    logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Пользователь {keep_user_id} пропал!")
            else:
                stmt = delete(TelegramAccount)
                result = await session.execute(stmt)
                deleted_counts['TelegramAccount_all'] = result.rowcount
                logger.info(f"  ✅ Все пользователи: {result.rowcount}")
            
            await session.commit()
            
            logger.info("\n📊 СОСТОЯНИЕ ПОСЛЕ ОЧИСТКИ:")
            after_counts = await get_table_counts(session)
            for table, count in after_counts.items():
                if count > 0:
                    logger.info(f"  • {table}: {count}")
            
            logger.info("\n" + "=" * 70)
            logger.info("📈 ИТОГИ ОЧИСТКИ:")
            total_deleted = sum(deleted_counts.values())
            logger.info(f"  ✅ Всего удалено записей: {total_deleted}")
            
            if keep_user_id and user_exists:
                logger.info(f"  👤 Сохранён пользователь: {keep_user_id}")
            
            if total_deleted == 0:
                logger.info("  ℹ️ База данных уже пуста")
            
            logger.info("=" * 70)
            logger.info("✅ ОЧИСТКА ЗАВЕРШЕНА УСПЕШНО")
            logger.info("=" * 70)
            
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"❌ Ошибка целостности данных: {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Непредвиденная ошибка: {e}", exc_info=True)
            raise
        finally:
            try:
                await session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            except:
                pass
    
    await engine.dispose()


async def main():
    """Точка входа"""
    
    DEFAULT_USER_ID = 1390719664
    
    print("\n" + "=" * 70)
    print("🧹 СКРИПТ ОЧИСТКИ БАЗЫ ДАННЫХ MyAggryBot")
    print("=" * 70)
    
    engine = create_async_engine(settings.database_url_async, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        user_exists = await verify_user_exists(session, DEFAULT_USER_ID)
        
        print("\n📊 ТЕКУЩЕЕ СОСТОЯНИЕ БД:")
        counts = await get_table_counts(session)
        has_data = False
        for table, count in counts.items():
            if count > 0:
                print(f"  • {table}: {count}")
                has_data = True
        if not has_data:
            print("  • База данных пуста")
    
    await engine.dispose()
    
    if not user_exists:
        print("\n⚠️  ВНИМАНИЕ: Пользователь для сохранения НЕ НАЙДЕН в БД!")
        print("   Будет очищена ВСЯ база данных, включая всех пользователей.")
    
    print("\n🗑️  БУДЕТ УДАЛЕНО:")
    print("  • Все источники (Telegram и YouTube каналы с их данными)")
    print("  • Все группы")
    print("  • Все подписки (личные и групповые)")
    print("  • Все темы")
    print("  • Все назначения")
    print("  • Весь кеш медиа")
    print("  • Настройки пользователей")
    
    if user_exists:
        print("\n👤 БУДЕТ СОХРАНЁН ТОЛЬКО ПОЛЬЗОВАТЕЛЬ:")
        print(f"  • ID: {DEFAULT_USER_ID}")
    else:
        print("\n⚠️  БУДУТ УДАЛЕНЫ ВСЕ ПОЛЬЗОВАТЕЛИ!")
    
    print("\n🔍 Опции:")
    print("  • dry — показать, что будет удалено (без реальных изменений)")
    print("  • yes — выполнить очистку")
    print("  • no — отмена")
    
    response = input("\nВаш выбор (dry/yes/no): ").strip().lower()
    
    if response in ('dry', '--dry', 'dry-run'):
        print("\n🚀 Запуск в режиме просмотра (dry-run)...\n")
        await clear_database(keep_user_id=DEFAULT_USER_ID, dry_run=True)
    elif response in ('yes', 'y', 'да', 'д'):
        print("\n🚀 Запуск очистки...\n")
        await clear_database(keep_user_id=DEFAULT_USER_ID, dry_run=False)
    else:
        print("\n❌ Отменено пользователем.\n")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
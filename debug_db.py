# debug_db.py
"""
🔍 СКРИПТ ДИАГНОСТИКИ БАЗЫ ДАННЫХ MyAggryBot
Версия: 4.1 (17 февраля 2026)

НАЗНАЧЕНИЕ:
    Полная диагностика состояния базы данных, проверка связей между таблицами,
    синхронизации с Redis и выявление проблем.

ЧТО ДИАГНОСТИРУЕТ:
    • Пользователи и их статусы
    • Группы и членства
    • Источники (Telegram/YouTube) с деталями (новые поля YouTube)
    • Подписки и назначения в темы
    • Кеш медиа и личный кеш пользователей
    • Redis синхронизация
    • Сводная статистика

ИСПОЛЬЗОВАНИЕ:
    python debug_db.py
"""
import asyncio
import sys
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.models import (
    TelegramAccount, 
    ManagedGroup, 
    GroupMembership,
    ContentSource,
    SourceSubscription,
    GroupTopic,
    TopicSourceAssignment,
    UserChannelSubscription,
    CachedMedia,
    UserCachedMedia,
    UserPreferences
)
from core.redis_client import get_cached_last_post, redis_client


# ======================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ======================================================================

def format_datetime(dt: datetime) -> str:
    """Форматирование даты для читаемости"""
    if not dt:
        return "никогда"
    return dt.strftime("%d.%m.%Y %H:%M:%S")


def format_bool(value: bool) -> str:
    """Форматирование булевых значений с эмодзи"""
    return "✅ Да" if value else "❌ Нет"


def get_source_icon(source_type: str) -> str:
    """Иконка для типа источника"""
    icons = {
        'telegram': '📱',
        'youtube': '📺',
        'rss': '📡',
        'default': '📄'
    }
    return icons.get(source_type, icons['default'])


def get_topic_icon(thread_id) -> str:
    """Иконка для темы"""
    return "💬 Главная" if thread_id is None else "🗨️ Тема"


# ======================================================================
# ОСНОВНЫЕ ФУНКЦИИ ДИАГНОСТИКИ
# ======================================================================

async def print_section_header(title: str, icon: str = "📋"):
    """Печать заголовка секции"""
    print("\n" + "=" * 80)
    print(f" {icon} {title.upper()}")
    print("=" * 80)


async def print_subsection(title: str, icon: str = "•"):
    """Печать подзаголовка"""
    print(f"\n  {icon} {title}")


async def check_redis_for_source(source: ContentSource):
    """Проверить Redis кеш для конкретного источника"""
    if source.source_type == "telegram" and source.telegram_username:
        try:
            val = await get_cached_last_post(source.telegram_username)
            return val
        except Exception as e:
            print(f"      ⚠️ Ошибка Redis: {e}")
            return None
    return None


async def debug_users(session: AsyncSession):
    """Диагностика пользователей"""
    await print_section_header("👥 ПОЛЬЗОВАТЕЛИ", "👤")
    
    stmt = select(TelegramAccount).order_by(TelegramAccount.telegram_account_id)
    result = await session.execute(stmt)
    users = result.scalars().all()
    
    print(f"\n  📊 Всего пользователей: {len(users)}")
    print()
    
    for i, user in enumerate(users, 1):
        print(f"  {i}. 👤 ID: {user.telegram_account_id}")
        print(f"     ├─ Username: @{user.telegram_username or 'не указан'}")
        print(f"     ├─ Имя: {user.telegram_first_name} {user.telegram_last_name or ''}")
        print(f"     ├─ Язык: {user.language_code or 'не указан'}")
        print(f"     ├─ Статус: {'🔴 Заблокировал бота' if user.is_bot_blocked else '🟢 Активен'}")
        print(f"     ├─ Зарегистрирован: {format_datetime(user.registration_timestamp)}")
        print(f"     └─ Последняя активность: {format_datetime(user.last_activity)}")
        print()


async def debug_groups(session: AsyncSession):
    """Диагностика групп"""
    await print_section_header("👥 ГРУППЫ", "🏢")
    
    stmt = select(ManagedGroup).order_by(ManagedGroup.telegram_chat_id)
    result = await session.execute(stmt)
    groups = result.scalars().all()
    
    print(f"\n  📊 Всего групп: {len(groups)}")
    print()
    
    for i, group in enumerate(groups, 1):
        print(f"  {i}. 🏢 Группа: {group.telegram_chat_title or 'Без названия'}")
        print(f"     ├─ ID чата: {group.telegram_chat_id}")
        print(f"     ├─ Тип: {group.chat_type}")
        print(f"     ├─ Активна: {format_bool(group.is_bot_active_in_group)}")
        print(f"     ├─ Роль бота: {group.bot_role_in_group}")
        print(f"     ├─ Restrict saving: {format_bool(group.restrict_saving_content)}")
        print(f"     └─ Добавлен: {format_datetime(group.bot_added_timestamp)}")
        print()


async def debug_memberships(session: AsyncSession):
    """Диагностика членств в группах"""
    await print_section_header("🤝 ЧЛЕНСТВА В ГРУППАХ", "👥")
    
    stmt = select(GroupMembership).order_by(GroupMembership.telegram_account_id)
    result = await session.execute(stmt)
    memberships = result.scalars().all()
    
    print(f"\n  📊 Всего членств: {len(memberships)}")
    print()
    
    for i, membership in enumerate(memberships, 1):
        print(f"  {i}. 🔗 Связь #{membership.id}")
        print(f"     ├─ Пользователь: {membership.telegram_account_id}")
        print(f"     ├─ Группа: {membership.telegram_chat_id}")
        print(f"     ├─ Роль: {membership.role}")
        print(f"     └─ Вступил: {format_datetime(membership.joined_timestamp)}")
        print()


async def debug_sources(session: AsyncSession):
    """Диагностика источников контента"""
    await print_section_header("📰 ИСТОЧНИКИ КОНТЕНТА", "📡")
    
    stmt = select(ContentSource).order_by(ContentSource.source_type, ContentSource.source_global_id)
    result = await session.execute(stmt)
    sources = result.scalars().all()
    
    telegram_count = sum(1 for s in sources if s.source_type == 'telegram')
    youtube_count = sum(1 for s in sources if s.source_type == 'youtube')
    rss_count = sum(1 for s in sources if s.source_type == 'rss')
    
    print(f"\n  📊 ВСЕГО ИСТОЧНИКОВ: {len(sources)}")
    print(f"     ├─ 📱 Telegram: {telegram_count}")
    print(f"     ├─ 📺 YouTube: {youtube_count}")
    print(f"     └─ 📡 RSS: {rss_count}")
    print()
    
    for i, source in enumerate(sources, 1):
        icon = get_source_icon(source.source_type)
        print(f"  {i}. {icon} {source.source_global_id}")
        print(f"     ├─ Тип: {source.source_type.upper()}")
        
        if source.source_type == "telegram":
            print(f"     ├─ Username: @{source.telegram_username or 'не указан'}")
            redis_val = await check_redis_for_source(source)
            print(f"     ├─ Последний пост ID: {source.last_successful_post_id or 'нет'}")
            print(f"     ├─ Redis кеш: {redis_val or 'нет'}")
            if redis_val != source.last_successful_post_id:
                print(f"     ├─ ⚠️ РАСХОЖДЕНИЕ REDIS!")
        
        elif source.source_type == "youtube":
            channel_id = source.feed_url.split('/')[-1] if source.feed_url else 'нет'
            print(f"     ├─ Channel ID: {channel_id}")
            print(f"     ├─ Username: @{source.youtube_username or 'не указан'}")  # ✅ НОВОЕ
            print(f"     ├─ Язык: {source.channel_language or 'en'}")  # ✅ НОВОЕ
            print(f"     ├─ Последнее видео: {source.last_video_id or 'нет'}")
            print(f"     ├─ Timestamp: {source.last_video_timestamp or 'нет'}")  # ✅ НОВОЕ
            print(f"     ├─ Числовой хеш: {source.last_successful_post_id or 'нет'}")
        
        elif source.source_type == "rss":
            print(f"     ├─ Feed URL: {source.feed_url or 'нет'}")
            print(f"     ├─ Последняя запись ID: {source.last_successful_post_id or 'нет'}")
        
        print(f"     ├─ Название: {source.title or 'Без названия'}")
        print(f"     ├─ Последняя проверка: {format_datetime(source.last_checked_timestamp)}")
        print(f"     ├─ Интервал: {source.parsing_interval} сек")
        print(f"     └─ Public URL: {source.public_url or 'нет'}")
        print()


async def debug_user_subscriptions(session: AsyncSession):
    """Диагностика личных подписок пользователей"""
    await print_section_header("🔔 ЛИЧНЫЕ ПОДПИСКИ ПОЛЬЗОВАТЕЛЕЙ", "📌")
    
    stmt = select(UserChannelSubscription).order_by(UserChannelSubscription.user_id)
    result = await session.execute(stmt)
    subs = result.scalars().all()
    
    print(f"\n  📊 Всего личных подписок: {len(subs)}")
    print()
    
    for i, sub in enumerate(subs, 1):
        print(f"  {i}. 🔖 Подписка #{sub.id}")
        print(f"     ├─ Пользователь: {sub.user_id}")
        print(f"     ├─ Источник: {sub.source_global_id}")
        print(f"     ├─ Название: {sub.custom_title or 'оригинальное'}")
        print(f"     ├─ Активна: {format_bool(sub.is_active)}")
        print(f"     └─ Создана: {format_datetime(sub.created_at)}")
        print()


async def debug_group_subscriptions(session: AsyncSession):
    """Диагностика подписок групп"""
    from sqlalchemy.orm import selectinload
    
    await print_section_header("📋 ПОДПИСКИ ГРУПП", "🔗")
    
    stmt = select(SourceSubscription).options(
        selectinload(SourceSubscription.source),
        selectinload(SourceSubscription.group)
    ).order_by(SourceSubscription.subscription_id)
    
    result = await session.execute(stmt)
    subs = result.scalars().all()
    
    print(f"\n  📊 Всего подписок групп: {len(subs)}")
    print()
    
    for i, sub in enumerate(subs, 1):
        source_name = sub.source.source_global_id if sub.source else "УДАЛЕН"
        group_name = sub.group.telegram_chat_title if sub.group else "УДАЛЕНА"
        
        print(f"  {i}. 🔗 Подписка #{sub.subscription_id}")
        print(f"     ├─ Группа: {sub.telegram_chat_id} ({group_name})")
        print(f"     ├─ Источник: {source_name}")
        print(f"     ├─ Кто добавил: {sub.added_by_telegram_account_id or 'неизвестно'}")
        print(f"     └─ Дата: {format_datetime(sub.subscription_timestamp)}")
        print()


async def debug_topics(session: AsyncSession):
    """Диагностика тем в группах"""
    from sqlalchemy.orm import selectinload
    from core.models import GroupTopic, ManagedGroup, TelegramAccount
    
    await print_section_header("🗂️ ТЕМЫ В ГРУППАХ", "📌")
    
    stmt = select(GroupTopic).options(
        selectinload(GroupTopic.group),
        selectinload(GroupTopic.created_by)
    ).order_by(GroupTopic.telegram_chat_id, GroupTopic.topic_name)
    
    result = await session.execute(stmt)
    topics = result.scalars().all()
    
    active_topics = sum(1 for t in topics if not t.is_closed)
    closed_topics = sum(1 for t in topics if t.is_closed)
    
    print(f"\n  📊 ВСЕГО ТЕМ: {len(topics)}")
    print(f"     ├─ 🟢 Активных: {active_topics}")
    print(f"     └─ 🔴 Закрытых: {closed_topics}")
    print()
    
    for i, topic in enumerate(topics, 1):
        icon = "💬" if topic.telegram_thread_id is None else "🗨️"
        thread_info = f"Thread ID: {topic.telegram_thread_id}" if topic.telegram_thread_id else "General (главная)"
        
        group_title = topic.group.telegram_chat_title if topic.group else "Неизвестная группа"
        group_id = topic.telegram_chat_id
        
        creator_name = "Неизвестен"
        if topic.created_by:
            creator_name = f"@{topic.created_by.telegram_username or 'нет username'}"
        
        print(f"  {i}. {icon} {topic.topic_name}")
        print(f"     ├─ ID темы: {topic.topic_identifier}")
        print(f"     ├─ Группа: {group_id} ({group_title})")
        print(f"     ├─ {thread_info}")
        print(f"     ├─ Статус: {'🔴 Закрыта' if topic.is_closed else '🟢 Активна'}")
        print(f"     ├─ Создал: {creator_name} (ID: {topic.created_by_telegram_account_id or 'удалён'})")
        print(f"     └─ Создана: {format_datetime(topic.created_timestamp)}")
        print()

async def debug_assignments(session: AsyncSession):
    """Диагностика назначений источников в темы"""
    from sqlalchemy.orm import selectinload
    
    await print_section_header("🔗 НАЗНАЧЕНИЯ ИСТОЧНИКОВ В ТЕМЫ", "📎")
    
    stmt = select(TopicSourceAssignment).options(
        selectinload(TopicSourceAssignment.subscription).selectinload(SourceSubscription.source)
    ).order_by(TopicSourceAssignment.assignment_id)
    
    result = await session.execute(stmt)
    assignments = result.scalars().all()
    
    print(f"\n  📊 Всего назначений: {len(assignments)}")
    print()
    
    for i, assignment in enumerate(assignments, 1):
        source_info = "УДАЛЕН"
        if assignment.subscription and assignment.subscription.source:
            source_info = assignment.subscription.source.source_global_id
        
        print(f"  {i}. 📎 Назначение #{assignment.assignment_id}")
        print(f"     ├─ Тема: {assignment.topic_identifier}")
        print(f"     ├─ Подписка: {assignment.subscription_id}")
        print(f"     ├─ Источник: {source_info}")
        print(f"     └─ Назначено: {format_datetime(assignment.assignment_timestamp)}")
        print()


async def debug_cached_media(session: AsyncSession):
    """Диагностика кеша медиа"""
    await print_section_header("💾 КЕШ МЕДИА (ОБЩИЙ)", "🖼️")
    
    from core.models import CachedMedia, ContentSource
    from sqlalchemy.orm import selectinload
    
    try:
        stmt = select(CachedMedia).options(
            selectinload(CachedMedia.source)
        ).order_by(CachedMedia.created_at.desc()).limit(20)
    except AttributeError:
        stmt = select(CachedMedia).order_by(CachedMedia.created_at.desc()).limit(20)
    
    result = await session.execute(stmt)
    media_list = result.scalars().all()
    
    total = await session.execute(select(func.count()).select_from(CachedMedia))
    total_count = total.scalar()
    
    print(f"\n  📊 Всего записей: {total_count}")
    print(f"  📋 Показано последних: {len(media_list)}")
    print()
    
    for i, media in enumerate(media_list, 1):
        source_name = "Неизвестен"
        if hasattr(media, 'source') and media.source:
            source_name = media.source.title or media.source.source_global_id
        
        print(f"  {i}. 🖼️ Запись #{media.id}")
        print(f"     ├─ Источник: {source_name} ({media.source_global_id})")
        print(f"     ├─ Пост ID: {media.post_id}")
        print(f"     ├─ Тип: {media.file_type}")
        print(f"     ├─ File ID: {media.file_id[:30]}...")
        print(f"     ├─ Создано: {format_datetime(media.created_at)}")
        print(f"     ├─ Истекает: {format_datetime(media.expires_at)}")
        print(f"     └─ Последнее использование: {format_datetime(media.last_used)}")
        print()
    
    if total_count > 20:
        print(f"  ... и ещё {total_count - 20} записей\n")


async def debug_user_media(session: AsyncSession):
    """Диагностика личного кеша пользователей"""
    await print_section_header("💾 ЛИЧНЫЙ КЕШ ПОЛЬЗОВАТЕЛЕЙ", "👤")
    
    stmt = select(UserCachedMedia).order_by(UserCachedMedia.created_at.desc()).limit(20)
    result = await session.execute(stmt)
    media_list = result.scalars().all()
    
    total = await session.execute(select(func.count()).select_from(UserCachedMedia))
    total_count = total.scalar()
    
    print(f"\n  📊 Всего записей: {total_count}")
    print(f"  📋 Показано последних: {len(media_list)}")
    print()
    
    for i, media in enumerate(media_list, 1):
        print(f"  {i}. 👤 Запись #{media.id}")
        print(f"     ├─ Пользователь: {media.user_id}")
        print(f"     ├─ Чат: {media.chat_id or 'удалён'}")
        print(f"     ├─ Сообщение ID: {media.message_id}")
        print(f"     ├─ Тип: {media.file_type}")
        print(f"     ├─ File ID: {media.file_id[:30]}...")
        print(f"     ├─ Создано: {format_datetime(media.created_at)}")
        print(f"     ├─ Истекает: {format_datetime(media.expires_at)}")
        print(f"     └─ Последний доступ: {format_datetime(media.last_accessed)}")
        print()
    
    if total_count > 20:
        print(f"  ... и ещё {total_count - 20} записей\n")


async def debug_preferences(session: AsyncSession):
    """Диагностика настроек пользователей"""
    await print_section_header("⚙️ НАСТРОЙКИ ПОЛЬЗОВАТЕЛЕЙ", "🔧")
    
    stmt = select(UserPreferences).order_by(UserPreferences.user_id)
    result = await session.execute(stmt)
    prefs = result.scalars().all()
    
    print(f"\n  📊 Всего настроек: {len(prefs)}")
    print()
    
    for i, pref in enumerate(prefs, 1):
        print(f"  {i}. ⚙️ Пользователь: {pref.user_id}")
        print(f"     ├─ Язык: {pref.language}")
        print(f"     ├─ Стиль иконок: {pref.icons_style}")
        print(f"     ├─ Создано: {format_datetime(pref.created_at)}")
        print(f"     └─ Обновлено: {format_datetime(pref.updated_at)}")
        print()


async def print_summary(session: AsyncSession):
    """Печать сводной статистики"""
    await print_section_header("📊 СВОДНАЯ СТАТИСТИКА", "📈")
    
    users_count = (await session.execute(select(func.count()).select_from(TelegramAccount))).scalar()
    groups_count = (await session.execute(select(func.count()).select_from(ManagedGroup))).scalar()
    memberships_count = (await session.execute(select(func.count()).select_from(GroupMembership))).scalar()
    
    sources_count = (await session.execute(select(func.count()).select_from(ContentSource))).scalar()
    telegram_count = (await session.execute(
        select(func.count()).select_from(ContentSource).where(ContentSource.source_type == 'telegram')
    )).scalar()
    youtube_count = (await session.execute(
        select(func.count()).select_from(ContentSource).where(ContentSource.source_type == 'youtube')
    )).scalar()
    rss_count = (await session.execute(
        select(func.count()).select_from(ContentSource).where(ContentSource.source_type == 'rss')
    )).scalar()
    
    user_subs_count = (await session.execute(select(func.count()).select_from(UserChannelSubscription))).scalar()
    group_subs_count = (await session.execute(select(func.count()).select_from(SourceSubscription))).scalar()
    topics_count = (await session.execute(select(func.count()).select_from(GroupTopic))).scalar()
    assignments_count = (await session.execute(select(func.count()).select_from(TopicSourceAssignment))).scalar()
    media_count = (await session.execute(select(func.count()).select_from(CachedMedia))).scalar()
    user_media_count = (await session.execute(select(func.count()).select_from(UserCachedMedia))).scalar()
    prefs_count = (await session.execute(select(func.count()).select_from(UserPreferences))).scalar()
    
    print(f"""
  📈 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ:
  ├─ 👤 Пользователей: {users_count}
  ├─ 👥 Групп: {groups_count}
  └─ 🤝 Членств в группах: {memberships_count}

  📰 СТАТИСТИКА ИСТОЧНИКОВ:
  ├─ 📰 Всего источников: {sources_count}
  ├─   ├─ 📱 Telegram: {telegram_count}
  ├─   ├─ 📺 YouTube: {youtube_count}
  └─   └─ 📡 RSS: {rss_count}

  🔔 СТАТИСТИКА ПОДПИСОК:
  ├─ 🔔 Личных подписок: {user_subs_count}
  ├─ 📋 Подписок групп: {group_subs_count}
  ├─ 🗂️ Тем: {topics_count}
  └─ 🔗 Назначений: {assignments_count}

  💾 СТАТИСТИКА КЕША:
  ├─ 💾 Общий кеш медиа: {media_count}
  └─ 👤 Личный кеш пользователей: {user_media_count}

  ⚙️ ПРОЧЕЕ:
  └─ ⚙️ Настроек пользователей: {prefs_count}
    """)


async def check_redis_all():
    """Проверить Redis кеш для всех Telegram источников"""
    await print_section_header("🔥 ПРОВЕРКА REDIS КЕША", "🔄")
    
    try:
        client = await redis_client.client
        if client:
            print("\n  ✅ Redis клиент инициализирован\n")
        else:
            print("\n  ❌ Redis клиент не инициализирован\n")
            return
    except Exception as e:
        print(f"\n  ❌ Ошибка подключения к Redis: {e}\n")
        return
    
    async with async_session() as session:
        try:
            sources_stmt = select(ContentSource).where(ContentSource.source_type == "telegram")
            sources_result = await session.execute(sources_stmt)
            sources = sources_result.scalars().all()
            
            if not sources:
                print("  📭 Нет Telegram источников для проверки\n")
                return
            
            all_ok = True
            for source in sources:
                if source.telegram_username:
                    redis_val = await get_cached_last_post(source.telegram_username)
                    bd_val = source.last_successful_post_id
                    
                    status = "✅" if redis_val == bd_val else "⚠️"
                    if redis_val != bd_val:
                        all_ok = False
                    
                    print(f"  {status} @{source.telegram_username}:")
                    print(f"     ├─ БД: {bd_val}")
                    print(f"     └─ Redis: {redis_val}")
                    print()
            
            if all_ok:
                print("  ✅ Все записи Redis синхронизированы с БД\n")
            else:
                print("  ⚠️ Обнаружены расхождения Redis с БД\n")
                    
        except Exception as e:
            print(f"  ❌ Ошибка при проверке Redis: {e}\n")
        finally:
            await session.close()


# ======================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ======================================================================

async def main():
    """Главная функция диагностики"""
    print("🔍 ЗАПУСК ДИАГНОСТИКИ БАЗЫ ДАННЫХ MyAggryBot")
    
    async with async_session() as session:
        try:
            await debug_users(session)
            await debug_groups(session)
            await debug_memberships(session)
            await debug_sources(session)
            await debug_user_subscriptions(session)
            await debug_group_subscriptions(session)
            await debug_topics(session)
            await debug_assignments(session)
            await debug_cached_media(session)
            await debug_user_media(session)
            await debug_preferences(session)
            await print_summary(session)
            
        except Exception as e:
            print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.close()
    
    await check_redis_all()
    
    try:
        await redis_client.close()
        print("\n  🔌 Redis соединение закрыто")
    except:
        pass
    
    print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
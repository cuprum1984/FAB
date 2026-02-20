#!/usr/bin/env python
"""
Скрипт для проверки информации о пользователе в БД.
Использование: python check_user.py <telegram_id>
Пример: python check_user.py 1390719664
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.models import (
    TelegramAccount,
    ManagedGroup,
    GroupMembership,
    ContentSource,
    SourceSubscription,
    GroupTopic,
    TopicSourceAssignment,
    UserChannelSubscription
)
from core.settings import settings


async def check_user(user_id: int):
    """Проверить информацию о пользователе"""
    
    # Создаём подключение к БД
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("\n" + "="*60)
    print(f"🔍 ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ ID: {user_id}")
    print("="*60)
    
    async with async_session() as session:
        # ===== 1. ОСНОВНАЯ ИНФОРМАЦИЯ =====
        stmt = select(TelegramAccount).where(TelegramAccount.telegram_account_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"\n❌ Пользователь с ID {user_id} НЕ НАЙДЕН в БД!")
            return
        
        print(f"\n📌 ОСНОВНАЯ ИНФОРМАЦИЯ:")
        print(f"  ├─ ID: {user.telegram_account_id}")
        print(f"  ├─ Username: @{user.telegram_username or 'нет'}")
        print(f"  ├─ Имя: {user.telegram_first_name} {user.telegram_last_name or ''}")
        print(f"  ├─ Язык: {user.language_code or 'не указан'}")
        print(f"  ├─ Статус: {'🔴 Заблокирован' if user.is_bot_blocked else '🟢 Активен'}")
        print(f"  ├─ Зарегистрирован: {user.registration_timestamp.strftime('%d.%m.%Y %H:%M:%S')}")
        print(f"  └─ Последняя активность: {user.last_activity.strftime('%d.%m.%Y %H:%M:%S') if user.last_activity else 'никогда'}")
        
        # ===== 2. ГРУППЫ ПОЛЬЗОВАТЕЛЯ =====
        memberships_stmt = select(GroupMembership).where(
            GroupMembership.telegram_account_id == user_id
        )
        memberships_result = await session.execute(memberships_stmt)
        memberships = memberships_result.scalars().all()
        
        print(f"\n👥 ГРУППЫ ({len(memberships)}):")
        if memberships:
            for i, m in enumerate(memberships, 1):
                # Получаем информацию о группе
                group_stmt = select(ManagedGroup).where(
                    ManagedGroup.telegram_chat_id == m.telegram_chat_id
                )
                group_result = await session.execute(group_stmt)
                group = group_result.scalar_one_or_none()
                
                if group:
                    print(f"  {i}. 🏢 {group.telegram_chat_title or 'Без названия'}")
                    print(f"     ├─ ID чата: {group.telegram_chat_id}")
                    print(f"     ├─ Роль: {m.role}")
                    print(f"     ├─ Активна: {'✅' if group.is_bot_active_in_group else '❌'}")
                    print(f"     └─ Вступил: {m.joined_timestamp.strftime('%d.%m.%Y %H:%M:%S')}")
        else:
            print("  └─ Нет групп")
        
        # ===== 3. ТЕМЫ, СОЗДАННЫЕ ПОЛЬЗОВАТЕЛЕМ =====
        topics_stmt = select(GroupTopic).where(
            GroupTopic.created_by_telegram_account_id == user_id
        )
        topics_result = await session.execute(topics_stmt)
        topics = topics_result.scalars().all()
        
        print(f"\n🗂️ ТЕМЫ, СОЗДАННЫЕ ПОЛЬЗОВАТЕЛЕМ ({len(topics)}):")
        if topics:
            for i, topic in enumerate(topics, 1):
                # Получаем группу
                group_stmt = select(ManagedGroup).where(
                    ManagedGroup.telegram_chat_id == topic.telegram_chat_id
                )
                group_result = await session.execute(group_stmt)
                group = group_result.scalar_one_or_none()
                
                emoji = "💬" if topic.telegram_thread_id is None else "🗨️"
                thread_info = "General" if topic.telegram_thread_id is None else f"Thread {topic.telegram_thread_id}"
                
                print(f"  {i}. {emoji} {topic.topic_name}")
                print(f"     ├─ Группа: {group.telegram_chat_title if group else 'Неизвестно'}")
                print(f"     ├─ ID темы: {thread_info}")
                print(f"     ├─ Статус: {'🔒 Закрыта' if topic.is_closed else '🔓 Открыта'}")
                print(f"     └─ Создана: {topic.created_timestamp.strftime('%d.%m.%Y %H:%M:%S')}")
        else:
            print("  └─ Нет созданных тем")
        
        # ===== 4. ЛИЧНЫЕ ПОДПИСКИ НА КАНАЛЫ =====
        subs_stmt = select(UserChannelSubscription).where(
            UserChannelSubscription.user_id == user_id
        )
        subs_result = await session.execute(subs_stmt)
        subs = subs_result.scalars().all()
        
        print(f"\n🔔 ЛИЧНЫЕ ПОДПИСКИ НА КАНАЛЫ ({len(subs)}):")
        if subs:
            for i, sub in enumerate(subs, 1):
                # Получаем источник
                source_stmt = select(ContentSource).where(
                    ContentSource.source_global_id == sub.source_global_id
                )
                source_result = await session.execute(source_stmt)
                source = source_result.scalar_one_or_none()
                
                if source:
                    source_icon = "📺" if source.source_type == "youtube" else "📰"
                    source_name = source.title or source.source_global_id
                    
                    print(f"  {i}. {source_icon} {source_name}")
                    print(f"     ├─ Канал: {source.public_url or 'нет ссылки'}")
                    print(f"     ├─ Название: {sub.custom_title or 'стандартное'}")
                    print(f"     ├─ Статус: {'✅ Активна' if sub.is_active else '❌ Неактивна'}")
                    print(f"     └─ Добавлена: {sub.created_at.strftime('%d.%m.%Y %H:%M:%S')}")
        else:
            print("  └─ Нет личных подписок")
        
        # ===== 5. ПОДПИСКИ ГРУПП, ДОБАВЛЕННЫЕ ПОЛЬЗОВАТЕЛЕМ =====
        added_stmt = select(SourceSubscription).where(
            SourceSubscription.added_by_telegram_account_id == user_id
        )
        added_result = await session.execute(added_stmt)
        added = added_result.scalars().all()
        
        print(f"\n➕ ПОДПИСКИ ГРУПП, ДОБАВЛЕННЫЕ ПОЛЬЗОВАТЕЛЕМ ({len(added)}):")
        if added:
            for i, sub in enumerate(added, 1):
                # Получаем группу
                group_stmt = select(ManagedGroup).where(
                    ManagedGroup.telegram_chat_id == sub.telegram_chat_id
                )
                group_result = await session.execute(group_stmt)
                group = group_result.scalar_one_or_none()
                
                # Получаем источник
                source_stmt = select(ContentSource).where(
                    ContentSource.source_global_id == sub.source_global_id
                )
                source_result = await session.execute(source_stmt)
                source = source_result.scalar_one_or_none()
                
                if group and source:
                    source_icon = "📺" if source.source_type == "youtube" else "📰"
                    
                    print(f"  {i}. {source_icon} {source.title or source.source_global_id[:20]}")
                    print(f"     ├─ Группа: {group.telegram_chat_title or 'Без названия'}")
                    print(f"     ├─ ID подписки: {sub.subscription_id}")
                    print(f"     └─ Добавлена: {sub.subscription_timestamp.strftime('%d.%m.%Y %H:%M:%S')}")
                    
                    # Получаем назначения в темы
                    assign_stmt = select(TopicSourceAssignment).where(
                        TopicSourceAssignment.subscription_id == sub.subscription_id
                    )
                    assign_result = await session.execute(assign_stmt)
                    assigns = assign_result.scalars().all()
                    
                    if assigns:
                        print(f"         Назначения в темы:")
                        for j, a in enumerate(assigns, 1):
                            topic_stmt = select(GroupTopic).where(
                                GroupTopic.topic_identifier == a.topic_identifier
                            )
                            topic_result = await session.execute(topic_stmt)
                            topic = topic_result.scalar_one_or_none()
                            
                            if topic:
                                emoji = "💬" if topic.telegram_thread_id is None else "🗨️"
                                print(f"           {j}. {emoji} {topic.topic_name}")
        else:
            print("  └─ Нет добавленных подписок")
        
        # ===== 6. СТАТИСТИКА =====
        print(f"\n📊 СТАТИСТИКА:")
        print(f"  ├─ Групп: {len(memberships)}")
        print(f"  ├─ Создано тем: {len(topics)}")
        print(f"  ├─ Личных подписок: {len(subs)}")
        print(f"  └─ Добавлено подписок в группы: {len(added)}")
    
    print("\n" + "="*60)
    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Использование: python check_user.py <telegram_id>")
        print("   Пример: python check_user.py 1390719664")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        asyncio.run(check_user(user_id))
    except ValueError:
        print("❌ ID пользователя должен быть числом")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
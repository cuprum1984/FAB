# check_and_fix_missing_assignments.py
import asyncio
from sqlalchemy import select
from core.database import async_session
from core.models import (
    ContentSource, 
    SourceSubscription, 
    TopicSourceAssignment,
    ManagedGroup,
    GroupTopic
)
from core.services.destination_service import (
    get_source_subscription,
    create_source_subscription,
    create_topic_assignment
)
from core.utils.topic_utils import generate_topic_identifier


async def check_and_fix_missing_assignments():
    """Проверить и исправить недостающие подписки и назначения"""
    async with async_session() as session:
        print("🔍 Проверка целостности данных...")
        
        # 1. Получаем все группы
        groups_stmt = select(ManagedGroup)
        groups_result = await session.execute(groups_stmt)
        groups = groups_result.scalars().all()
        
        print(f"📊 Найдено групп: {len(groups)}")
        
        for group in groups:
            print(f"\n👥 Группа: {group.telegram_chat_title} (ID: {group.telegram_chat_id})")
            
            # 2. Получаем все источники
            sources_stmt = select(ContentSource)
            sources_result = await session.execute(sources_stmt)
            sources = sources_result.scalars().all()
            
            print(f"  📰 Всего источников в системе: {len(sources)}")
            
            # 3. Проверяем подписки группы
            subscriptions_stmt = select(SourceSubscription).where(
                SourceSubscription.telegram_chat_id == group.telegram_chat_id
            )
            subscriptions_result = await session.execute(subscriptions_stmt)
            subscriptions = subscriptions_result.scalars().all()
            
            subscription_sources = {sub.source_global_id for sub in subscriptions}
            print(f"  📋 Подписок группы: {len(subscriptions)}")
            print(f"  📌 ID источников в подписках: {subscription_sources}")
            
            # 4. Проверяем, какие источники НЕ имеют подписки
            all_source_ids = {source.source_global_id for source in sources}
            missing_subscriptions = all_source_ids - subscription_sources
            
            if missing_subscriptions:
                print(f"  ❌ Отсутствуют подписки для источников: {missing_subscriptions}")
                
                # Создаём недостающие подписки
                for source_id in missing_subscriptions:
                    print(f"  ➕ Создаём подписку для источника: {source_id}")
                    
                    # Находим источник
                    source_stmt = select(ContentSource).where(ContentSource.source_global_id == source_id)
                    source_result = await session.execute(source_stmt)
                    source = source_result.scalar_one_or_none()
                    
                    if source:
                        # Создаём подписку
                        subscription = SourceSubscription(
                            telegram_chat_id=group.telegram_chat_id,
                            source_global_id=source_id,
                            added_by_telegram_account_id=1390719664  # ваш user_id
                        )
                        session.add(subscription)
                        await session.flush()
                        print(f"    ✅ Создана подписка ID: {subscription.subscription_id}")
            else:
                print(f"  ✅ Все источники имеют подписки")
            
            # 5. Проверяем назначения (TopicSourceAssignment)
            # Получаем все темы группы
            topics_stmt = select(GroupTopic).where(GroupTopic.telegram_chat_id == group.telegram_chat_id)
            topics_result = await session.execute(topics_stmt)
            topics = topics_result.scalars().all()
            
            print(f"  🗂️  Тем в группе: {len(topics)}")
            
            for topic in topics:
                print(f"    Тема: {topic.topic_name} (ID: {topic.topic_identifier})")
                
                # Проверяем назначения для этой темы
                assignments_stmt = select(TopicSourceAssignment).where(
                    TopicSourceAssignment.topic_identifier == topic.topic_identifier
                )
                assignments_result = await session.execute(assignments_stmt)
                assignments = assignments_result.scalars().all()
                
                assignment_sources = {ass.source_global_id for ass in assignments}
                print(f"      📌 Назначений в теме: {len(assignments)}")
                print(f"      🔗 ID источников в назначениях: {assignment_sources}")
                
                # Для каждой подписки группы проверяем, есть ли назначение в эту тему
                for subscription in subscriptions:
                    if subscription.source_global_id not in assignment_sources:
                        print(f"      ❌ Нет назначения для подписки {subscription.subscription_id} "
                              f"(источник: {subscription.source_global_id})")
                        
                        # Создаём назначение
                        assignment = TopicSourceAssignment(
                            topic_identifier=topic.topic_identifier,
                            source_global_id=subscription.source_global_id,
                            subscription_id=subscription.subscription_id
                        )
                        session.add(assignment)
                        print(f"        ➕ Создано назначение для источника: {subscription.source_global_id}")
        
        # 6. Коммитим все изменения
        try:
            await session.commit()
            print("\n✅ Все изменения сохранены в базе данных")
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка при сохранении: {e}")


async def manual_add_missing_assignment():
    """Вручную добавить недостающее назначение для @vottaktv"""
    async with async_session() as session:
        chat_id = -1003855551445
        source_global_id = "tg_channel_vottaktv"
        
        print(f"\n🔧 Ручное добавление назначения для @vottaktv")
        
        # 1. Проверяем источник
        source_stmt = select(ContentSource).where(ContentSource.source_global_id == source_global_id)
        source_result = await session.execute(source_stmt)
        source = source_result.scalar_one_or_none()
        
        if not source:
            print(f"❌ Источник {source_global_id} не найден")
            return
        
        print(f"✅ Источник найден: {source.name}")
        
        # 2. Создаём или получаем подписку
        subscription = await get_source_subscription(chat_id, source_global_id, session)
        
        if not subscription:
            print(f"➕ Создаём подписку...")
            subscription = await create_source_subscription(
                chat_id=chat_id,
                source_global_id=source_global_id,
                added_by_id=1390719664,
                session=session
            )
            print(f"✅ Создана подписка ID: {subscription.subscription_id}")
        else:
            print(f"✅ Подписка уже существует ID: {subscription.subscription_id}")
        
        # 3. Создаём назначение в General тему
        general_identifier = generate_topic_identifier(chat_id, None)
        
        # Проверяем, нет ли уже такого назначения
        existing_stmt = select(TopicSourceAssignment).where(
            TopicSourceAssignment.topic_identifier == general_identifier,
            TopicSourceAssignment.source_global_id == source_global_id
        )
        existing_result = await session.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            print(f"✅ Назначение уже существует ID: {existing.assignment_id}")
        else:
            assignment = await create_topic_assignment(
                topic_identifier=general_identifier,
                source_global_id=source_global_id,
                subscription_id=subscription.subscription_id,
                session=session
            )
            print(f"✅ Создано назначение ID: {assignment.assignment_id}")
        
        # 4. Также можно создать назначение в тему "Новости" если нужно
        news_identifier = f"{chat_id}:227"
        
        existing_news_stmt = select(TopicSourceAssignment).where(
            TopicSourceAssignment.topic_identifier == news_identifier,
            TopicSourceAssignment.source_global_id == source_global_id
        )
        existing_news_result = await session.execute(existing_news_stmt)
        existing_news = existing_news_result.scalar_one_or_none()
        
        if not existing_news:
            assignment_news = await create_topic_assignment(
                topic_identifier=news_identifier,
                source_global_id=source_global_id,
                subscription_id=subscription.subscription_id,
                session=session
            )
            print(f"✅ Создано назначение в тему 'Новости' ID: {assignment_news.assignment_id}")
        
        await session.commit()
        print(f"\n🎉 Назначения для @vottaktv успешно добавлены!")


async def main():
    print("=" * 60)
    print("🛠️  ПРОВЕРКА И ВОССТАНОВЛЕНИЕ ЦЕЛОСТНОСТИ ДАННЫХ")
    print("=" * 60)
    
    # 1. Проверяем и исправляем все недостающие связи
    await check_and_fix_missing_assignments()
    
    # 2. Ручное добавление для @vottaktv
    await manual_add_missing_assignment()
    
    print("\n" + "=" * 60)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
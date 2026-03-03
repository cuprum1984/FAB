"""Старые хендлеры для списков источников (src_page:, close_sources, del_source:)."""
import logging
import html
from aiogram import Router, F
from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ManagedGroup, ContentSource, SourceSubscription, GroupTopic, TopicSourceAssignment
from core.services.destination_service import get_user_groups
from bot.keyboards import get_source_list_kb, get_main_menu_inline
from bot.utils.menu_message import update_or_send_menu

logger = logging.getLogger(__name__)
router = Router(name="sources_list")


@router.callback_query(F.data.startswith("src_page:"))
async def navigate_sources(callback: CallbackQuery, session: AsyncSession, get_text: callable, bot: Bot):
    """Навигация по страницам источников - обновляет ВСЁ сообщение"""
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Получаем текст проверки из локализации
    check_text = get_text(['topic_check', 'message'])

    # Проверяем темы пользователя
    from core.utils.topic_checker import verify_user_topics
    alive_topics, deleted_topics, total = await verify_user_topics(user_id, bot, session, check_text)

    # Получаем все источники пользователя (только с живыми темами)
    groups = await get_user_groups(user_id, session, only_existing_topics=True)

    if not groups:
        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=get_text(['sources', 'error_no_groups_short']),
            keyboard=get_main_menu_inline(get_text),
            state=callback.state
        )
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
        .where(GroupTopic.is_exists_in_tg == True)  # Только живые темы
        .order_by(ManagedGroup.telegram_chat_title, GroupTopic.topic_name, ContentSource.source_global_id)
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

        # 🔥 ИСПРАВЛЕНО: используем display_name
        if source.channel_title:
            source_name = source.channel_title
        elif source.source_type == "telegram" and source.telegram_username:
            source_name = f"@{source.telegram_username}"
        elif source.source_type == "youtube" and source.youtube_username:
            source_name = source.youtube_username
        else:
            source_name = "Без названия"

        grouped_data[chat_id]["topics"][topic.topic_identifier]["sources"].append({
            "icon": source_icon,
            "name": source_name,
            "type": source.source_type,
            "url": source.public_url,
            "source_global_id": source.source_global_id
        })

    # ===== ФОРМИРУЕМ ТЕКСТ =====
    text = get_text(['sources', 'list_title'])
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
        group_text = get_text(['sources', 'list_group_header'], name=html.escape(chat_data['title']))

        for topic_id, topic_data in chat_data["topics"].items():
            if sources_shown >= end_source:
                break

            topic_has_sources = False
            topic_text = get_text(['sources', 'list_separator'])

            if topic_data["thread_id"] is None:
                topic_text += get_text(['sources', 'list_topic_general'], name=html.escape(topic_data['name']))
            else:
                topic_text += get_text(['sources', 'list_topic'], name=html.escape(topic_data['name']))

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

                    topic_text += get_text(['sources', 'list_source'], icon=source['icon'], link=source_link)
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
        text += get_text(['sources', 'list_page_empty'])

    # Если показали не всё, добавляем сообщение
    if sources_shown < total_sources:
        text += get_text(['sources', 'list_more'], count=total_sources - sources_shown)

    text += get_text(['sources', 'list_total'], total=total_sources, groups=len(grouped_data))

    # Собираем плоский список для кнопок
    flat_sources = []
    for chat_id, chat_data in grouped_data.items():
        for topic_id, topic_data in chat_data["topics"].items():
            for source in topic_data["sources"]:
                flat_sources.append(source)

    # Обновляем ВСЁ сообщение через update_or_send_menu
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=get_source_list_kb(flat_sources, topic_title="Источники", page=page, get_text=get_text),
        state=callback.state
    )
    await callback.answer()


@router.callback_query(F.data == "close_sources")
async def close_sources(callback: CallbackQuery, get_text: callable):
    """Закрыть список источников"""
    await callback.message.delete()
    await callback.answer(get_text(['sources', 'list_closed']))


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустышка для неактивных кнопок"""
    await callback.answer()


@router.callback_query(F.data.startswith("del_source:"))
async def delete_source_subscription(callback: CallbackQuery, session: AsyncSession, get_text: callable):
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
            await callback.answer(get_text(['sources', 'delete_not_found']))
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
        await callback.answer(get_text(['sources', 'delete_success']))

        # Обновляем список источников (переходим на первую страницу)
        await update_sources_list(callback.message, session, user_id, page=0, get_text=get_text)

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка удаления подписки: {e}")
        await callback.answer(get_text(['sources', 'delete_error']))


async def update_sources_list(message: Message, session: AsyncSession, user_id: int, page: int = 0, get_text: callable = None):
    """Вспомогательная функция для обновления списка источников"""

    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session)
    if not groups:
        # Для вспомогательной функции без state — используем простое сообщение
        await message.answer(
            get_text(['sources', 'error_no_groups_short']) if get_text else "❌ Нет активных групп"
        )
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
        .order_by(ManagedGroup.telegram_chat_title, GroupTopic.topic_name, ContentSource.source_global_id)
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

        # 🔥 ИСПРАВЛЕНО: используем display_name
        if source.channel_title:
            source_name = source.channel_title
        elif source.source_type == "telegram" and source.telegram_username:
            source_name = f"@{source.telegram_username}"
        elif source.source_type == "youtube" and source.youtube_username:
            source_name = source.youtube_username
        else:
            source_name = "Без названия"

        grouped_data[chat_id]["topics"][topic.topic_identifier]["sources"].append({
            "icon": source_icon,
            "name": source_name,
            "type": source.source_type,
            "url": source.public_url,
            "source_global_id": source.source_global_id
        })

    # ===== ФОРМИРУЕМ ТЕКСТ =====
    text = get_text(['sources', 'list_title']) if get_text else "<b>📚 Ваши подписки по группам</b>\n\n"
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
            topic_text = "    ──────────────────\n"
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

    # Обновляем сообщение через update_or_send_menu
    await update_or_send_menu(
        bot=message.bot,
        chat_id=message.from_user.id,
        text=text,
        keyboard=get_source_list_kb(flat_sources, topic_title="Источники", page=page, get_text=get_text),
        state=message.state
    )

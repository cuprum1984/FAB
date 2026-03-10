# bot/handlers/my_overview.py
"""
Обзор всех групп, топиков и источников пользователя.
Команда /mytopics и кнопка "📰 Обзор"
"""
import logging
from typing import List, Dict, Optional
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import ManagedGroup, GroupTopic, ContentSource, SourceSubscription, TopicSourceAssignment
from core.services.destination_service import get_user_groups
from core.utils.topic_checker import verify_user_topics
from bot.states import Overview
from bot.keyboards import get_overview_kb, get_main_menu_inline
from bot.utils.menu_message import update_or_send_menu, delete_menu_message_with_delay, send_menu_message, MENU_MESSAGE_ID_KEY

logger = logging.getLogger(__name__)
router = Router(name="my_overview")


# ========== КОМАНДА /mytopics ==========
@router.message(Command("mytopics"))
async def cmd_mytopics(message: Message, session: AsyncSession, bot: Bot, state: FSMContext, get_text: callable):
    """Показать обзор всех групп, топиков и источников"""
    user_id = message.from_user.id
    logger.info(f"📊 Команда /mytopics от пользователя {user_id}")
    
    await start_overview(bot, user_id, session, state, get_text)


# ========== CALLBACK "Обзор" ==========
@router.callback_query(F.data == "menu_overview")
async def on_menu_overview(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Обработчик кнопки "Обзор" из главного меню"""
    await callback.answer()
    await start_overview(callback.bot, callback.from_user.id, session, state, get_text)


async def start_overview(bot: Bot, user_id: int, session: AsyncSession, state: FSMContext, get_text: callable):
    """Запустить процесс обзора"""
    logger.info(f"📊 Запуск обзора для пользователя {user_id}")
    
    # Проверяем темы
    check_text = get_text(['topic_check', 'message'])
    await verify_user_topics(user_id, bot, session, check_text)
    
    # Получаем все группы пользователя
    groups = await get_user_groups(user_id, session, only_existing_topics=True)
    logger.info(f"📊 Найдено групп: {len(groups) if groups else 0}")
    
    if not groups:
        text = "❌ <b>Нет активных групп</b>\n\nСначала активируйте группу командой /activ"
        await update_or_send_menu(
            bot=bot,
            chat_id=user_id,
            text=text,
            keyboard=get_main_menu_inline(get_text),
            state=state
        )
        return
    
    # Для каждой группы получаем топики и источники
    overview_data = []
    total_sources = 0
    
    for group in groups:
        chat_id = group["chat_id"]
        chat_title = group["chat_title"]
        
        # Получаем топики группы
        topics_stmt = select(GroupTopic).where(
            GroupTopic.telegram_chat_id == chat_id,
            GroupTopic.is_exists_in_tg == True
        )
        topics_result = await session.execute(topics_stmt)
        topics = list(topics_result.scalars().all())
        
        group_data = {
            "chat_id": chat_id,
            "chat_title": chat_title,
            "topics": []
        }
        
        for topic in topics:
            # Получаем источники для топика
            stmt = (
                select(ContentSource, SourceSubscription, TopicSourceAssignment)
                .join(SourceSubscription, SourceSubscription.source_global_id == ContentSource.source_global_id)
                .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
                .where(
                    TopicSourceAssignment.topic_identifier == topic.topic_identifier,
                    SourceSubscription.telegram_chat_id == chat_id
                )
            )
            result = await session.execute(stmt)
            rows = result.all()
            
            sources = []
            for row in rows:
                source = row[0]
                source_name = source.channel_title or source.telegram_username or source.youtube_username or "Без названия"
                sources.append({
                    "name": source_name,
                    "source_type": source.source_type
                })
            
            total_sources += len(sources)
            
            group_data["topics"].append({
                "topic_name": topic.topic_name or "Без названия",
                "topic_identifier": topic.topic_identifier,
                "telegram_thread_id": topic.telegram_thread_id,
                "sources": sources,
                "is_general": topic.telegram_thread_id is None,
                "sources_count": len(sources)
            })
        
        overview_data.append(group_data)
    
    # Сохраняем в состояние
    await state.update_data(
        user_id=user_id,
        overview_data=overview_data,
        total_groups=len(groups),
        total_sources=total_sources,
        overview_page=0
    )
    
    # Формируем текст обзора (показываем до 5 групп на странице)
    text = format_overview_page(overview_data, 0, total_sources)
    
    # Отправляем сообщение с клавиатурой (обновляем текущее message_id!)
    keyboard = get_overview_kb(overview_data, page=0, get_text=get_text)
    
    await update_or_send_menu(
        bot=bot,
        chat_id=user_id,
        text=text,
        keyboard=keyboard,
        state=state
    )
    
    await state.set_state(Overview.viewing)


def format_overview_page(overview_data: List[Dict], page: int, total_sources: int) -> str:
    """Форматировать страницу обзора (до 5 групп на странице)"""
    groups_per_page = 5
    total_pages = (len(overview_data) + groups_per_page - 1) // groups_per_page if overview_data else 1
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * groups_per_page
    end_idx = min(start_idx + groups_per_page, len(overview_data))
    page_groups = overview_data[start_idx:end_idx]
    
    text = f"<b>📰 Обзор источников</b>\n\n"
    text += f"<b>📊 Найдено групп:</b> {len(overview_data)}\n"
    text += f"<b>📊 Всего источников:</b> {total_sources}\n\n"
    
    for group in page_groups:
        text += f"<b>👥 {group['chat_title']}</b> ({len(group['topics'])})\n"
        
        for topic in group["topics"]:
            topic_name = topic["topic_name"]
            if topic["is_general"]:
                topic_name = "💬 General"
            else:
                topic_name = f"🗨️ {topic_name}"
            
            sources_count = topic["sources_count"]
            text += f"   <b>{topic_name}</b> ({sources_count})\n"
            
            for source in topic["sources"]:
                icon = "📺" if source["source_type"] == "youtube" else "📰"
                # Обрезаем длинные имена
                name = source["name"][:25] + "..." if len(source["name"]) > 25 else source["name"]
                text += f"       {icon} {name}\n"
        
        text += "\n"
    
    if total_pages > 1:
        text += f"<i>Страница {page + 1}/{total_pages}</i>"
    
    return text


# ========== НАВИГАЦИЯ ПО ОБЗОРУ ==========
@router.callback_query(F.data.startswith("overview_page:"))
async def on_overview_page_change(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Навигация по страницам обзора"""
    await callback.answer()
    
    page = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    overview_data = data.get("overview_data", [])
    total_sources = data.get("total_sources", 0)
    
    if not overview_data:
        return
    
    total_pages = (len(overview_data) + 4) // 5  # 5 групп на страницу
    if page < 0 or page >= total_pages:
        return
    
    # Обновляем страницу в состоянии
    await state.update_data(overview_page=page)
    
    # Формируем текст для новой страницы
    text = format_overview_page(overview_data, page, total_sources)
    
    # Обновляем клавиатуру
    keyboard = get_overview_kb(overview_data, page=page, get_text=get_text)
    
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=keyboard,
        state=state
    )

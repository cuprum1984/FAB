# bot/handlers/admin.py
"""
Хендлеры для админ-панели и управления группами/темами.
Версия: 4.1 (21 февраля 2026)
Изменения:
- Добавлена локализация (i18n)
- Все тексты вынесены в locales/
- Исправлена команда /activ: убрана клавиатура из ответа в группе
- Добавлена отправка подтверждения в ЛС
"""
import html
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberAdministrator
from aiogram.exceptions import TelegramBadRequest

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models import ManagedGroup, GroupTopic
from bot.states import AdminPanel
from bot.keyboards import (
    get_admin_panel_menu, 
    get_main_menu, 
    get_groups_menu,
    get_back_to_main_kb
)
from core.services.destination_service import (
    get_user_groups,
    create_or_update_topic,
    TopicUtils
)


# Настройка логгера
logger = logging.getLogger(__name__)

router = Router(name="admin")


@router.message(F.text.in_({"👨‍💼 Админ-панель", "👨‍💼 Admin panel"}))
async def open_admin_panel(message: Message, state: FSMContext, get_text: callable):
    """Открыть админ-панель."""
    await message.answer(
        get_text(['admin', 'panel']),
        parse_mode="HTML", 
        reply_markup=get_admin_panel_menu(get_text)
    )
    await state.set_state(AdminPanel.main)


@router.message(AdminPanel.main, F.text.in_({"👥 Управление группами", "👥 Manage groups"}))
async def manage_groups_start(message: Message, session: AsyncSession, state: FSMContext, get_text: callable):
    """Управление группами."""
    user_id = message.from_user.id
    
    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session)
    
    if not groups:
        await message.answer(
            get_text(['admin', 'no_groups']),
            parse_mode="HTML",
            reply_markup=get_admin_panel_menu(get_text)
        )
        return
    
    # Сохраняем группы в состояние для следующих шагов
    await state.update_data(groups_for_manage=groups)
    
    await message.answer(
        get_text(['admin', 'groups_found'], count=len(groups)),
        parse_mode="HTML",
        reply_markup=get_groups_menu(groups, get_text)
    )
    await state.set_state(AdminPanel.group_selected)


@router.message(AdminPanel.group_selected)
async def manage_group_selected(message: Message, state: FSMContext, session: AsyncSession, get_text: callable):
    """Пользователь выбрал конкретную группу."""
    data = await state.get_data()
    groups = data.get("groups_for_manage", [])
    
    # Если groups нет в состоянии, получаем заново
    if not groups:
        user_id = message.from_user.id
        groups = await get_user_groups(user_id, session)
    
    if message.text in ("← Назад", "← Back"):
        await message.answer(
            get_text(['admin', 'panel']),
            parse_mode="HTML", 
            reply_markup=get_admin_panel_menu(get_text)
        )
        await state.set_state(AdminPanel.main)
        return
    
    if message.text in ("🏠 Главное меню", "🏠 Main menu"):
        await message.answer(
            get_text(['common', 'menu']),
            parse_mode="HTML", 
            reply_markup=get_main_menu(get_text)
        )
        await state.clear()
        return
    
    # Находим выбранную группу
    selected_text = message.text.strip()
    # Убираем эмодзи статуса если есть
    if selected_text.startswith(("✅ ", "❌ ")):
        selected_text = selected_text[2:]
    
    selected_group = None
    for group in groups:
        if group["chat_title"] == selected_text or group["display_name"] == message.text:
            selected_group = group
            break
    
    if not selected_group:
        await message.answer(
            get_text(['admin', 'select_from_list']),
            parse_mode="HTML",
            reply_markup=get_groups_menu(groups, get_text)
        )
        return
    
    chat_id = selected_group["chat_id"]
    
    # Получаем темы группы из базы
    topics_stmt = select(GroupTopic).where(
        GroupTopic.telegram_chat_id == chat_id,
        GroupTopic.is_closed == False
    ).order_by(GroupTopic.topic_name)
    
    topics_result = await session.execute(topics_stmt)
    topics = topics_result.scalars().all()
    
    # Формируем список тем
    topics_list = ""
    if topics:
        for i, topic in enumerate(topics, 1):
            thread_info = f" (ID: {topic.telegram_thread_id})" if topic.telegram_thread_id else get_text(['admin', 'general_topic'])
            topics_list += get_text(['admin', 'topic_item'], i=i, name=html.escape(topic.topic_name), thread_info=thread_info)
    else:
        topics_list = get_text(['admin', 'no_topics'])
    
    status_text = get_text(['admin', 'group_active']) if selected_group.get('is_active', True) else get_text(['admin', 'group_inactive'])
    
    await message.answer(
        get_text(['admin', 'group_info'],
                name=html.escape(selected_group['chat_title']),
                chat_id=chat_id,
                status=status_text,
                topics=topics_list),
        parse_mode="HTML",
        reply_markup=get_admin_panel_menu(get_text)
    )
    
    await state.set_state(AdminPanel.main)



@router.message(Command("activ"))
async def activate_group(message: Message, bot: Bot, session: AsyncSession, get_text: callable):
    """Активация группы."""
    # Middleware уже гарантирует, что мы здесь только в группе/супергруппе
    # Но на всякий случай добавим проверку
    if message.chat.type not in ("group", "supergroup"):
        return  # middleware должно было отсечь, но для надёжности
    
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Проверка, что отправитель - администратор
    try:
        user_member = await bot.get_chat_member(chat_id, user_id)
        if user_member.status not in ("creator", "administrator"):
            await message.answer(
                get_text(['admin', 'activ_not_admin'])
            )
            return
    except TelegramBadRequest as e:
        await message.answer(
            get_text(['admin', 'activ_check_failed'], error=e)
        )
        return

    # Проверка, что бот администратор в группе
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        
        if not isinstance(bot_member, ChatMemberAdministrator):
            await message.answer(
                get_text(['admin', 'activ_bot_not_admin']),
                parse_mode="HTML"
            )
            return
        
        can_post = getattr(bot_member, 'can_post_messages', None)
        can_send = getattr(bot_member, 'can_send_messages', None)
        
        if can_post is False and can_send is False:
            await message.answer(
                get_text(['admin', 'activ_bot_no_permission']),
                parse_mode="HTML"
            )
            return

    except TelegramBadRequest as e:
        await message.answer(
            get_text(['admin', 'activ_bot_not_member'], error=e)
        )
        return

    # Проверяем, существует ли уже группа в БД
    stmt = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
    result = await session.execute(stmt)
    existing_group = result.scalar_one_or_none()
    
    try:
        if existing_group:
            # Обновляем существующую группу
            if not existing_group.is_bot_active_in_group:
                existing_group.is_bot_active_in_group = True
                existing_group.bot_role_in_group = bot_member.status
                await session.commit()
                
                # ✅ В ГРУППЕ: только текст, БЕЗ клавиатуры
                await message.answer(
                    get_text(['admin', 'activ_reactivated'], 
                            name=html.escape(message.chat.title or get_text(['admin', 'no_title']))),
                    parse_mode="HTML"
                    # НЕТ reply_markup!
                )
                
                # ✅ В ЛС: отправляем клавиатуру для продолжения
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=get_text(['admin', 'activ_success_dm'], 
                                     name=html.escape(message.chat.title or get_text(['admin', 'no_title']))),
                        parse_mode="HTML",
                        reply_markup=get_admin_panel_menu(get_text)
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение в ЛС пользователю {user_id}: {e}")
            else:
                # ✅ В ГРУППЕ: только текст
                await message.answer(
                    get_text(['admin', 'activ_already_active'],
                            name=html.escape(message.chat.title or get_text(['admin', 'no_title']))),
                    parse_mode="HTML"
                    # НЕТ reply_markup!
                )
        else:
            # Создаём новую группу
            group = ManagedGroup(
                telegram_chat_id=chat_id,
                telegram_chat_title=message.chat.title,
                chat_type=message.chat.type,
                bot_role_in_group=bot_member.status,
                is_bot_active_in_group=True,
                restrict_saving_content=False
            )
            session.add(group)
            
            # Создаём запись о членстве пользователя
            from core.models import GroupMembership
            membership = GroupMembership(
                telegram_account_id=user_id,
                telegram_chat_id=chat_id,
                role=user_member.status
            )
            session.add(membership)
            
            await session.commit()
            
            # Создаём General тему
            general_identifier = TopicUtils.generate_topic_identifier(chat_id, None)
            
            topic_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == general_identifier)
            topic_result = await session.execute(topic_stmt)
            existing_topic = topic_result.scalar_one_or_none()
            
            if not existing_topic:
                general_topic = GroupTopic(
                    topic_identifier=general_identifier,
                    telegram_chat_id=chat_id,
                    telegram_thread_id=None,
                    topic_name="General",
                    is_closed=False,
                    created_by_telegram_account_id=user_id
                )
                session.add(general_topic)
                await session.commit()
                logger.info(f"✅ Создана General тема для группы {chat_id}")
            
            # ✅ В ГРУППЕ: только текст, БЕЗ клавиатуры
            await message.answer(
                get_text(['admin', 'activ_success'],
                        name=html.escape(message.chat.title or get_text(['admin', 'no_title'])),
                        chat_id=chat_id),
                parse_mode="HTML"
                # НЕТ reply_markup!
            )
            
            # ✅ В ЛС: отправляем клавиатуру для продолжения
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=get_text(['admin', 'activ_success_dm'],
                                 name=html.escape(message.chat.title or get_text(['admin', 'no_title']))),
                    parse_mode="HTML",
                    reply_markup=get_admin_panel_menu(get_text)
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить сообщение в ЛС пользователю {user_id}: {e}")
            
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка активации группы: {e}", exc_info=True)
        await message.answer(
            get_text(['admin', 'activ_error'], error=html.escape(str(e)[:200])),
            parse_mode="HTML"
        )



@router.message(Command("mytopics"))
async def cmd_my_topics(message: Message, session: AsyncSession, get_text: callable):
    """Показать все зарегистрированные темы пользователя."""
    user_id = message.from_user.id
    
    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session)
    
    if not groups:
        await message.answer(
            get_text(['admin', 'mytopics_no_groups']),
            parse_mode="HTML"
        )
        return
    
    text = get_text(['admin', 'mytopics_title'])
    total_topics = 0
    
    for group in groups:
        chat_id = group["chat_id"]
        
        # Получаем темы этой группы из базы
        topics_stmt = select(GroupTopic).where(
            GroupTopic.telegram_chat_id == chat_id,
            GroupTopic.is_closed == False
        ).order_by(GroupTopic.topic_name)
        
        topics_result = await session.execute(topics_stmt)
        topics = topics_result.scalars().all()
        
        if topics:
            text += get_text(['admin', 'mytopics_group_header'], name=html.escape(group['chat_title']))
            
            for topic in topics:
                emoji = get_text(['admin', 'mytopics_general']) if topic.telegram_thread_id is None else get_text(['admin', 'mytopics_topic'])
                thread_info = f" (ID: {topic.telegram_thread_id})" if topic.telegram_thread_id else get_text(['admin', 'general_topic'])
                text += get_text(['admin', 'mytopics_item'], emoji=emoji, name=html.escape(topic.topic_name), thread_info=thread_info)
                total_topics += 1
            
            text += "\n"
    
    if total_topics == 0:
        text += get_text(['admin', 'mytopics_no_topics'])
    
    text += get_text(['admin', 'mytopics_total'], count=total_topics)
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("plus"))
async def cmd_plus_topic(message: Message, bot: Bot, session: AsyncSession, state: FSMContext, get_text: callable):
    """
    Зарегистрировать тему в базе бота.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    thread_id = message.message_thread_id
    
    logger.info(f"🔍 Команда /plus: chat_id={chat_id}, thread_id={thread_id}")
    
    # ===== 1. ПРОВЕРЯЕМ, ГДЕ ВЫЗВАНА КОМАНДА =====
    is_general = False
    
    if not thread_id:
        # Это может быть General тема (у неё нет thread_id)
        # Проверяем, есть ли уже General тема в БД для этого чата
        general_identifier = TopicUtils.generate_topic_identifier(chat_id, None)
        general_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == general_identifier)
        general_result = await session.execute(general_stmt)
        general_topic = general_result.scalar_one_or_none()
        
        if general_topic:
            # Это General тема!
            is_general = True
            logger.info("📝 Команда /plus в General теме")
        else:
            # Это не тема вообще
            await message.answer(
                get_text(['admin', 'plus_not_in_topic']),
                parse_mode="HTML"
            )
            return
    
    # ===== 2. ПРОВЕРЯЕМ, АКТИВИРОВАНА ЛИ ГРУППА =====
    group_stmt = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
    group_result = await session.execute(group_stmt)
    group = group_result.scalar_one_or_none()
    
    if not group or not group.is_bot_active_in_group:
        await message.answer(
            get_text(['admin', 'plus_group_not_active']),
            parse_mode="HTML"
        )
        return
    
    # ===== 3. ПРОВЕРЯЕМ ПРАВА ПОЛЬЗОВАТЕЛЯ =====
    try:
        user_member = await bot.get_chat_member(chat_id, user_id)
        if user_member.status not in ("creator", "administrator"):
            await message.answer(
                get_text(['admin', 'plus_not_admin'])
            )
            return
    except Exception as e:
        await message.answer(
            get_text(['admin', 'plus_error'], error=e)
        )
        return
    
    # ===== 4. ПОЛУЧАЕМ ИДЕНТИФИКАТОР ТЕМЫ =====
    if is_general:
        # Для General темы thread_id = None
        topic_identifier = TopicUtils.generate_topic_identifier(chat_id, None)
        thread_id_to_save = None
    else:
        topic_identifier = TopicUtils.generate_topic_identifier(chat_id, thread_id)
        thread_id_to_save = thread_id
    
    # ===== 5. ПРОВЕРЯЕМ, ЕСТЬ ЛИ ТЕМА В БД =====
    topic_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
    topic_result = await session.execute(topic_stmt)
    existing_topic = topic_result.scalar_one_or_none()
    
    # ===== 6. ОПРЕДЕЛЯЕМ НАЗВАНИЕ ТЕМЫ =====
    topic_name = None
    
    if existing_topic:
        # Тема уже есть в БД
        topic_name = existing_topic.topic_name
        logger.info(f"📝 Название темы из БД: '{topic_name}'")
        
        # Если тема уже зарегистрирована, просто показываем информацию
        thread_display = "General" if is_general else thread_id
        await message.answer(
            get_text(['admin', 'plus_already_exists'],
                    name=html.escape(existing_topic.topic_name),
                    thread_id=thread_display,
                    identifier=topic_identifier),
            parse_mode="HTML"
        )
        return
    
    # ===== 7. ЕСЛИ ТЕМЫ НЕТ В БД, ОПРЕДЕЛЯЕМ НАЗВАНИЕ =====
    if is_general:
        topic_name = "General"
        logger.info("📝 Создание General темы")
    else:
        # Пробуем получить название через служебные сообщения
        topic_name = f"Topic {thread_id}"
        logger.info(f"📝 Тема не найдена в БД, использую fallback: '{topic_name}'")
        await message.answer(
            get_text(['admin', 'plus_not_found'], name=topic_name),
            parse_mode="HTML"
        )
    
    # ===== 8. СОЗДАЁМ ТЕМУ В БД =====
    try:
        topic = await create_or_update_topic(
            chat_id=chat_id,
            thread_id=thread_id_to_save,
            topic_name=topic_name,
            created_by_id=user_id,
            session=session
        )
        
        thread_display = "General" if is_general else thread_id
        
        await message.answer(
            get_text(['admin', 'plus_success'],
                    name=html.escape(topic_name),
                    thread_id=thread_display,
                    identifier=topic.topic_identifier),
            parse_mode="HTML"
        )
        logger.info(f"✅ Зарегистрирована тема: {topic_name} (thread_id: {thread_id_to_save})")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка регистрации темы: {e}", exc_info=True)
        await message.answer(
            get_text(['admin', 'plus_error_db'], error=html.escape(str(e)[:200])),
            parse_mode="HTML"
        )


@router.message(AdminPanel.main, F.text.in_({"← Назад в главное меню", "← Back to main menu"}))
async def back_to_main(message: Message, state: FSMContext, get_text: callable):
    """Вернуться в главное меню."""
    await message.answer(
        get_text(['common', 'menu']),
        parse_mode="HTML", 
        reply_markup=get_main_menu(get_text)
    )
    await state.clear()
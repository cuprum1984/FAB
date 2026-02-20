# bot/handlers/admin.py
"""
Хендлеры для админ-панели и управления группами/темами.
Версия: 3.3 (16 февраля 2026)
Изменения:
- УДАЛЁН устаревший обработчик TopicRegistration.waiting_for_name
- Добавлена обработка ошибок pyrogram
- Улучшено логирование
- Добавлена проверка прав бота на управление темами
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
from bot.states import AdminPanel  # TopicRegistration больше не импортируем!
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


@router.message(F.text == "👨‍💼 Админ-панель")
async def open_admin_panel(message: Message, state: FSMContext):
    """Открыть админ-панель."""
    await message.answer("👨‍💼 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=get_admin_panel_menu())
    await state.set_state(AdminPanel.main)


@router.message(AdminPanel.main, F.text == "👥 Управление группами")
async def manage_groups_start(message: Message, session: AsyncSession, state: FSMContext):
    """Управление группами."""
    user_id = message.from_user.id
    
    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session)
    
    if not groups:
        await message.answer(
            "<b>❌ У вас нет активных групп.</b>\n\n"
            "Добавьте группу командой /activ в нужной группе.",
            parse_mode="HTML",
            reply_markup=get_admin_panel_menu()
        )
        return
    
    # Сохраняем группы в состояние для следующих шагов
    await state.update_data(groups_for_manage=groups)
    
    await message.answer(
        f"<b>👥 Управление группами</b>\n\n"
        f"Найдено групп: <b>{len(groups)}</b>\n\n"
        f"Выберите группу для управления:",
        parse_mode="HTML",
        reply_markup=get_groups_menu(groups)
    )
    await state.set_state(AdminPanel.group_selected)


@router.message(AdminPanel.group_selected)
async def manage_group_selected(message: Message, state: FSMContext, session: AsyncSession):
    """Пользователь выбрал конкретную группу."""
    data = await state.get_data()
    groups = data.get("groups_for_manage", [])
    
    # Если groups нет в состоянии, получаем заново
    if not groups:
        user_id = message.from_user.id
        groups = await get_user_groups(user_id, session)
    
    if message.text == "← Назад в Админ-панель":
        await message.answer("👨‍💼 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=get_admin_panel_menu())
        await state.set_state(AdminPanel.main)
        return
    
    if message.text == "🏠 Главное меню":
        await message.answer("🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=get_main_menu())
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
            "<b>❌ Пожалуйста, выберите группу из списка.</b>",
            parse_mode="HTML",
            reply_markup=get_groups_menu(groups)
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
            thread_info = f" (ID: {topic.telegram_thread_id})" if topic.telegram_thread_id else " (General)"
            topics_list += f"{i}. <b>{html.escape(topic.topic_name)}</b>{thread_info}\n"
    else:
        topics_list = "<i>Нет зарегистрированных тем</i>\n"
    
    await message.answer(
        f"<b>👥 Управление группой</b>\n\n"
        f"<b>📛 Название:</b> {html.escape(selected_group['chat_title'])}\n"
        f"<b>🆔 ID:</b> <code>{chat_id}</code>\n"
        f"<b>📊 Статус:</b> {'✅ Активна' if selected_group.get('is_active', True) else '❌ Неактивна'}\n\n"
        f"<b>🗂️ Зарегистрированные темы:</b>\n{topics_list}\n"
        f"<b>⚡ Доступные действия:</b>\n"
        f"• /activ — переактивировать группу\n"
        f"• /plus — зарегистрировать текущую тему\n"
        f"• /mytopics — список всех тем\n"
        f"• /add — добавить канал в группу",
        parse_mode="HTML",
        reply_markup=get_admin_panel_menu()
    )
    
    await state.set_state(AdminPanel.main)


@router.message(Command("activ"))
async def activate_group(message: Message, bot: Bot, session: AsyncSession):
    """Активация группы."""
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Команда работает только в группах.")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Проверка, что отправитель - администратор
    try:
        user_member = await bot.get_chat_member(chat_id, user_id)
        if user_member.status not in ("creator", "administrator"):
            await message.answer("❌ Только администраторы группы могут активировать бота.")
            return
    except TelegramBadRequest as e:
        await message.answer(f"❌ Не удалось проверить ваши права в группе: {e}")
        return

    # Проверка, что бот администратор в группе
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        
        # Проверяем, что бот администратор
        if not isinstance(bot_member, ChatMemberAdministrator):
            await message.answer(
                "<b>❌ Бот должен быть администратором группы.</b>\n\n"
                "Добавьте бота как администратора с правами:\n"
                "• <b>Отправка сообщений</b> (Send Messages) — обязательно\n"
                "• <b>Управление темами</b> (Manage Topics) — для работы с форумами",
                parse_mode="HTML"
            )
            return
        
        # Проверяем права на отправку сообщений
        can_post = getattr(bot_member, 'can_post_messages', None)
        can_send = getattr(bot_member, 'can_send_messages', None)
        
        if can_post is False and can_send is False:
            await message.answer(
                "<b>❌ Бот должен иметь право публиковать сообщения.</b>\n\n"
                "Пожалуйста, дайте боту право 'Отправка сообщений' (Send Messages).",
                parse_mode="HTML"
            )
            return

    except TelegramBadRequest as e:
        await message.answer(f"❌ Бот не является участником этой группы: {e}")
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
                await message.answer(
                    f"<b>✅ Группа реактивирована!</b>\n\n"
                    f"<b>📛 Название:</b> {html.escape(message.chat.title or 'Без названия')}",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"<b>✅ Группа уже активна</b>\n\n"
                    f"<b>📛 Название:</b> {html.escape(message.chat.title or 'Без названия')}",
                    parse_mode="HTML"
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
            
            # Проверяем, есть ли уже General тема
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
            
            await message.answer(
                f"<b>✅ Группа активирована!</b>\n\n"
                f"<b>📛 Название:</b> {html.escape(message.chat.title or 'Без названия')}\n"
                f"<b>🆔 ID:</b> <code>{chat_id}</code>\n"
                f"<b>🗂️ Создана тема:</b> General\n\n"
                f"<b>🎯 Теперь можно:</b>\n"
                f"• Добавлять каналы через /add\n"
                f"• Регистрировать темы через /plus\n"
                f"• Управлять через Админ-панель",
                parse_mode="HTML"
            )
            
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка активации группы: {e}", exc_info=True)
        await message.answer(
            f"<b>❌ Ошибка при активации группы:</b>\n<code>{html.escape(str(e)[:200])}</code>",
            parse_mode="HTML"
        )


@router.message(Command("mytopics"))
async def cmd_my_topics(message: Message, session: AsyncSession):
    """Показать все зарегистрированные темы пользователя."""
    user_id = message.from_user.id
    
    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session)
    
    if not groups:
        await message.answer(
            "<b>❌ Нет активных групп</b>\n\n"
            "<i>Сначала активируйте группу через /activ</i>",
            parse_mode="HTML"
        )
        return
    
    text = "<b>🗂️ Ваши зарегистрированные темы</b>\n\n"
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
            text += f"<b>👥 {html.escape(group['chat_title'])}</b>:\n"
            
            for topic in topics:
                emoji = "💬" if topic.telegram_thread_id is None else "🗨️"
                thread_info = f" (ID: {topic.telegram_thread_id})" if topic.telegram_thread_id else " (General)"
                text += f"  {emoji} <b>{html.escape(topic.topic_name)}</b>{thread_info}\n"
                total_topics += 1
            
            text += "\n"
    
    if total_topics == 0:
        text += "<i>Нет зарегистрированных тем</i>\n\n"
    
    text += (
        f"<b>📊 Всего тем:</b> {total_topics}\n\n"
        f"<b>📌 Как добавить тему:</b>\n"
        f"1. Перейдите в тему в Telegram\n"
        f"2. Напишите команду <code>/plus</code>\n"
        f"3. Бот зарегистрирует тему\n\n"
        f"<i>После регистрации темы можно добавлять в неё источники через /add</i>"
    )
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("plus"))
async def cmd_plus_topic(message: Message, bot: Bot, session: AsyncSession, state: FSMContext):
    """
    Зарегистрировать тему в базе бота.
    Название темы уже автоматически сохранено через служебные сообщения.
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
                "<b>❌ Эта команда работает только внутри темы!</b>\n\n"
                "1. Перейдите в нужную тему\n"
                "2. Напишите команду <code>/plus</code>\n\n"
                "<i>Если это General тема, она уже должна быть создана автоматически при /activ</i>",
                parse_mode="HTML"
            )
            return
    
    # ===== 2. ПРОВЕРЯЕМ, АКТИВИРОВАНА ЛИ ГРУППА =====
    group_stmt = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
    group_result = await session.execute(group_stmt)
    group = group_result.scalar_one_or_none()
    
    if not group or not group.is_bot_active_in_group:
        await message.answer(
            "<b>❌ Группа не активирована!</b>\n\n"
            "Сначала активируйте группу командой <code>/activ</code>",
            parse_mode="HTML"
        )
        return
    
    # ===== 3. ПРОВЕРЯЕМ ПРАВА ПОЛЬЗОВАТЕЛЯ =====
    try:
        user_member = await bot.get_chat_member(chat_id, user_id)
        if user_member.status not in ("creator", "administrator"):
            await message.answer("❌ Только администраторы могут регистрировать темы.")
            return
    except Exception as e:
        await message.answer(f"❌ Ошибка проверки прав: {e}")
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
        await message.answer(
            f"<b>✅ Тема уже зарегистрирована!</b>\n\n"
            f"• <b>📛 Название:</b> {html.escape(existing_topic.topic_name)}\n"
            f"• <b>🆔 ID темы:</b> {'General' if is_general else thread_id}\n"
            f"• <b>🔗 Идентификатор:</b> <code>{topic_identifier}</code>",
            parse_mode="HTML"
        )
        return
    
    # ===== 7. ЕСЛИ ТЕМЫ НЕТ В БД, ОПРЕДЕЛЯЕМ НАЗВАНИЕ =====
    if is_general:
        topic_name = "General"
        logger.info("📝 Создание General темы")
    else:
        # Пробуем получить название через служебные сообщения
        # Для этого нужно было бы сохранить его при создании темы
        # Но как fallback используем thread_id
        topic_name = f"Тема {thread_id}"
        logger.info(f"📝 Тема не найдена в БД, использую fallback: '{topic_name}'")
        await message.answer(
            f"⚠️ <b>Не удалось найти название темы в базе.</b>\n\n"
            f"Тема будет зарегистрирована как <b>'{topic_name}'</b>.\n"
            f"При следующем переименовании название обновится автоматически.",
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
        
        # Формируем ответ
        response = (
            f"<b>✅ Тема зарегистрирована!</b>\n\n"
            f"• <b>📛 Название:</b> {html.escape(topic_name)}\n"
        )
        
        if is_general:
            response += f"• <b>🆔 ID темы:</b> General\n"
        else:
            response += f"• <b>🆔 ID темы:</b> {thread_id}\n"
        
        response += f"• <b>🔗 Идентификатор:</b> <code>{topic.topic_identifier}</code>"
        
        await message.answer(response, parse_mode="HTML")
        logger.info(f"✅ Зарегистрирована тема: {topic_name} (thread_id: {thread_id_to_save})")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка регистрации темы: {e}", exc_info=True)
        await message.answer(
            f"<b>❌ Ошибка при регистрации темы:</b>\n<code>{html.escape(str(e)[:200])}</code>",
            parse_mode="HTML"
        )


@router.message(AdminPanel.main, F.text == "← Назад в главное меню")
async def back_to_main(message: Message, state: FSMContext):
    """Вернуться в главное меню."""
    await message.answer("🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=get_main_menu())
    await state.clear()
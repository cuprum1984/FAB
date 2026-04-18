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
from datetime import datetime, timezone
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberAdministrator, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models import ManagedGroup, GroupTopic
from bot.states import AdminPanel
from bot.keyboards import (
    get_admin_panel_menu_inline,
    get_main_menu_inline,
    get_groups_inline_kb
)
from bot.utils.menu_message import update_or_send_menu
from core.services.destination_service import (
    get_user_groups,
    create_or_update_topic,
    TopicUtils
)


# Настройка логгера
logger = logging.getLogger(__name__)

router = Router(name="admin")


@router.message(Command("activ"))
async def activate_group(message: Message, bot: Bot, session: AsyncSession, get_text: callable):
    """Активация группы."""
    # Middleware уже гарантирует, что мы здесь только в группе/супергруппе
    if message.chat.type not in ("group", "supergroup"):
        return  # middleware должно было отсечь, но для надёжности
    
    # ✅ ПРОВЕРКА: только супергруппы поддерживают темы (форумы)
    if message.chat.type == "group":
        await message.answer(
            get_text(['admin', 'activ_only_supergroup']),
            parse_mode="HTML"
        )
        return
    
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

    now = datetime.now(timezone.utc).replace(tzinfo=None)  # ✅ Naive datetime для БД

    # ✅ ДОБАВЛЕНО: обновляем название группы, если оно изменилось
    chat_title = message.chat.title
    if existing_group and chat_title and existing_group.telegram_chat_title != chat_title:
        existing_group.telegram_chat_title = chat_title
        logger.info(f"📝 Обновление названия группы: '{existing_group.telegram_chat_title or 'N/A'}' → '{chat_title}'")

    try:
        if existing_group:
            # Обновляем существующую группу
            was_inactive = not existing_group.is_bot_active_in_group

            if not existing_group.is_bot_active_in_group:
                existing_group.is_bot_active_in_group = True
                existing_group.bot_role_in_group = bot_member.status

                # ✅ ДОБАВЛЕНО: обновляем last_seen_at
                existing_group.last_seen_at = now

                # ✅ ДОБАВЛЕНО: устанавливаем creator_id, если его нет
                if not existing_group.creator_id:
                    existing_group.creator_id = user_id
                    logger.info(f"👤 Установлен creator_id={user_id} для группы {chat_id}")

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
                    await update_or_send_menu(
                        bot=bot,
                        chat_id=user_id,
                        text=get_text(['admin', 'activ_success_dm'],
                                     name=html.escape(message.chat.title or get_text(['admin', 'no_title']))),
                        keyboard=get_admin_panel_menu_inline(get_text),
                        state=state
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение в ЛС пользователю {user_id}: {e}")
            else:
                # ✅ ДОБАВЛЕНО: даже если группа активна, обновляем last_seen_at
                existing_group.last_seen_at = now
                await session.commit()
                
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
                restrict_saving_content=False,
                creator_id=user_id,           # ✅ НОВОЕ ПОЛЕ
                last_seen_at=now               # ✅ НОВОЕ ПОЛЕ
            )
            session.add(group)
            
            # ❌ Удаляем создание GroupMembership - таблицы больше нет
            
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
                    is_exists_in_tg=True,      # ✅ ЯВНО УКАЗЫВАЕМ, ЧТО ТЕМА СУЩЕСТВУЕТ
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
                await update_or_send_menu(
                    bot=bot,
                    chat_id=user_id,
                    text=get_text(['admin', 'activ_success_dm'],
                                 name=html.escape(message.chat.title or get_text(['admin', 'no_title']))),
                    keyboard=get_admin_panel_menu_inline(get_text),
                    state=state
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
async def cmd_my_topics(message: Message, session: AsyncSession, get_text: callable, bot: Bot):
    """Показать все зарегистрированные темы пользователя."""
    user_id = message.from_user.id

    # Получаем текст проверки из локализации
    check_text = get_text(['topic_check', 'message'])

    # Проверяем все темы
    from core.utils.topic_checker import verify_user_topics
    alive_topics, deleted_topics, total = await verify_user_topics(user_id, bot, session, check_text)

    # Получаем группы пользователя (только с живыми темами)
    groups = await get_user_groups(user_id, session, only_existing_topics=True)

    if not groups:
        # Используем sendMessageDraft для эффекта "печатает..."
        try:
            await bot.send_message_draft(
                chat_id=user_id,
                text=get_text(['admin', 'mytopics_no_groups']),
                parse_mode="HTML"
            )
        except Exception:
            # Fallback: обычное сообщение
            await message.answer(
                get_text(['admin', 'mytopics_no_groups']),
                parse_mode="HTML"
            )
        return

    text = get_text(['admin', 'mytopics_title'])
    total_topics = 0

    for group in groups:
        chat_id = group["chat_id"]

        # Получаем темы этой группы из базы (только живые)
        topics_stmt = select(GroupTopic).where(
            GroupTopic.telegram_chat_id == chat_id,
            GroupTopic.is_closed == False,
            GroupTopic.is_exists_in_tg == True
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

    # Используем sendMessageDraft для эффекта "печатает..."
    try:
        await bot.send_message_draft(
            chat_id=user_id,
            text=text,
            parse_mode="HTML"
        )
    except Exception:
        # Fallback: обычное сообщение
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
        general_identifier = TopicUtils.generate_topic_identifier(chat_id, None)
        general_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == general_identifier)
        general_result = await session.execute(general_stmt)
        general_topic = general_result.scalar_one_or_none()

        if general_topic:
            is_general = True
            logger.info("📝 Команда /plus в General теме")
        else:
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

    # ✅ ДОБАВЛЕНО: обновляем название группы, если оно изменилось
    chat_title = message.chat.title
    if group and chat_title and group.telegram_chat_title != chat_title:
        group.telegram_chat_title = chat_title
        logger.info(f"📝 Обновление названия группы: '{group.telegram_chat_title or 'N/A'}' → '{chat_title}'")

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
        topic_identifier = TopicUtils.generate_topic_identifier(chat_id, None)
        thread_id_to_save = None
    else:
        topic_identifier = TopicUtils.generate_topic_identifier(chat_id, thread_id)
        thread_id_to_save = thread_id

    # ===== 5. ПРОВЕРЯЕМ, ЕСТЬ ЛИ ТЕМА В БД =====
    topic_stmt = select(GroupTopic).where(GroupTopic.topic_identifier == topic_identifier)
    topic_result = await session.execute(topic_stmt)
    existing_topic = topic_result.scalar_one_or_none()

    # ===== 6. ЕСЛИ ТЕМА УЖЕ ЕСТЬ - ОБНОВЛЯЕМ ИНФОРМАЦИЮ =====
    if existing_topic:
        # ✅ Обновляем last_seen_at и флаг существования
        existing_topic.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)
        existing_topic.is_exists_in_tg = True
        await session.commit()

        thread_display = "General" if is_general else thread_id
        await message.answer(
            get_text(['admin', 'plus_already_exists'],
                    name=html.escape(existing_topic.topic_name),
                    thread_id=thread_display,
                    identifier=topic_identifier),
            parse_mode="HTML"
        )
        logger.info(f"✅ Тема обновлена: '{existing_topic.topic_name}' (ID: {thread_id})")
        return  # ✅ ВАЖНО: не создаём дубликат

    # ===== 7. ЕСЛИ ТЕМЫ НЕТ В БД - ОТПРАВЛЯЕМ ЧЕРНОВИК С КНОПКАМИ =====
    # Сохраняем данные для следующего шага
    await state.update_data({
        'chat_id': chat_id,
        'thread_id': thread_id,
        'thread_id_to_save': thread_id_to_save,
        'topic_identifier': topic_identifier,
        'user_id': user_id,
        'is_general': is_general
    })

    # Отправляем черновик с инлайн-кнопками
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_topic:{thread_id}"),
        InlineKeyboardButton(text="⚙️ Ввести название", callback_data=f"enter_topic_name:{thread_id}")
    )
    
    draft_text = (
        f"⚠️ <b>Не удалось найти название темы в базе.</b>\n\n"
        f"Тема будет зарегистрирована как <b>'Topic {thread_id}'</b>.\n"
        f"При следующем переименовании название обновится автоматически.\n\n"
        f"<b>Действия:</b>"
    )
    
    try:
        # Используем send_message_draft для топика
        draft_msg = await bot.send_message_draft(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=draft_text,
            reply_markup=builder.as_markup()
        )
        
        logger.info(f"✅ Черновик отправлен в топик {chat_id}:{thread_id}")
        
        # Переходим в состояние ожидания
        await state.set_state(AdminPanel.waiting_for_topic_name)
        
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить черновик: {e}. Использую обычное сообщение.")
        # Fallback: обычное сообщение
        await message.answer(
            draft_text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        await state.set_state(AdminPanel.waiting_for_topic_name)


# ========== ОБРАБОТКА ВВОДА НАЗВАНИЯ ТЕМЫ ==========
@router.message(AdminPanel.waiting_for_topic_name, F.text)
async def process_topic_name_input(message: Message, bot: Bot, session: AsyncSession, state: FSMContext, get_text: callable):
    """Обработка ввода названия темы"""
    topic_name = message.text.strip()
    
    # Проверяем длину
    if len(topic_name) < 1:
        await message.answer(
            get_text(['admin', 'plus_name_too_short']),
            parse_mode="HTML"
        )
        return
    
    if len(topic_name) > 128:
        await message.answer(
            get_text(['admin', 'plus_name_too_long']),
            parse_mode="HTML"
        )
        return
    
    # Получаем сохранённые данные
    data = await state.get_data()
    chat_id = data.get('chat_id')
    thread_id = data.get('thread_id')
    thread_id_to_save = data.get('thread_id_to_save')
    topic_identifier = data.get('topic_identifier')
    user_id = data.get('user_id')
    is_general = data.get('is_general', False)
    
    # Для General всегда используем "General"
    if is_general:
        topic_name = "General"
    
    # ===== СОЗДАЁМ ТЕМУ В БД =====
    try:
        topic = await create_or_update_topic(
            chat_id=chat_id,
            thread_id=thread_id_to_save,
            topic_name=topic_name,
            created_by_id=user_id,
            session=session
        )

        thread_display = "General" if is_general else thread_id

        # ✅ ОБНОВЛЯЕМ ЧЕРНОВИК вместо создания нового сообщения
        final_text = (
            f"✅ <b>Тема зарегистрирована!</b>\n\n"
            f"• <b>📛 Название:</b> {html.escape(topic_name)}\n"
            f"• <b>🆔 ID темы:</b> {thread_display}\n"
            f"• <b>🔗 Идентификатор:</b> <code>{topic.topic_identifier}</code>"
        )
        
        # Пытаемся обновить черновик
        try:
            await message.edit_text(
                final_text,
                parse_mode="HTML",
                reply_markup=None
            )
        except Exception as edit_error:
            # Если не удалось обновить (сообщение уже удалено/изменено)
            logger.warning(f"⚠️ Не удалось обновить черновик: {edit_error}")
            await message.answer(
                final_text,
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
    finally:
        # Очищаем состояние
        await state.clear()


# ========== ОБРАБОТКА КНОПОК ЧЕРНОВИКА ==========
@router.callback_query(F.data.startswith("confirm_topic:"))
async def confirm_topic_callback(callback: CallbackQuery, bot: Bot, session: AsyncSession, state: FSMContext):
    """Подтверждение регистрации темы с названием по умолчанию"""
    thread_id = int(callback.data.split(":")[1])
    
    # Получаем данные из состояния
    data = await state.get_data()
    chat_id = data.get('chat_id')
    thread_id_to_save = data.get('thread_id_to_save')
    topic_identifier = data.get('topic_identifier')
    user_id = data.get('user_id')
    is_general = data.get('is_general', False)
    
    # Название по умолчанию
    topic_name = f"Topic {thread_id}"
    if is_general:
        topic_name = "General"
    
    try:
        topic = await create_or_update_topic(
            chat_id=chat_id,
            thread_id=thread_id_to_save,
            topic_name=topic_name,
            created_by_id=user_id,
            session=session
        )
        
        # Обновляем сообщение
        final_text = (
            f"✅ <b>Тема зарегистрирована!</b>\n\n"
            f"• <b>📛 Название:</b> {html.escape(topic_name)}\n"
            f"• <b>🆔 ID темы:</b> {thread_id}\n"
            f"• <b>🔗 Идентификатор:</b> <code>{topic.topic_identifier}</code>\n\n"
            f"🔒 <i>Подтверждено пользователем</i>"
        )
        
        await callback.message.edit_text(
            final_text,
            parse_mode="HTML",
            reply_markup=None
        )
        
        await callback.answer("✅ Тема подтверждена!")
        logger.info(f"✅ Тема подтверждена: {topic_name} (thread_id: {thread_id})")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка подтверждения темы: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при регистрации темы", show_alert=True)
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("enter_topic_name:"))
async def enter_topic_name_callback(callback: CallbackQuery, state: FSMContext):
    """Запрос названия темы у пользователя"""
    thread_id = int(callback.data.split(":")[1])
    
    # Обновляем сообщение с просьбой ввести название
    await callback.message.edit_text(
        callback.message.text + "\n\n<b>📝 Введите название темы текстом:</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    
    await callback.answer("📝 Введите название темы текстом")
    logger.info(f"⏳ Ожидание названия темы от пользователя {callback.from_user.id}")


# ========== ОБРАБОТКА ПЕРЕИМЕНОВАНИЯ ГРУППЫ ==========
# ⚠️ Telegram не отправляет уведомления о переименовании группы напрямую
# Решение: обновлять название при каждом взаимодействии с группой

async def update_group_title_if_changed(chat_id: int, chat_title: str, session: AsyncSession):
    """
    Обновить название группы в БД, если оно изменилось.
    Вызывается из других хендлеров при работе с группой.
    """
    from core.models import ManagedGroup
    from sqlalchemy import select
    
    if not chat_title:
        return

    try:
        stmt = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if group and group.telegram_chat_title != chat_title:
            old_title = group.telegram_chat_title
            group.telegram_chat_title = chat_title
            await session.commit()
            logger.info(f"✅ Название группы обновлено: '{old_title}' → '{chat_title}'")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении названия группы: {e}", exc_info=True)
        await session.rollback()


# ========== ОБРАБОТЧИКИ CALLBACK_QUERY ДЛЯ АДМИН-ПАНЕЛИ ==========
@router.callback_query(F.data == "admin_groups")
async def on_admin_groups(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Обработчик кнопки "Группы" в админ-панели"""
    from bot.keyboards import get_groups_inline_kb

    await callback.answer()
    user_id = callback.from_user.id

    groups = await get_user_groups(user_id, session)

    if not groups:
        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=get_text(['admin', 'no_groups']),
            keyboard=get_admin_panel_menu_inline(get_text),
            state=state
        )
        return

    await state.update_data(groups_for_manage=groups)

    keyboard = get_groups_inline_kb(groups=groups, page=0, page_size=5, get_text=get_text, back_callback="admin_back")

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['admin', 'groups_list']),
        keyboard=keyboard,
        state=state
    )


@router.callback_query(F.data == "admin_topics")
async def on_admin_topics(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Обработчик кнопки "Топики" в админ-панели"""
    await callback.answer()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text="🗨️ <b>Управление топиками</b>\n\nИспользуйте команду /topics для управления топиками.",
        keyboard=get_admin_panel_menu_inline(get_text),
        state=state
    )


@router.callback_query(F.data == "admin_stats")
async def on_admin_stats(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Обработчик кнопки "Статистика" в админ-панели"""
    await callback.answer()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text="📊 <b>Статистика</b>\n\nФункция в разработке.",
        keyboard=get_admin_panel_menu_inline(get_text),
        state=state
    )


@router.callback_query(F.data == "admin_monitoring")
async def on_admin_monitoring(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Обработчик кнопки "Мониторинг" в админ-панели"""
    await callback.answer()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text="🔍 <b>Мониторинг</b>\n\nФункция в разработке.",
        keyboard=get_admin_panel_menu_inline(get_text),
        state=state
    )


@router.callback_query(F.data == "admin_back")
async def on_admin_back(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Обработчик кнопки "Назад" в админ-панели"""
    await callback.answer()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['admin', 'panel']),
        keyboard=get_admin_panel_menu_inline(get_text),
        state=state
    )
    await state.set_state(AdminPanel.main)
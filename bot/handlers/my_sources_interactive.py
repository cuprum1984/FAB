# bot/handlers/my_sources_interactive.py
"""
Интерактивная навигация по источникам через черновик.
Одно сообщение, которое обновляется при навигации.
"""
import logging
import hashlib
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    ContentSource, SourceSubscription, TopicSourceAssignment, 
    ManagedGroup, GroupTopic
)
from core.services.destination_service import get_user_groups
from core.utils.topic_checker import verify_user_topics
from bot.states import MySources

logger = logging.getLogger(__name__)

router = Router()


# ========== ГЛАВНАЯ КОМАНДА /list ==========
@router.message(F.command.in_(["list", "mysources"]))
@router.message(F.text.in_(["Мои источники", "My sources", "📚 Мои источники"]))
async def cmd_my_sources_interactive(message: Message, session: AsyncSession, bot: Bot, state: FSMContext, get_text: callable):
    """Показать источники с интерактивной навигацией"""
    logger.info(f"📚 /list вызван пользователем {message.from_user.id}")
    user_id = message.from_user.id

    # Проверяем темы
    check_text = get_text(['topic_check', 'message'])
    logger.info(f"🔍 Проверка тем...")
    await verify_user_topics(user_id, bot, session, check_text)

    # Получаем группы
    groups = await get_user_groups(user_id, session, only_existing_topics=True)

    if not groups:
        await message.answer(
            "❌ <b>Нет активных групп</b>\n\n"
            "Сначала активируйте группу командой /activ",
            parse_mode="HTML"
        )
        return

    # Удаляем предыдущее сообщение с клавиатурой, если есть
    data = await state.get_data()
    old_message_id = data.get('sources_message_id')
    if old_message_id:
        try:
            await bot.delete_message(chat_id=user_id, message_id=old_message_id)
            logger.info(f"🗑️ Удалено старое сообщение {old_message_id}")
        except Exception as e:
            logger.debug(f"⚠️ Не удалось удалить старое сообщение: {e}")

    # Сохраняем в состояние
    await state.update_data(user_id=user_id, groups=groups, groups_page=0)
    logger.info(f"✅ Сохранено в состояние: user_id={user_id}, groups={len(groups)}")

    # Импортируем функцию формирования клавиатуры
    from bot.keyboards import get_groups_inline_kb

    # Формируем клавиатуру через get_groups_inline_kb
    keyboard = get_groups_inline_kb(groups=groups, page=0, page_size=5, get_text=get_text, back_callback="list_cancel")

    text = (
        f"<b>📚 Мои источники</b>\n\n"
        f"<b>📊 Найдено групп:</b> {len(groups)}\n\n"
        f"<i>Выберите группу для просмотра тем:</i>"
    )

    # Отправляем сообщение и сохраняем message_id
    try:
        sent_message = await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        # Сохраняем message_id для последующего удаления
        await state.update_data(sources_message_id=sent_message.message_id)
        
        # Удаляем исходное сообщение команды
        try:
            await message.delete()
        except:
            pass
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить сообщение: {e}")
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    await state.set_state(MySources.viewing_groups)


# ========== ВЫБОР ГРУППЫ ==========
@router.callback_query(F.data.startswith("list_group:"))
async def on_group_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot, get_text: callable):
    """Пользователь выбрал группу — показываем топики"""
    chat_id = int(callback.data.split(":")[1])
    logger.info(f"🔍 Выбрана группа: {chat_id}")
    
    data = await state.get_data()
    user_id = data.get('user_id')
    groups = data.get('groups', [])
    
    logger.info(f"📊 Данные из состояния: user_id={user_id}, groups={len(groups) if groups else 0}")
    
    # Находим выбранную группу
    group = next((g for g in groups if g["chat_id"] == chat_id), None)
    if not group:
        logger.warning(f"❌ Группа {chat_id} не найдена в состоянии")
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    # Получаем топики группы
    topics_stmt = select(GroupTopic).where(
        GroupTopic.telegram_chat_id == chat_id,
        GroupTopic.is_exists_in_tg == True
    )
    topics_result = await session.execute(topics_stmt)
    topics = list(topics_result.scalars().all())
    
    logger.info(f"📊 Топики из БД: {[(t.topic_name, t.topic_identifier, t.telegram_thread_id) for t in topics]}")

    if not topics:
        await callback.answer("❌ В группе нет тем", show_alert=True)
        return

    # Создаём mapping хеш → topic_identifier (чтобы обойти ограничение 64 байта)
    topic_mapping = {}
    for topic in topics:
        # Короткий хеш (8 символов) для callback_data
        topic_hash = hashlib.md5(topic.topic_identifier.encode()).hexdigest()[:8]
        topic_mapping[topic_hash] = topic.topic_identifier

    # Сохраняем в состояние
    await state.update_data(current_group=group, current_topics=topics, topic_mapping=topic_mapping, topics_page=0)
    logger.info(f"✅ Сохранено в состояние: current_group={group['chat_title']}, topics={len(topics)}, mapping={topic_mapping}")

    # Преобразуем объекты GroupTopic в словари для get_topics_inline_kb
    topics_as_dicts = [
        {
            'topic_name': t.topic_name,
            'topic_identifier': t.topic_identifier,
            'telegram_thread_id': t.telegram_thread_id
        }
        for t in topics
    ]

    # Импортируем функцию формирования клавиатуры
    from bot.keyboards import get_topics_inline_kb

    # Формируем клавиатуру через get_topics_inline_kb
    keyboard = get_topics_inline_kb(topics=topics_as_dicts, page=0, page_size=5, get_text=get_text, back_callback="list_back:groups")

    text = (
        f"<b>👥 Группа: {group['chat_title']}</b>\n\n"
        f"<b>📊 Найдено тем:</b> {len(topics)}\n\n"
        f"<i>Выберите тему для просмотра источников:</i>"
    )

    # Обновляем черновик
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.warning(f"⚠️ Не удалось обновить сообщение: {e}")
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    
    await state.set_state(MySources.viewing_topics)


# ========== ВЫБОР ТОПИКА ==========
@router.callback_query(F.data.startswith("list_topic:"))
async def on_topic_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Пользователь выбрал топик — показываем источники"""
    topic_hash_or_id = callback.data.split(":")[1]
    data = await state.get_data()
    current_group = data.get('current_group')
    topic_mapping = data.get('topic_mapping', {})

    # Поддерживаем оба формата: хеш и полный identifier (для старых кнопок)
    if len(topic_hash_or_id) == 8:
        # Это хеш (8 символов)
        topic_identifier = topic_mapping.get(topic_hash_or_id)
        logger.info(f"🔍 Выбор топика (hash): hash={topic_hash_or_id}, identifier={topic_identifier}")
    else:
        # Это полный topic_identifier (старая кнопка)
        topic_identifier = topic_hash_or_id
        logger.info(f"🔍 Выбор топика (full): identifier={topic_identifier}")

    if not current_group:
        logger.error("❌ current_group не найден в состоянии")
        await callback.answer("❌ Ошибка: группа не найдена", show_alert=True)
        return

    if not topic_identifier:
        logger.error(f"❌ topic_identifier не найден для {topic_hash_or_id}")
        await callback.answer("❌ Ошибка: топик не найден", show_alert=True)
        return

    # Получаем источники для топика
    stmt = (
        select(ContentSource, SourceSubscription, TopicSourceAssignment)
        .join(SourceSubscription, SourceSubscription.source_global_id == ContentSource.source_global_id)
        .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
        .where(
            TopicSourceAssignment.topic_identifier == topic_identifier,
            SourceSubscription.telegram_chat_id == current_group['chat_id']
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    logger.info(f"📊 Найдено источников: {len(rows)}")

    # Формируем список источников для get_source_list_kb
    sources = []
    for row in rows:
        source = row[0]
        subscription = row[1]
        sources.append({
            'source_global_id': source.source_global_id,
            'name': source.channel_title or source.telegram_username or source.youtube_username or "Без названия",
            'subscription_id': subscription.subscription_id,
            'public_url': source.public_url or "#",
            'source_type': source.source_type
        })

    # Импортируем функцию формирования клавиатуры
    from bot.keyboards import get_source_list_kb
    
    # Формируем клавиатуру через get_source_list_kb (всегда с навигацией)
    keyboard = get_source_list_kb(sources=sources, page=0, page_size=5, get_text=get_text, use_subscription_id=True, back_callback="list_back:topics")

    text = (
        f"<b>🗨️ Тема: {current_group.get('chat_title', 'N/A')}</b>\n\n"
        f"<b>📊 Источники:</b> {len(sources)}\n\n"
        f"<i>Нажмите на источник для перехода или ❌ для удаления</i>"
    )

    # Обновляем сообщение
    try:
        if callback.message:
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
        else:
            await callback.answer("❌ Ошибка: сообщение не найдено", show_alert=True)
    except Exception as e:
        logger.warning(f"⚠️ Не удалось обновить сообщение: {e}")
        await callback.message.answer(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

    await state.set_state(MySources.viewing_sources)

    # Сохраняем topic_identifier для пагинации
    await state.update_data(current_topic_identifier=topic_identifier, sources_page=0)


# ========== УДАЛЕНИЕ ИСТОЧНИКА ==========
@router.callback_query(F.data.startswith("del_sub:"))
async def on_delete_source(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Удаление источника из топика (полное удаление подписки)"""
    logger.info(f"🔥 CALLBACK del_sub: {callback.data}")
    
    callback_data = callback.data.split(":")
    if len(callback_data) != 2:
        logger.error(f"❌ Неверный формат callback_data: {callback.data}")
        await callback.answer("❌ Ошибка формата", show_alert=True)
        return
    
    subscription_id = int(callback_data[1])
    data = await state.get_data()
    current_group = data.get('current_group')
    
    logger.info(f"🗑️ Удаление подписки {subscription_id}, current_group={current_group}")
    
    try:
        # Находим подписку (SourceSubscription)
        sub_stmt = select(SourceSubscription).where(
            SourceSubscription.subscription_id == subscription_id
        )
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()
        
        logger.info(f"🔍 Подписка найдена: {subscription is not None}")
        
        if not subscription:
            logger.warning(f"❌ Подписка {subscription_id} не найдена")
            await callback.answer("❌ Подписка не найдена. Возможно, она уже удалена.", show_alert=True)
            return
        
        topic_identifier = None
        # Находим назначение, чтобы знать, какой топик обновлять
        # У одной подписки может быть несколько назначений, поэтому используем first()
        assign_stmt = select(TopicSourceAssignment).where(
            TopicSourceAssignment.subscription_id == subscription_id
        )
        assign_result = await session.execute(assign_stmt)
        assignment = assign_result.first()
        if assignment:
            assignment = assignment[0]  # Получаем первый элемент кортежа
        
        if assignment:
            topic_identifier = assignment.topic_identifier
        
        logger.info(f"✅ Найдена подписка: source={subscription.source_global_id}, chat={subscription.telegram_chat_id}")
        
        # Удаляем подписку (TopicSourceAssignment удалятся каскадно!)
        await session.delete(subscription)
        await session.commit()
        
        logger.info(f"✅ Подписка удалена: subscription_id={subscription_id}")
        
        # Получаем обновлённый список источников
        stmt = (
            select(ContentSource, SourceSubscription, TopicSourceAssignment)
            .join(SourceSubscription, SourceSubscription.source_global_id == ContentSource.source_global_id)
            .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
            .where(
                TopicSourceAssignment.topic_identifier == topic_identifier,
                SourceSubscription.telegram_chat_id == current_group['chat_id']
            )
        )
        result = await session.execute(stmt)
        rows = result.all()
        
        logger.info(f"📊 Осталось источников: {len(rows)}")

        # Формируем список источников для get_source_list_kb
        sources = []
        for row in rows:
            source = row[0]
            subscription = row[1]
            sources.append({
                'source_global_id': source.source_global_id,
                'name': source.channel_title or source.telegram_username or source.youtube_username or "Без названия",
                'subscription_id': subscription.subscription_id,
                'public_url': source.public_url or "#",
                'source_type': source.source_type
            })

        # Получаем текущую страницу
        total_pages = (len(sources) + 4) // 5 if len(sources) > 0 else 1
        page = data.get('sources_page', 0)
        page = max(0, min(page, total_pages - 1))

        # Импортируем функцию формирования клавиатуры
        from bot.keyboards import get_source_list_kb

        # Формируем клавиатуру через get_source_list_kb
        keyboard = get_source_list_kb(sources=sources, page=page, page_size=5, get_text=get_text, use_subscription_id=True, back_callback="list_back:topics")

        page_info = f" ({page + 1}/{total_pages})" if total_pages > 1 else ""
        text = (
            f"<b>🗨️ Тема: {current_group.get('chat_title', 'N/A')}</b>{page_info}\n\n"
            f"<b>📊 Источники:</b> {len(sources)}\n\n"
            f"<i>Нажмите на источник для перехода или ❌ для удаления</i>"
        )

        try:
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
        except:
            await callback.message.answer(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
        
        await callback.answer("✅ Подписка удалена")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка удаления подписки: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


# ========== ПАГИНАЦИЯ ИСТОЧНИКОВ ==========
@router.callback_query(F.data.startswith("sources_page:"))
async def on_sources_page_change(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Переключение страницы источников"""
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    current_group = data.get('current_group')
    topic_identifier = data.get('current_topic_identifier')

    # Обновляем страницу в состоянии
    await state.update_data(sources_page=page)

    # Получаем источники
    stmt = (
        select(ContentSource, SourceSubscription, TopicSourceAssignment)
        .join(SourceSubscription, SourceSubscription.source_global_id == ContentSource.source_global_id)
        .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
        .where(
            TopicSourceAssignment.topic_identifier == topic_identifier,
            SourceSubscription.telegram_chat_id == current_group['chat_id']
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Формируем список источников для get_source_list_kb
    sources = []
    for row in rows:
        source = row[0]
        subscription = row[1]
        sources.append({
            'source_global_id': source.source_global_id,
            'name': source.channel_title or source.telegram_username or source.youtube_username or "Без названия",
            'subscription_id': subscription.subscription_id,
            'public_url': source.public_url or "#",
            'source_type': source.source_type
        })

    # Получаем текущую страницу для пагинации
    total_pages = (len(sources) + 4) // 5 if len(sources) > 0 else 1
    page = max(0, min(page, total_pages - 1))

    # Импортируем функцию формирования клавиатуры
    from bot.keyboards import get_source_list_kb

    # Формируем клавиатуру через get_source_list_kb
    keyboard = get_source_list_kb(sources=sources, page=page, page_size=5, get_text=get_text, use_subscription_id=True, back_callback="list_back:topics")

    page_info = f" ({page + 1}/{total_pages})" if total_pages > 1 else ""
    text = (
        f"<b>🗨️ Тема: {current_group.get('chat_title', 'N/A')}</b>{page_info}\n\n"
        f"<b>📊 Источники:</b> {len(sources)}\n\n"
        f"<i>Нажмите на источник для перехода или ❌ для удаления</i>"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
    except:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

    await callback.answer()


# ========== НАЗАД ==========
@router.callback_query(F.data.startswith("list_back:"))
async def on_back_pressed(callback: CallbackQuery, state: FSMContext, bot: Bot, get_text: callable):
    """Навигация назад"""
    where_to = callback.data.split(":")[1]
    data = await state.get_data()
    user_id = data.get('user_id')
    groups = data.get('groups', [])

    if where_to == "main":
        # Главное меню - ReplyKeyboardMarkup нельзя использовать в edit_text
        from bot.keyboards import get_main_menu

        # Отправляем новое сообщение с главным меню
        await callback.message.answer(
            get_text(['common', 'menu']),
            parse_mode="HTML",
            reply_markup=get_main_menu(get_text)
        )

        # Удаляем сообщение с кнопками
        try:
            await callback.message.delete()
        except:
            pass

        await state.clear()
        await callback.answer()
        return

    elif where_to == "groups":
        # Возврат к списку групп с пагинацией
        from bot.keyboards import get_groups_inline_kb

        # Получаем текущую страницу из состояния
        groups_page = data.get('groups_page', 0)

        # Формируем клавиатуру через get_groups_inline_kb
        keyboard = get_groups_inline_kb(groups=groups, page=groups_page, page_size=5, get_text=get_text, back_callback="list_cancel")

        text = (
            f"<b>📚 Мои источники</b>\n\n"
            f"<b>📊 Найдено групп:</b> {len(groups)}\n\n"
            f"<i>Выберите группу для просмотра тем:</i>"
        )

        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

        await state.set_state(MySources.viewing_groups)

    elif where_to == "topics":
        # Возврат к списку топиков с пагинацией
        from bot.keyboards import get_topics_inline_kb

        current_group = data.get('current_group')
        topics = data.get('current_topics', [])

        # Преобразуем объекты GroupTopic в словари для get_topics_inline_kb
        topics_as_dicts = [
            {
                'topic_name': t.topic_name,
                'topic_identifier': t.topic_identifier,
                'telegram_thread_id': t.telegram_thread_id
            }
            for t in topics
        ]

        # Получаем текущую страницу из состояния
        topics_page = data.get('topics_page', 0)

        # Формируем клавиатуру через get_topics_inline_kb
        keyboard = get_topics_inline_kb(topics=topics_as_dicts, page=topics_page, page_size=5, get_text=get_text, back_callback="list_back:groups")

        text = (
            f"<b>👥 Группа: {current_group['chat_title']}</b>\n\n"
            f"<b>📊 Найдено тем:</b> {len(topics)}\n\n"
            f"<i>Выберите тему для просмотра источников:</i>"
        )

        try:
            if callback.message:
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            else:
                await callback.answer("❌ Ошибка: сообщение не найдено", show_alert=True)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось обновить сообщение: {e}")
            await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

        await state.set_state(MySources.viewing_topics)

    await callback.answer()


# ========== ПАГИНАЦИЯ ГРУПП ==========
@router.callback_query(F.data.startswith("groups_page:"))
async def on_groups_page_change(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Переключение страницы групп"""
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    groups = data.get('groups', [])

    # Обновляем страницу в состоянии
    await state.update_data(groups_page=page)

    # Импортируем функцию формирования клавиатуры
    from bot.keyboards import get_groups_inline_kb

    # Формируем клавиатуру через get_groups_inline_kb
    keyboard = get_groups_inline_kb(groups=groups, page=page, page_size=5, get_text=get_text, back_callback="list_cancel")

    text = (
        f"<b>📚 Мои источники</b>\n\n"
        f"<b>📊 Найдено групп:</b> {len(groups)}\n\n"
        f"<i>Выберите группу для просмотра тем:</i>"
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    await callback.answer()


# ========== ПАГИНАЦИЯ ТОПИКОВ ==========
@router.callback_query(F.data.startswith("topics_page:"))
async def on_topics_page_change(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Переключение страницы топиков"""
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    current_group = data.get('current_group')
    topics = data.get('current_topics', [])

    # Преобразуем объекты GroupTopic в словари для get_topics_inline_kb
    topics_as_dicts = [
        {
            'topic_name': t.topic_name,
            'topic_identifier': t.topic_identifier,
            'telegram_thread_id': t.telegram_thread_id
        }
        for t in topics
    ]

    # Обновляем страницу в состоянии
    await state.update_data(topics_page=page)

    # Импортируем функцию формирования клавиатуры
    from bot.keyboards import get_topics_inline_kb

    # Формируем клавиатуру через get_topics_inline_kb
    keyboard = get_topics_inline_kb(topics=topics_as_dicts, page=page, page_size=5, get_text=get_text, back_callback="list_back:groups")

    text = (
        f"<b>👥 Группа: {current_group['chat_title']}</b>\n\n"
        f"<b>📊 Найдено тем:</b> {len(topics)}\n\n"
        f"<i>Выберите тему для просмотра источников:</i>"
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    await callback.answer()


# ========== ОТМЕНА ==========
@router.callback_query(F.data == "list_cancel")
async def on_cancel_pressed(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Отмена просмотра источников - возврат в главное меню"""
    # Получаем message_id перед очисткой состояния
    data = await state.get_data()
    sources_message_id = data.get('sources_message_id')
    
    # Очищаем состояние
    await state.clear()
    
    # Удаляем сообщение с клавиатурой источников
    if sources_message_id:
        try:
            await callback.bot.delete_message(chat_id=callback.from_user.id, message_id=sources_message_id)
            logger.info(f"🗑️ Удалено сообщение источников {sources_message_id}")
        except Exception as e:
            logger.debug(f"⚠️ Не удалось удалить сообщение источников: {e}")

    from bot.keyboards import get_main_menu

    # ReplyKeyboardMarkup нельзя использовать в edit_text, поэтому отправляем новое сообщение
    await callback.message.answer(
        get_text(['common', 'menu']),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )

    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except:
        pass

    await callback.answer()

# bot/handlers/my_sources_interactive.py
"""
Интерактивная навигация по источникам через черновик.
Одно сообщение, которое обновляется при навигации.
"""
import logging
import hashlib
from aiogram import Router, F, Bot
from aiogram.filters import Command
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
from bot.utils.menu_message import update_or_send_menu, MENU_MESSAGE_ID_KEY, delete_menu_message_with_delay

logger = logging.getLogger(__name__)

router = Router()


# ========== ГЛАВНАЯ КОМАНДА /list ==========
@router.message(Command("list", "mysources"))
async def cmd_my_sources_command(message: Message, session: AsyncSession, bot: Bot, state: FSMContext, get_text: callable = None):
    """Показать источники с интерактивной навигацией (обработчик команды /list)"""
    user_id = message.from_user.id
    is_bot = message.from_user.is_bot
    username = message.from_user.username
    full_name = message.from_user.full_name
    chat_id = message.chat.id
    chat_type = message.chat.type
    
    logger.info(f"📚 КОМАНДА /list получена:")
    logger.info(f"   - from_user.id: {user_id}")
    logger.info(f"   - from_user.is_bot: {is_bot}")
    logger.info(f"   - from_user.username: @{username}")
    logger.info(f"   - from_user.full_name: {full_name}")
    logger.info(f"   - chat.id: {chat_id}")
    logger.info(f"   - chat.type: {chat_type}")
    logger.info(f"   - bot.id: {bot.id}")
    
    # Проверка: если бот тестирует сам себя
    if user_id == bot.id:
        logger.error(f"❌ Бот {user_id} пытается вызвать /list - это неправильно!")
        logger.error(f"💡 ОТКРОЙТЕ БОТА С ВАШЕГО ЛИЧНОГО АККАУНТА TELEGRAM (не бота!)")
        logger.error(f"💡 Найдите @MyAggryBot в списке чатов и напишите ему напрямую")
        return
    
    logger.info(f"📚 get_text доступен: {get_text is not None}")
    
    # Если get_text не передан, создаём fallback функцию
    if get_text is None:
        logger.warning("⚠️ get_text не передан, используем fallback")
        def get_text(keys, **kwargs):
            fallback_texts = {
                'topic_check': {'message': '🤗 Проверка...'},
                'common': {'menu': '🏠 Главное меню'},
                'keyboards': {
                    'main_menu': {'my_sources': '📚 Мои источники'},
                    'back_to_main': '🔙 В главное меню',
                    'groups_menu': {'prev': '◀️', 'next': '▶️', 'cancel': '❌', 'dot': '.'}
                }
            }
            try:
                result = fallback_texts
                for key in keys:
                    result = result[key]
                return result
            except (KeyError, TypeError):
                return str(keys)

    await _process_my_sources(message, session, bot, state, get_text)


@router.message(F.text.in_([
    "📚 Мои источники", "📚 My sources", "📚 Мої джерела", "📚 Маё крыніцы",
    "📚 Источники", "Мои источники", "My sources", "Інші джерела", "Маё крыніцы"
]))
async def cmd_my_sources_text(message: Message, session: AsyncSession, bot: Bot, state: FSMContext, get_text: callable = None):
    """Показать источники с интерактивной навигацией (обработчик текстовой кнопки)"""
    user_id = message.from_user.id
    logger.info(f"📚 ТЕКСТОВАЯ КНОПКА нажата пользователем {user_id}")
    logger.info(f"📚 get_text доступен: {get_text is not None}")
    
    # Если get_text не передан, создаём fallback функцию
    if get_text is None:
        logger.warning("⚠️ get_text не передан, используем fallback")
        def get_text(keys, **kwargs):
            fallback_texts = {
                'topic_check': {'message': '🤗 Проверка...'},
                'common': {'menu': '🏠 Главное меню'},
                'keyboards': {
                    'main_menu': {'my_sources': '📚 Мои источники'},
                    'back_to_main': '🔙 В главное меню',
                    'groups_menu': {'prev': '◀️', 'next': '▶️', 'cancel': '❌', 'dot': '.'}
                }
            }
            try:
                result = fallback_texts
                for key in keys:
                    result = result[key]
                return result
            except (KeyError, TypeError):
                return str(keys)

    await _process_my_sources(message, session, bot, state, get_text)


async def _process_my_sources(message: Message, session: AsyncSession, bot: Bot, state: FSMContext, get_text: callable):
    """Общая логика для /list и кнопки "Мои источники" (для сообщений)"""
    user_id = message.from_user.id
    await _process_my_sources_internal(user_id, message, session, bot, state, get_text)


async def _process_my_sources_from_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Общая логика для кнопки "Мои источники" (для callback query)"""
    # ВАЖНО: берём user_id из callback.from_user, а не из callback.message!
    user_id = callback.from_user.id
    # НЕ передаём callback.message как fallback — используем только message_id из состояния
    await _process_my_sources_internal(user_id, None, session, callback.bot, state, get_text)


async def _process_my_sources_internal(user_id: int, message: Message, session: AsyncSession, bot: Bot, state: FSMContext, get_text: callable):
    """Внутренняя функция обработки — принимает user_id явно"""
    logger.info(f"📚 _process_my_sources_internal для пользователя {user_id}")
    logger.info(f"   - bot type: {type(bot)}")
    logger.info(f"   - session type: {type(session)}")
    
    # Проверяем темы
    check_text = get_text(['topic_check', 'message'])
    logger.info(f"🔍 Проверка тем... {check_text}")
    logger.info(f"   - Вызов verify_user_topics(user_id={user_id}, bot={type(bot)}, session={type(session)})")
    await verify_user_topics(user_id, bot, session, check_text)
    logger.info(f"✅ verify_user_topics завершён")

    # Получаем группы - ПРЯМОЙ ЗАПРОС для отладки
    from sqlalchemy import select
    from core.models import ManagedGroup
    
    # Проверяем ВСЕ группы в БД
    all_groups_stmt = select(ManagedGroup)
    all_groups_result = await session.execute(all_groups_stmt)
    all_groups = all_groups_result.scalars().all()
    logger.info(f"📊 ВСЕ группы в БД: {len(all_groups)}")
    for g in all_groups:
        logger.info(f"   - Группа: {g.telegram_chat_title}, creator_id={g.creator_id}, is_bot_active={g.is_bot_active_in_group}")
    
    # Получаем группы пользователя
    groups = await get_user_groups(user_id, session, only_existing_topics=True)
    logger.info(f"📊 Найдено групп для пользователя {user_id}: {len(groups) if groups else 0}")
    for g in groups:
        logger.info(f"   - {g['chat_title']}, chat_id={g['chat_id']}")

    if not groups:
        logger.warning(f"⚠️ У пользователя {user_id} нет групп. Возможно, вы тестируете с аккаунта бота?")
        logger.warning(f"💡 ОТКРОЙТЕ БОТА С ВАШЕГО ЛИЧНОГО АККАУНТА (не бота!)")

        text = "❌ <b>Нет активных групп</b>\n\nСначала активируйте группу командой /activ"

        # Пробуем отправить с клавиатурой главного меню
        from bot.keyboards import get_main_menu_inline
        keyboard = get_main_menu_inline(get_text)

        # НЕ передаём fallback_message — используем только message_id из состояния
        await update_or_send_menu(
            bot=bot,
            chat_id=user_id,
            text=text,
            keyboard=keyboard,
            state=state
        )
        return

    # Сохраняем в состояние
    await state.update_data(user_id=user_id, groups=groups, groups_page=0)
    logger.info(f"✅ Сохранено в состояние: user_id={user_id}, groups={len(groups)}")

    # Импортируем функцию формирования клавиатуры
    from bot.keyboards import get_groups_inline_kb

    # Формируем клавиатуру через get_groups_inline_kb
    keyboard = get_groups_inline_kb(groups=groups, page=0, page_size=5, get_text=get_text, back_callback="back_to_main")

    text = (
        f"<b>📚 Мои источники</b>\n\n"
        f"<b>📊 Найдено групп:</b> {len(groups)}\n\n"
        f"<i>Выберите группу для просмотра тем:</i>"
    )

    # Отправляем/обновляем сообщение через update_or_send_menu
    # НЕ передаём fallback_message — используем только message_id из состояния
    await update_or_send_menu(
        bot=bot,
        chat_id=user_id,
        text=text,
        keyboard=keyboard,
        state=state
    )

    await state.set_state(MySources.viewing_groups)


# ========== ВЫБОР ГРУППЫ ==========
@router.callback_query(F.data.startswith("list_group:"))
async def on_group_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot, get_text: callable):
    """Пользователь выбрал группу — показываем топики"""
    chat_id = int(callback.data.split(":")[1])
    logger.info(f"🔍 Выбрана группа: {chat_id}")

    # Получаем user_id из callback, а не из состояния!
    user_id = callback.from_user.id
    
    data = await state.get_data()
    groups = data.get('groups', [])

    logger.info(f"📊 Данные из состояния: user_id={user_id}, groups={len(groups) if groups else 0}")

    # Если групп нет в состоянии, загружаем их заново
    if not groups:
        logger.info(f"🔄 Группы не найдены в состоянии, загружаем заново для пользователя {user_id}")
        groups = await get_user_groups(user_id, session, only_existing_topics=True)
        logger.info(f"📊 Загружено групп: {len(groups) if groups else 0}")
        
        if not groups:
            logger.warning(f"⚠️ У пользователя {user_id} нет групп")
            await callback.answer("❌ Нет групп", show_alert=True)
            return
        
        # Сохраняем в состояние
        await state.update_data(user_id=user_id, groups=groups, groups_page=0)
        logger.info(f"✅ Сохранено в состояние: user_id={user_id}, groups={len(groups)}")

    # Находим выбранную группу
    group = next((g for g in groups if g["chat_id"] == chat_id), None)
    if not group:
        logger.warning(f"❌ Группа {chat_id} не найдена в состоянии")
        # Пробуем найти группу напрямую из БД
        group_stmt = select(ManagedGroup).where(ManagedGroup.telegram_chat_id == chat_id)
        group_result = await session.execute(group_stmt)
        group_db = group_result.scalar_one_or_none()
        
        if not group_db:
            await callback.answer("❌ Группа не найдена", show_alert=True)
            return
        
        # Используем данные из БД
        group = {
            "chat_id": group_db.telegram_chat_id,
            "chat_title": group_db.telegram_chat_title or f"Группа {chat_id}"
        }
        logger.info(f"✅ Группа найдена в БД: {group['chat_title']}")

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

    # Формируем клавиатуру через get_topics_inline_kb (с заголовком группы!)
    keyboard = get_topics_inline_kb(
        topics=topics_as_dicts,
        group_title=group['chat_title'],
        page=0,
        page_size=5,
        get_text=get_text,
        back_callback="list_back:groups"
    )

    text = (
        f"<b>👥 Группа: {group['chat_title']}</b>\n\n"
        f"<b>📊 Найдено тем:</b> {len(topics)}\n\n"
        f"<i>Выберите тему для просмотра источников:</i>"
    )

    # Обновляем сообщение через update_or_send_menu
    await update_or_send_menu(
        bot=bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=keyboard,
        state=state
    )

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

    # Получаем название темы для заголовка
    topic_name = "Без названия"
    for topic in data.get('current_topics', []):
        if topic.topic_identifier == topic_identifier:
            topic_name = topic.topic_name or "Без названия"
            break

    # Импортируем функцию формирования клавиатуры
    from bot.keyboards import get_source_list_kb

    # Формируем клавиатуру через get_source_list_kb (с заголовком темы!)
    keyboard = get_source_list_kb(
        sources=sources,
        topic_title=topic_name,
        page=0,
        page_size=5,
        get_text=get_text,
        use_subscription_id=True,
        back_callback="list_back:topics"
    )

    text = (
        f"<b>🗨️ Тема: {topic_name}</b>\n\n"
        f"<b>📊 Источники:</b> {len(sources)}\n\n"
        f"<i>Нажмите на источник для перехода или ❌ для удаления</i>"
    )

    # Обновляем сообщение через update_or_send_menu
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=keyboard,
        state=state
    )

    await state.set_state(MySources.viewing_sources)

    # Сохраняем topic_identifier для пагинации
    await state.update_data(current_topic_identifier=topic_identifier, sources_page=0, topic_title=topic_name)


# ========== УДАЛЕНИЕ ИСТОЧНИКА ==========
@router.callback_query(F.data.startswith("del_sub:"))
async def on_delete_source_request(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Показать подтверждение удаления источника"""
    logger.info(f"🔍 CALLBACK del_sub: {callback.data}")

    callback_data = callback.data.split(":")
    if len(callback_data) != 2:
        logger.error(f"❌ Неверный формат callback_data: {callback.data}")
        await callback.answer("❌ Ошибка формата", show_alert=True)
        return

    subscription_id = int(callback_data[1])

    # Находим подписку для получения имени источника
    sub_stmt = select(SourceSubscription).where(
        SourceSubscription.subscription_id == subscription_id
    )
    sub_result = await session.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()

    if not subscription:
        logger.warning(f"❌ Подписка {subscription_id} не найдена")
        await callback.answer("❌ Подписка не найдена", show_alert=True)
        return

    # Получаем имя источника
    source_stmt = select(ContentSource).where(
        ContentSource.source_global_id == subscription.source_global_id
    )
    source_result = await session.execute(source_stmt)
    source = source_result.scalar_one_or_none()

    source_name = "Без названия"
    if source:
        source_name = source.channel_title or source.telegram_username or source.youtube_username or "Без названия"

    # Сохраняем subscription_id в состоянии для последующего удаления
    await state.update_data(pending_delete_subscription_id=subscription_id)

    # Показываем подтверждение
    from bot.keyboards import get_confirm_delete_source_kb

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=f"⚠️ <b>Удалить источник?</b>\n\n📰 {source_name}\n\nВы уверены?",
        keyboard=get_confirm_delete_source_kb(source_name, subscription_id, get_text),
        state=state
    )

    await callback.answer()


@router.callback_query(F.data.startswith("del_sub_confirm:"))
async def on_delete_source_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Подтверждение удаления источника - выполняем удаление"""
    logger.info(f"✅ CALLBACK del_sub_confirm: {callback.data}")

    callback_data = callback.data.split(":")
    if len(callback_data) != 2:
        logger.error(f"❌ Неверный формат callback_data: {callback.data}")
        await callback.answer("❌ Ошибка формата", show_alert=True)
        return

    subscription_id = int(callback_data[1])
    data = await state.get_data()
    current_group = data.get('current_group')
    current_topic_identifier = data.get('current_topic_identifier')
    topic_title = data.get('topic_title', 'Тема')

    try:
        # Находим подписку для получения информации об источнике
        sub_stmt = select(SourceSubscription).where(
            SourceSubscription.subscription_id == subscription_id
        )
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"❌ Подписка {subscription_id} не найдена")
            await callback.answer("❌ Подписка не найдена", show_alert=True)
            return

        topic_identifier = current_topic_identifier
        if not topic_identifier:
            # Находим назначение, чтобы знать, какой топик обновлять
            assign_stmt = select(TopicSourceAssignment).where(
                TopicSourceAssignment.subscription_id == subscription_id
            )
            assign_result = await session.execute(assign_stmt)
            assignment = assign_result.first()
            if assignment:
                topic_identifier = assignment[0].topic_identifier

        logger.info(f"✅ Найдена подписка: source={subscription.source_global_id}, chat={subscription.telegram_chat_id}")

        # Получаем имя источника перед удалением
        source_stmt = select(ContentSource).where(
            ContentSource.source_global_id == subscription.source_global_id
        )
        source_result = await session.execute(source_stmt)
        source = source_result.scalar_one_or_none()

        source_name = "Без названия"
        if source:
            source_name = source.channel_title or source.telegram_username or source.youtube_username or "Без названия"

        # Удаляем только назначение из темы (не всю подписку!)
        assign_to_delete_stmt = select(TopicSourceAssignment).where(
            TopicSourceAssignment.subscription_id == subscription_id,
            TopicSourceAssignment.topic_identifier == topic_identifier
        )
        assign_to_delete_result = await session.execute(assign_to_delete_stmt)
        assignment_to_delete = assign_to_delete_result.scalar_one_or_none()

        if assignment_to_delete:
            await session.delete(assignment_to_delete)
            await session.commit()
            logger.info(f"✅ Назначение удалено: subscription_id={subscription_id}, topic_identifier={topic_identifier}")
        else:
            logger.warning(f"⚠️ Назначение не найдено: subscription_id={subscription_id}, topic_identifier={topic_identifier}")
            await session.rollback()
            await callback.answer("❌ Назначение не найдено", show_alert=True)
            return

        # Проверяем, остались ли другие назначения у этой подписки
        remaining_assignments_stmt = select(TopicSourceAssignment).where(
            TopicSourceAssignment.subscription_id == subscription_id
        )
        remaining_result = await session.execute(remaining_assignments_stmt)
        remaining_assignments = remaining_result.scalars().all()

        if not remaining_assignments:
            # Если назначений не осталось, можно удалить и саму подписку
            await session.delete(subscription)
            await session.commit()
            logger.info(f"✅ Подписка удалена (не осталось назначений): subscription_id={subscription_id}")
        else:
            logger.info(f"✅ Подписка осталась (есть {len(remaining_assignments)} других назначений): subscription_id={subscription_id}")

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

        # Формируем клавиатуру через get_source_list_kb (с заголовком темы!)
        keyboard = get_source_list_kb(
            sources=sources,
            topic_title=topic_title,
            page=page,
            page_size=5,
            get_text=get_text,
            use_subscription_id=True,
            back_callback="list_back:topics"
        )

        page_info = f" ({page + 1}/{total_pages})" if total_pages > 1 else ""
        text = (
            f"<b>🗨️ Тема: {topic_title}</b>{page_info}\n\n"
            f"<b>📊 Источники:</b> {len(sources)}\n\n"
            f"<i>Нажмите на источник для перехода или ❌ для удаления</i>"
        )

        # Импортируем функцию формирования клавиатуры
        from bot.keyboards import get_source_list_kb

        # Формируем клавиатуру через get_source_list_kb (с заголовком темы!)
        keyboard = get_source_list_kb(
            sources=sources,
            topic_title=topic_title,
            page=page,
            page_size=5,
            get_text=get_text,
            use_subscription_id=True,
            back_callback="list_back:topics"
        )

        # 1. Удаляем старое навигационное сообщение ЧЕРЕЗ 2 СЕКУНДЫ
        await delete_menu_message_with_delay(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            state=state,
            delay=2
        )

        # 2. Отправляем НОВОЕ сообщение с результатом
        result_msg = await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=f"✅ <b>{source_name}</b> удалён из темы <b>{topic_title}</b>",
            parse_mode="HTML"
        )
        logger.info(f"📤 Отправлено сообщение о результате: {result_msg.message_id}")

        # 3. Отправляем НОВОЕ навигационное сообщение (обновлённый список)
        new_nav_msg = await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logger.info(f"📤 Отправлено новое навигационное сообщение: {new_nav_msg.message_id}")

        # 4. Сохраняем новый message_id в состоянии
        await state.update_data({MENU_MESSAGE_ID_KEY: new_nav_msg.message_id})

        await callback.answer("✅ Подписка удалена")

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка удаления подписки: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


@router.callback_query(F.data == "del_sub_cancel")
async def on_delete_source_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: callable):
    """Отмена удаления источника"""
    logger.info(f"❌ CALLBACK del_sub_cancel")

    # Очищаем pending_delete_subscription_id из состояния
    data = await state.get_data()
    if 'pending_delete_subscription_id' in data:
        del data['pending_delete_subscription_id']
        await state.set_data(data)

    # Возвращаемся назад к списку источников
    topic_title = data.get('topic_title', 'Тема')
    sources = data.get('current_sources', [])
    sources_page = data.get('sources_page', 0)
    current_topic_identifier = data.get('current_topic_identifier')

    # Если нет current_sources, загружаем из БД
    if not sources and current_topic_identifier:
        current_group = data.get('current_group')
        stmt = (
            select(ContentSource, SourceSubscription, TopicSourceAssignment)
            .join(SourceSubscription, SourceSubscription.source_global_id == ContentSource.source_global_id)
            .join(TopicSourceAssignment, TopicSourceAssignment.subscription_id == SourceSubscription.subscription_id)
            .where(
                TopicSourceAssignment.topic_identifier == current_topic_identifier,
                SourceSubscription.telegram_chat_id == current_group['chat_id']
            )
        )
        result = await session.execute(stmt)
        rows = result.all()
        sources = [
            {
                'source_global_id': row[0].source_global_id,
                'name': row[0].channel_title or row[0].telegram_username or "Без названия",
                'subscription_id': row[1].subscription_id,
                'source_type': row[0].source_type
            }
            for row in rows
        ]

    from bot.keyboards import get_source_list_kb

    keyboard = get_source_list_kb(
        sources=sources,
        topic_title=topic_title,
        page=sources_page,
        page_size=5,
        get_text=get_text,
        use_subscription_id=True,
        back_callback="list_back:topics"
    )

    text = (
        f"<b>🗨️ Тема: {topic_title}</b>\n\n"
        f"<b>📊 Источники:</b> {len(sources)}\n\n"
        f"<i>Нажмите на источник для перехода или ❌ для удаления</i>"
    )

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=keyboard,
        state=state
    )

    await callback.answer("Удаление отменено")


# ========== ПАГИНАЦИЯ ИСТОЧНИКОВ ==========
@router.callback_query(F.data.startswith("sources_page:"))
async def on_sources_page_change(callback: CallbackQuery, session: AsyncSession, state: FSMContext, get_text: callable):
    """Переключение страницы источников"""
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    current_group = data.get('current_group')
    topic_identifier = data.get('current_topic_identifier')
    topic_title = data.get('topic_title', 'Тема')

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

    # Формируем клавиатуру через get_source_list_kb (с заголовком темы!)
    keyboard = get_source_list_kb(
        sources=sources,
        topic_title=topic_title,
        page=page,
        page_size=5,
        get_text=get_text,
        use_subscription_id=True,
        back_callback="list_back:topics"
    )

    page_info = f" ({page + 1}/{total_pages})" if total_pages > 1 else ""
    text = (
        f"<b>🗨️ Тема: {topic_title}</b>{page_info}\n\n"
        f"<b>📊 Источники:</b> {len(sources)}\n\n"
        f"<i>Нажмите на источник для перехода или ❌ для удаления</i>"
    )

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=keyboard,
        state=state
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
        # Главное меню - InlineKeyboardMarkup
        from bot.keyboards import get_main_menu_inline

        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=get_text(['common', 'menu']),
            keyboard=get_main_menu_inline(get_text),
            state=state
        )

        await state.clear()
        await callback.answer()
        return

    elif where_to == "groups":
        # Возврат к списку групп с пагинацией
        from bot.keyboards import get_groups_inline_kb

        # Получаем текущую страницу из состояния
        groups_page = data.get('groups_page', 0)

        # Формируем клавиатуру через get_groups_inline_kb
        keyboard = get_groups_inline_kb(groups=groups, page=groups_page, page_size=5, get_text=get_text, back_callback="back_to_main")

        text = (
            f"<b>📚 Мои источники</b>\n\n"
            f"<b>📊 Найдено групп:</b> {len(groups)}\n\n"
            f"<i>Выберите группу для просмотра тем:</i>"
        )

        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=text,
            keyboard=keyboard,
            state=state
        )

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

        # Формируем клавиатуру через get_topics_inline_kb (с заголовком группы!)
        keyboard = get_topics_inline_kb(
            topics=topics_as_dicts,
            group_title=current_group['chat_title'],
            page=topics_page,
            page_size=5,
            get_text=get_text,
            back_callback="list_back:groups"
        )

        text = (
            f"<b>👥 Группа: {current_group['chat_title']}</b>\n\n"
            f"<b>📊 Найдено тем:</b> {len(topics)}\n\n"
            f"<i>Выберите тему для просмотра источников:</i>"
        )

        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=text,
            keyboard=keyboard,
            state=state
        )

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
    keyboard = get_groups_inline_kb(groups=groups, page=page, page_size=5, get_text=get_text, back_callback="back_to_main")

    text = (
        f"<b>📚 Мои источники</b>\n\n"
        f"<b>📊 Найдено групп:</b> {len(groups)}\n\n"
        f"<i>Выберите группу для просмотра тем:</i>"
    )

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=keyboard,
        state=state
    )

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

    # Формируем клавиатуру через get_topics_inline_kb (с заголовком группы!)
    keyboard = get_topics_inline_kb(
        topics=topics_as_dicts,
        group_title=current_group['chat_title'],
        page=page,
        page_size=5,
        get_text=get_text,
        back_callback="list_back:groups"
    )

    text = (
        f"<b>👥 Группа: {current_group['chat_title']}</b>\n\n"
        f"<b>📊 Найдено тем:</b> {len(topics)}\n\n"
        f"<i>Выберите тему для просмотра источников:</i>"
    )

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=text,
        keyboard=keyboard,
        state=state
    )

    await callback.answer()


# ========== ОТМЕНА ==========
@router.callback_query(F.data == "list_cancel")
async def on_cancel_pressed(callback: CallbackQuery, state: FSMContext, get_text: callable):
    """Отмена просмотра источников - возврат в главное меню (как back_to_main)"""
    # Сохраняем message_id перед очисткой!
    data = await state.get_data()
    menu_message_id = data.get('_menu_message_id')
    logger.info(f"🔙 НАЗАД: сохранён menu_message_id={menu_message_id}")

    await state.clear()

    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({'_menu_message_id': menu_message_id})
        logger.info(f"🔙 НАЗАД: восстановлен menu_message_id={menu_message_id}")

    # Проверяем, что message_id читается
    data_after = await state.get_data()
    logger.info(f"🔙 НАЗАД: после восстановления data={data_after}")

    from bot.keyboards import get_main_menu_inline

    # Обновляем текущее сообщение на главное меню (без fallback_message)
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )

    await callback.answer("✅ Возврат в главное меню")

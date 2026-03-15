# bot/handlers/settings_handler.py
"""
Хендлеры для настроек пользователя.
Версия: 2.3 (20 февраля 2026)
Изменения:
- Исправлена смена языка (set_lang:)
- Убраны конфликтующие хендлеры
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    TelegramAccount,
    UserChannelSubscription,
    SourceSubscription,
    TopicSourceAssignment,
    UserPreferences,
    UserCachedMedia
)
from bot.states import Settings
from bot.keyboards import (
    get_main_menu_inline,
    get_settings_menu_inline,
    get_language_menu,
    get_back_to_settings_kb,
    get_confirm_delete_kb,
    GetTextFunc
)
from bot.utils.menu_message import update_or_send_menu, MENU_MESSAGE_ID_KEY
import core.utils.i18n
from core.redis_client import redis_client
from core.utils.i18n import create_i18n
import bot.middlewares.i18n



logger = logging.getLogger(__name__)
logger.info(f"core.utils.i18n path: {core.utils.i18n.__file__}")
logger.info(f"bot.middlewares.i18n path: {bot.middlewares.i18n.__file__}")
router = Router(name="settings")

# Все кнопки используют локализованный текст через callback

@router.callback_query(
    ~F.data.startswith("set_lang:") &
    ~(F.data == "back_to_settings") &
    ~(F.data == "settings_back") &
    ~(F.data == "settings_lang") &
    ~(F.data == "settings_delete") &
    ~F.data.startswith("list_") &  # Исключаем list_group, list_topic, list_back
    ~F.data.startswith("del_source:") &  # Исключаем del_source (из sources.py)
    ~F.data.startswith("del_sub:")  # Исключаем del_sub (из my_sources_interactive.py)
)
async def debug_callbacks(callback: CallbackQuery):
    """Временный дебаг - логирует все callbacks кроме set_lang, back_to_settings, list_*, del_source, del_sub"""
    logger.info(f"🔥 SETTINGS CALLBACK: {callback.data}")
    # НЕ отвечаем, чтобы не блокировать другие хендлеры



@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext, session: AsyncSession, get_text: GetTextFunc):
    """Показать меню настроек"""
    user_id = message.from_user.id

    # Получаем или создаем настройки пользователя
    stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
    result = await session.execute(stmt)
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = UserPreferences(user_id=user_id, language='en')
        session.add(prefs)
        await session.commit()

    # Используем update_or_send_menu без fallback_message — обновляет текущее message_id
    await update_or_send_menu(
        bot=message.bot,
        chat_id=user_id,
        text=get_text(['settings', 'title']),
        keyboard=get_settings_menu_inline(get_text),
        state=state
    )
    await state.set_state(Settings.main)


# ✅ ЕДИНСТВЕННЫЙ хендлер для смены языка
@router.callback_query(F.data.startswith("set_lang:"))
async def process_language_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка смены языка через callback"""
    lang = callback.data.split(":")[1]
    user_id = callback.from_user.id

    logger.info(f"🌐 Смена языка для пользователя {user_id} на {lang}")

    try:
        # 1. Сохраняем язык в БД
        stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await session.execute(stmt)
        prefs = result.scalar_one_or_none()

        if prefs:
            prefs.language = lang
            logger.info(f"✅ Обновлен язык пользователя {user_id}: {prefs.language} -> {lang}")
        else:
            prefs = UserPreferences(user_id=user_id, language=lang)
            session.add(prefs)
            logger.info(f"✅ Созданы настройки пользователя {user_id} с языком: {lang}")

        await session.commit()
        logger.info(f"✅ Язык {lang} успешно сохранен в БД для пользователя {user_id}")

        # 2. Создаем новую локализацию для ответа
        i18n = create_i18n(lang)
        get_text = i18n.get

        # 3. Отвечаем пользователю
        lang_name = get_text(['settings', f'language_{lang}'])
        await callback.answer(get_text(['settings', 'language_changed'], lang=lang_name))

        # 4. Обновляем команды бота для пользователя
        from bot.main import update_user_commands
        await update_user_commands(callback.bot, user_id, lang)

        # 5. Устанавливаем состояние Settings.main СРАЗУ, чтобы кнопки работали
        await state.set_state(Settings.main)

        # 6. Обновляем меню настроек с новым языком (в том же сообщении)
        await update_or_send_menu(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            text=get_text(['settings', 'title']),
            keyboard=get_settings_menu_inline(get_text),
            state=state
        )

    except Exception as e:
        logger.error(f"❌ Ошибка при смене языка: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при смене языка", show_alert=True)




@router.callback_query(Settings.confirm_delete, F.data == "confirm_delete")
async def confirm_delete_data(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: GetTextFunc):
    """ПОДТВЕРЖДЕНИЕ - удаление всех данных пользователя"""
    user_id = callback.from_user.id
    
    try:
        # 1. Удаляем личные подписки на каналы
        del_user_subs = delete(UserChannelSubscription).where(
            UserChannelSubscription.user_id == user_id
        )
        await session.execute(del_user_subs)
        
        # 2. Удаляем подписки, добавленные пользователем
        del_subs = delete(SourceSubscription).where(
            SourceSubscription.added_by_telegram_account_id == user_id
        )
        await session.execute(del_subs)
        
        # 3. Удаляем темы, созданные пользователем
        from core.models import GroupTopic
        del_topics = delete(GroupTopic).where(
            GroupTopic.created_by_telegram_account_id == user_id
        )
        await session.execute(del_topics)
        
        # 4. Удаляем настройки пользователя
        del_prefs = delete(UserPreferences).where(UserPreferences.user_id == user_id)
        await session.execute(del_prefs)
        
        # 5. Удаляем личный кеш
        del_cache = delete(UserCachedMedia).where(UserCachedMedia.user_id == user_id)
        await session.execute(del_cache)
        
        # 6. Помечаем аккаунт
        acc_stmt = select(TelegramAccount).where(TelegramAccount.telegram_account_id == user_id)
        acc_result = await session.execute(acc_stmt)
        account = acc_result.scalar_one_or_none()
        
        if account:
            account.telegram_username = None
            account.telegram_first_name = "Deleted"
            account.telegram_last_name = "User"
            account.is_bot_blocked = True
        
        await session.commit()
        
        # 7. Очищаем Redis кеш
        try:
            await redis_client.flush()
        except:
            pass

        # Отправляем НОВОЕ сообщение об успехе
        success_msg = await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text(['settings', 'delete_success']),
            parse_mode="HTML"
        )
        logger.info(f"📤 Отправлено сообщение об удалении данных: {success_msg.message_id}")

        # Отправляем НОВОЕ главное меню
        main_menu_msg = await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text(['common', 'menu']),
            parse_mode="HTML",
            reply_markup=get_main_menu_inline(get_text)
        )
        logger.info(f"📤 Отправлено новое главное меню: {main_menu_msg.message_id}")

        # Сохраняем новый message_id в состоянии
        await state.update_data({MENU_MESSAGE_ID_KEY: main_menu_msg.message_id})
        await state.clear()
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка при удалении данных пользователя {user_id}: {e}")
        # Отправляем сообщение об ошибке
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text(['settings', 'delete_error'], error=str(e)[:200]),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(Settings.confirm_delete, F.data == "cancel_delete")
async def cancel_delete_data(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: GetTextFunc):
    """Отмена удаления данных"""
    user_id = callback.from_user.id

    # Получаем текущий язык пользователя из БД
    stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
    result = await session.execute(stmt)
    prefs = result.scalar_one_or_none()

    # Определяем язык для отображения
    current_lang = prefs.language if prefs else 'en'

    # Создаем локализацию с правильным языком
    from core.utils.i18n import create_i18n
    i18n = create_i18n(current_lang)
    get_text = i18n.get

    # Возвращаемся в меню настроек через update_or_send_menu (сообщение обновляется)
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['settings', 'title']),
        keyboard=get_settings_menu_inline(get_text),
        state=state
    )
    await state.set_state(Settings.main)
    await callback.answer()


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: GetTextFunc):
    """Вернуться в меню настроек"""
    user_id = callback.from_user.id

    logger.info(f"🔙 Возврат в настройки для пользователя {user_id}")

    # Получаем текущий язык пользователя из БД
    stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
    result = await session.execute(stmt)
    prefs = result.scalar_one_or_none()

    # Определяем язык для отображения
    current_lang = prefs.language if prefs else 'en'

    # Создаем локализацию с правильным языком
    from core.utils.i18n import create_i18n
    i18n = create_i18n(current_lang)
    get_text = i18n.get

    # Возвращаемся в меню настроек через update_or_send_menu
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['settings', 'title']),
        keyboard=get_settings_menu_inline(get_text),
        state=state
    )
    await state.set_state(Settings.main)
    await callback.answer()


# ========== ОБРАБОТЧИКИ CALLBACK_QUERY ДЛЯ НАСТРОЕК ==========
@router.callback_query(F.data == "settings_lang")
async def on_settings_lang(callback: CallbackQuery, state: FSMContext, get_text: GetTextFunc):
    """Обработчик кнопки "Язык" в настройках"""
    from bot.keyboards import get_language_menu

    await callback.answer()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['keyboards', 'language_menu', 'prompt']),
        keyboard=get_language_menu(get_text),
        state=state
    )
    await state.set_state(Settings.language)


@router.callback_query(F.data == "settings_delete")
async def on_settings_delete(callback: CallbackQuery, state: FSMContext, get_text: GetTextFunc):
    """Обработчик кнопки "Удалить данные" в настройках"""
    from bot.keyboards import get_confirm_delete_kb

    await callback.answer()
    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['settings', 'delete_warning']),
        keyboard=get_confirm_delete_kb(get_text),
        state=state
    )
    await state.set_state(Settings.confirm_delete)


@router.callback_query(F.data == "settings_back")
async def on_settings_back(callback: CallbackQuery, state: FSMContext, get_text: GetTextFunc):
    """Обработчик кнопки "Назад" в настройках"""
    await callback.answer()

    # Сохраняем message_id перед очисткой состояния!
    data = await state.get_data()
    menu_message_id = data.get(MENU_MESSAGE_ID_KEY)

    # Очищаем состояние, КРОМЕ message_id
    await state.clear()

    # Восстанавливаем message_id
    if menu_message_id:
        await state.update_data({MENU_MESSAGE_ID_KEY: menu_message_id})

    await update_or_send_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        text=get_text(['common', 'menu']),
        keyboard=get_main_menu_inline(get_text),
        state=state
    )



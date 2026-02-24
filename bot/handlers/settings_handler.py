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
    get_main_menu,
    get_settings_menu,
    get_language_menu,
    get_back_to_settings_kb,
    get_confirm_delete_kb,
    GetTextFunc
)
import core.utils.i18n
from core.redis_client import redis_client
from core.utils.i18n import create_i18n
import bot.middlewares.i18n



logger = logging.getLogger(__name__)
logger.info(f"core.utils.i18n path: {core.utils.i18n.__file__}")
logger.info(f"bot.middlewares.i18n path: {bot.middlewares.i18n.__file__}")
router = Router(name="settings")

# Константы для текстов кнопок (без локализации в декораторах!)
SETTINGS_BUTTONS = [
    "⚙️ Настройки",
    "⚙️ Settings",
    "⚙️ Налаштування",
    "⚙️ Налады"
]
# Все остальные кнопки используют локализованный текст

@router.callback_query(~F.data.startswith("set_lang:") & ~(F.data == "back_to_settings"))  # Исключаем set_lang и back_to_settings из дебага
async def debug_callbacks(callback: CallbackQuery):
    """Временный дебаг - логирует все callbacks кроме set_lang и back_to_settings"""
    logger.info(f"🔥 CALLBACK: {callback.data}")
    # НЕ отвечаем, чтобы не блокировать другие хендлеры



@router.message(F.text.in_(SETTINGS_BUTTONS))
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
    
    # Текущий язык
    lang_display = get_text(['settings', 'language_ru']) if prefs.language == "ru" else get_text(['settings', 'language_en'])
    
    await message.answer(
        get_text(['settings', 'title'], lang=lang_display),
        parse_mode="HTML",
        reply_markup=get_settings_menu(get_text)
    )
    await state.set_state(Settings.main)


# ========== ЕДИНЫЙ ХЕНДЛЕР МЕНЮ НАСТРОЕК ==========
# В aiogram при return следующий хендлер не вызывается, поэтому все кнопки обрабатываем в одном месте

@router.message(Settings.main)
async def settings_main_menu(message: Message, state: FSMContext, get_text: GetTextFunc):
    """Обработка всех кнопок меню настроек: Назад, Язык, Удаление данных"""
    from core.utils.i18n import create_i18n

    # Собираем тексты кнопок для всех поддерживаемых языков
    i18n_ru = create_i18n('ru')
    i18n_en = create_i18n('en')
    i18n_uk = create_i18n('uk')
    i18n_be = create_i18n('be')

    all_i18n = [i18n_ru, i18n_en, i18n_uk, i18n_be]

    back_texts = [i18n.get(['keyboards', 'settings_menu', 'back']) for i18n in all_i18n]
    lang_texts = [i18n.get(['keyboards', 'settings_menu', 'language']) for i18n in all_i18n]
    delete_texts = [i18n.get(['keyboards', 'settings_menu', 'delete_data']) for i18n in all_i18n]

    text = message.text

    # 1. Кнопка "Назад" → главное меню
    if text in back_texts:
        logger.info(f"✅ Кнопка 'Назад' распознана, возвращаемся в главное меню")
        await message.answer(
            get_text(['common', 'menu']),
            parse_mode="HTML",
            reply_markup=get_main_menu(get_text)
        )
        await state.clear()
        return

    # 2. Кнопка "Язык" → выбор языка (только inline-клавиатура)
    if text in lang_texts:
        await message.answer(
            get_text(['keyboards', 'language_menu', 'prompt']),  # "Выберите язык:"
            reply_markup=get_language_menu(get_text)
        )
        await state.set_state(Settings.language)
        return

    # 3. Кнопка "Удалить данные" → подтверждение
    if text in delete_texts:
        await message.answer(
            get_text(['settings', 'delete_warning']),
            parse_mode="HTML",
            reply_markup=get_confirm_delete_kb(get_text)
        )
        await state.set_state(Settings.confirm_delete)
        return

    # Неизвестная кнопка — показываем меню настроек снова
    logger.debug(f"Неизвестный текст в настройках: '{text}'")


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
        
        # 4. Устанавливаем состояние Settings.main СРАЗУ, чтобы кнопки работали
        await state.set_state(Settings.main)
        
        # 5. Обновляем сообщение с выбором языка (если оно есть)
        try:
            await callback.message.edit_text(
                get_text(['settings', 'language_changed'], lang=lang_name),
                parse_mode="HTML",
                reply_markup=get_back_to_settings_kb(get_text)
            )
            logger.info(f"✅ Сообщение с выбором языка обновлено, добавлена кнопка 'Назад'")
        except Exception as e:
            # Если не удалось обновить (сообщение уже изменено), просто отвечаем
            logger.warning(f"⚠️ Не удалось обновить сообщение с выбором языка: {e}")
            # Отправляем новое сообщение с кнопкой "Назад"
            await callback.message.answer(
                get_text(['settings', 'language_changed'], lang=lang_name),
                parse_mode="HTML",
                reply_markup=get_back_to_settings_kb(get_text)
            )
        
        # 6. Отправляем новое меню настроек
        await callback.message.answer(
            get_text(['settings', 'title'], lang=lang_name),
            parse_mode="HTML",
            reply_markup=get_settings_menu(get_text)
        )
        
        # 7. Отправляем обновленное главное меню
        await callback.message.answer(
            get_text(['common', 'menu']),
            parse_mode="HTML",
            reply_markup=get_main_menu(get_text)
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
        
        await callback.message.edit_text(
            get_text(['settings', 'delete_success']),
            parse_mode="HTML"
        )
        await callback.message.answer(
            get_text(['common', 'menu']),
            parse_mode="HTML",
            reply_markup=get_main_menu(get_text)
        )
        await state.clear()
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка при удалении данных пользователя {user_id}: {e}")
        await callback.message.edit_text(
            get_text(['settings', 'delete_error'], error=str(e)[:200]),
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
    lang_display = get_text(['settings', 'language_ru']) if current_lang == "ru" else get_text(['settings', 'language_en'])
    
    await callback.message.edit_text(
        get_text(['settings', 'delete_cancelled'])
    )
    await callback.message.answer(
        get_text(['settings', 'title'], lang=lang_display),
        parse_mode="HTML",
        reply_markup=get_settings_menu(get_text)
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
    
    lang_display = get_text(['settings', 'language_ru']) if current_lang == "ru" else get_text(['settings', 'language_en'])
    
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    await callback.message.answer(
        get_text(['settings', 'title'], lang=lang_display),
        parse_mode="HTML",
        reply_markup=get_settings_menu(get_text)
    )
    await state.set_state(Settings.main)
    await callback.answer()




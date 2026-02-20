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
    GroupMembership,
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
from core.redis_client import redis_client
from core.utils.i18n import create_i18n

logger = logging.getLogger(__name__)
router = Router(name="settings")

# Константы для текстов кнопок (без локализации в декораторах!)
SETTINGS_BUTTONS = ["⚙️ Настройки", "⚙️ Settings"]
LANGUAGE_BUTTON = "🌐 Язык / Language"
DELETE_DATA_BUTTON = "🗑️ Удалить мои данные"
BACK_BUTTON = "← Назад"


@router.callback_query()
async def debug_all_callbacks(callback: CallbackQuery):
    """ОТЛАДКА: ловим ВСЕ callback'и"""
    logger.info("=" * 50)
    logger.info(f"🔍 ПОЛУЧЕН CALLBACK: {callback.data}")
    logger.info(f"   From user: {callback.from_user.id}")
    logger.info(f"   Message ID: {callback.message.message_id}")
    logger.info("=" * 50)
    # НЕ отвечаем, просто логируем


# bot/handlers/settings_handler.py - добавь после debug_all_callbacks

@router.callback_query(F.data.in_(["lang_ru", "lang_en"]))
async def test_lang_handler(callback: CallbackQuery):
    """ТЕСТОВЫЙ хендлер для языка"""
    logger.info(f"✅ ТЕСТОВЫЙ ХЕНДЛЕР СРАБОТАЛ! data={callback.data}")
    await callback.answer(f"Выбрано: {callback.data}", show_alert=True)



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


# ========== ЯЗЫК ==========

@router.message(Settings.main, F.text == LANGUAGE_BUTTON)
async def settings_language(message: Message, state: FSMContext, get_text: GetTextFunc):
    """Выбор языка"""
    await message.answer(
        get_text(['settings', 'language_prompt']),
        parse_mode="HTML",
        reply_markup=get_language_menu(get_text)  # ← здесь создается клавиатура с set_lang:
    )
    await state.set_state(Settings.language)


# ✅ ВАЖНО: хендлер должен ловить ТОТ ЖЕ ПРЕФИКС, что и в клавиатуре!
@router.callback_query(Settings.language, F.data.startswith("set_lang:"))  # ← ИСПРАВЛЕНО!
async def process_language_choice(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора языка"""
    lang = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    logger.info(f"🌐 Смена языка для {user_id} на {lang}")
    
    try:
        # Сохраняем в БД
        stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await session.execute(stmt)
        prefs = result.scalar_one_or_none()
        
        if prefs:
            prefs.language = lang
        else:
            prefs = UserPreferences(user_id=user_id, language=lang)
            session.add(prefs)
        
        await session.commit()
        
        # Создаем новую локализацию
        from core.utils.i18n import create_i18n
        new_i18n = create_i18n(lang)
        new_get_text = new_i18n.get
        
        # Название языка
        lang_name = new_get_text(['settings', f'language_{lang}'])
        
        # Обновляем сообщение
        await callback.message.edit_text(
            new_get_text(['settings', 'language_changed'], lang=lang_name),
            parse_mode="HTML"
        )
        
        # Отправляем новое меню настроек
        await callback.message.answer(
            new_get_text(['settings', 'title'], lang=lang_name),
            parse_mode="HTML",
            reply_markup=get_settings_menu(new_get_text)
        )
        
        # Отправляем обновленное главное меню
        await callback.message.answer(
            new_get_text(['common', 'menu']),
            parse_mode="HTML",
            reply_markup=get_main_menu(new_get_text)
        )
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка смены языка: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)



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
        else:
            prefs = UserPreferences(user_id=user_id, language=lang)
            session.add(prefs)
        
        await session.commit()
        
        # 2. Создаем новую локализацию для ответа
        i18n = create_i18n(lang)
        get_text = i18n.get
        
        # 3. Отвечаем пользователю
        lang_name = get_text(['settings', f'language_{lang}'])
        
        await callback.answer(get_text(['settings', 'language_changed'], lang=lang_name))
        
        # 4. Обновляем сообщение настроек
        await callback.message.edit_text(
            get_text(['settings', 'title'], lang=lang_name),
            parse_mode="HTML",
            reply_markup=get_settings_menu(get_text)
        )
        
        # 5. Отправляем новое сообщение с главным меню (обновленные кнопки)
        await callback.message.answer(
            get_text(['common', 'menu']),
            parse_mode="HTML",
            reply_markup=get_main_menu(get_text)
        )
        
        # 6. Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при смене языка: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при смене языка", show_alert=True)


@router.message(Settings.main, F.text == DELETE_DATA_BUTTON)
async def settings_delete_data(message: Message, state: FSMContext, get_text: GetTextFunc):
    """Запрос на удаление данных"""
    await message.answer(
        get_text(['settings', 'delete_warning']),
        parse_mode="HTML",
        reply_markup=get_confirm_delete_kb(get_text)
    )
    await state.set_state(Settings.confirm_delete)


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
async def cancel_delete_data(callback: CallbackQuery, state: FSMContext, get_text: GetTextFunc):
    """Отмена удаления данных"""
    await callback.message.edit_text(
        get_text(['settings', 'delete_cancelled'])
    )
    await callback.message.answer(
        get_text(['settings', 'title'], lang=get_text(['settings', 'language_en'])),
        parse_mode="HTML",
        reply_markup=get_settings_menu(get_text)
    )
    await state.set_state(Settings.main)
    await callback.answer()


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery, state: FSMContext, get_text: GetTextFunc):
    """Вернуться в меню настроек"""
    await callback.message.delete()
    await callback.message.answer(
        get_text(['settings', 'title'], lang=get_text(['settings', 'language_en'])),
        parse_mode="HTML",
        reply_markup=get_settings_menu(get_text)
    )
    await state.set_state(Settings.main)
    await callback.answer()


@router.message(Settings.main, F.text == BACK_BUTTON)
async def settings_back_to_main(message: Message, state: FSMContext, get_text: GetTextFunc):
    """Назад в главное меню"""
    await message.answer(
        get_text(['common', 'menu']),
        parse_mode="HTML",
        reply_markup=get_main_menu(get_text)
    )
    await state.clear()
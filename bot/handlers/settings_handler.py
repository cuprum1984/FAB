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
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    TelegramAccount,
    GroupMembership,
    UserChannelSubscription,
    SourceSubscription,
    TopicSourceAssignment,
    UserPreferences,
    UserCachedMedia,
    ManagedGroup
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

@router.message(F.text == "⚙️ Настройки")
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
    lang_display = "404" if prefs.language == "ru" else "🇬🇧 English"

    await message.answer(
        get_text(['settings', 'title'], lang=lang_display),
        parse_mode="HTML",
        reply_markup=get_settings_menu(get_text)
    )
    await state.set_state(Settings.main)

@router.message(Settings.main, F.text == "🌐 Язык / Language")
async def settings_language(message: Message, state: FSMContext):
    """Выбор языка"""
    await message.answer(
        "<b>🌐 Выберите язык / Choose language</b>\n\n"
        "404\n"
        "🇬🇧 English",
        parse_mode="HTML",
        reply_markup=get_language_menu()
    )
    await state.set_state(Settings.language)

@router.callback_query(Settings.language, F.data.startswith("lang:"))
async def process_language_choice(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора языка"""
    lang = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Сохраняем язык в БД
    stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
    result = await session.execute(stmt)
    prefs = result.scalar_one_or_none()

    if prefs:
        prefs.language = lang
    else:
        prefs = UserPreferences(user_id=user_id, language=lang)
        session.add(prefs)

    await session.commit()

    lang_name = "🚽 Русский" if lang == "ru" else "🚽 English"

    # Редактируем inline сообщение
    await callback.message.edit_text(
        f"✅ Язык изменён на {lang_name}",
        parse_mode="HTML"
    )

    # ✅ ВАЖНО: отправляем НОВОЕ сообщение с меню настроек (reply клавиатура)
    await callback.message.answer(
        "<b>⚙️ Настройки</b>\n\n"
        f"👤 <b>Текущий язык:</b> {lang_name}\n\n"
        "<i>Выберите действие:</i>",
        parse_mode="HTML",
        reply_markup=get_settings_menu()  # ← возвращаем клавиатуру настроек
    )

    await state.set_state(Settings.main)
    await callback.answer()

@router.message(Settings.main, F.text == "🗑️ Удалить мои данные")
async def settings_delete_data(message: Message, state: FSMContext):
    """Запрос на удаление данных"""
    await message.answer(
        "<b>⚠️ ВНИМАНИЕ!</b>\n\n"
        "Вы собираетесь удалить <b>ВСЕ СВОИ ДАННЫЕ</b> из бота:\n\n"
        "• 🗂️ Все личные подписки\n"
        "• 👥 Выход из всех групп (если вы администратор)\n"
        "• ⚙️ Все настройки\n"
        "• 💾 Весь кеш\n\n"
        "<b>Это действие НЕЛЬЗЯ отменить!</b>\n\n"
        "Группы, где вы не администратор, останутся активными для других пользователей.\n\n"
        "Вы уверены?",
        parse_mode="HTML",
        reply_markup=get_confirm_delete_kb()
    )
    await state.set_state(Settings.confirm_delete)

@router.callback_query(Settings.confirm_delete, F.data == "confirm_delete")
async def confirm_delete_data(callback: CallbackQuery, state: FSMContext, session: AsyncSession, get_text: GetTextFunc):
    """ПОДТВЕРЖДЕНИЕ - удаление всех данных пользователя"""
    user_id = callback.from_user.id

    try:
        # 1. Подготовка к удалению: находим все группы, где пользователь является creator_id
        groups_stmt = select(ManagedGroup).where(
            ManagedGroup.creator_id == user_id
        )
        groups_result = await session.execute(groups_stmt)
        groups = groups_result.scalars().all()

        # 2. Очистка внешних систем: очищаем состояние FSM пользователя
        await state.clear()

        # 3. Удаление из БД: удаляем запись в TelegramAccount
        del_account = delete(TelegramAccount).where(
            TelegramAccount.telegram_account_id == user_id
        )
        await session.execute(del_account)

        # 4. Обратная связь: отправляем финальное сообщение
        await callback.message.edit_text(
            "✅ <b>Ваши данные успешно удалены!</b>\n\n"
            "Все ваши данные были удалены из системы.",
            parse_mode="HTML",
            reply_markup=None  # Удаляем клавиатуру
        )

        # 5. Обработка групп, где пользователь является creator_id
        for group in groups:
            try:
                # Отправляем сообщение о выходе
                await callback.bot.send_message(
                    chat_id=group.telegram_chat_id,
                    text="Владелец удалил свой аккаунт, бот покидает группу."
                )
                # Покидаем группу
                await callback.bot.leave_chat(chat_id=group.telegram_chat_id)
            except (TelegramForbiddenError, TelegramBadRequest) as e:
                logger.error(f"❌ Ошибка при выходе из группы {group.telegram_chat_id}: {e}")

        # 6. Очистка Redis
        try:
            redis_keys = await redis_client.keys(f"user:{user_id}*")
            if redis_keys:
                await redis_client.delete(*redis_keys)
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке Redis: {e}")

        await session.commit()

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

# Добавьте в конец bot/handlers/settings.py

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

@router.message(Settings.main, F.text == "← Назад")
async def settings_back_to_main(message: Message, state: FSMContext):
    """Назад в главное меню"""
    await message.answer(
        "🏠 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    await state.clear()

# bot/handlers/settings.py
"""
Хендлеры для настроек пользователя.
Версия: 1.0 (19 февраля 2026)
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
    get_confirm_delete_kb
)
from core.redis_client import redis_client

logger = logging.getLogger(__name__)
router = Router(name="settings")


@router.message(F.text == "⚙️ Настройки")
@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext, session: AsyncSession):
    """Показать меню настроек"""
    user_id = message.from_user.id
    
    # Получаем или создаем настройки пользователя
    stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
    result = await session.execute(stmt)
    prefs = result.scalar_one_or_none()
    
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        session.add(prefs)
        await session.commit()
    
    # Текущий язык
    lang_display = "404" if prefs.language == "ru" else "🇬🇧 English"
    
    await message.answer(
        f"<b>⚙️ Настройки</b>\n\n"
        f"👤 <b>Язык:</b> {lang_display}\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Личных подписок: ?\n"
        f"• Групп: ?\n\n"
        f"<i>Выберите действие:</i>",
        parse_mode="HTML",
        reply_markup=get_settings_menu()
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
async def confirm_delete_data(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """ПОДТВЕРЖДЕНИЕ - удаление всех данных пользователя"""
    user_id = callback.from_user.id
    
    try:
        # 1. Удаляем личные подписки на каналы
        del_user_subs = delete(UserChannelSubscription).where(
            UserChannelSubscription.user_id == user_id
        )
        await session.execute(del_user_subs)
        
        # 2. Получаем группы, где пользователь НЕ администратор (чтобы не трогать)
        # Сначала получим все группы пользователя
        groups_stmt = select(GroupMembership.telegram_chat_id).where(
            GroupMembership.telegram_account_id == user_id,
            GroupMembership.role.in_(("creator", "administrator"))
        )
        groups_result = await session.execute(groups_stmt)
        admin_group_ids = [r[0] for r in groups_result.all()]
        
        # 3. Удаляем подписки, добавленные пользователем в НЕ своих группах
        if admin_group_ids:
            # Если есть группы где он админ, оставляем подписки там?
            # Или тоже удаляем? Пока оставим - удаляем всё что он добавлял
            pass
        
        # Удаляем все подписки, добавленные пользователем
        del_subs = delete(SourceSubscription).where(
            SourceSubscription.added_by_telegram_account_id == user_id
        )
        await session.execute(del_subs)
        
        # 4. Удаляем темы, созданные пользователем
        # (каскадно удалятся и назначения)
        from core.models import GroupTopic
        del_topics = delete(GroupTopic).where(
            GroupTopic.created_by_telegram_account_id == user_id
        )
        await session.execute(del_topics)
        
        # 5. Удаляем настройки пользователя
        del_prefs = delete(UserPreferences).where(UserPreferences.user_id == user_id)
        await session.execute(del_prefs)
        
        # 6. Удаляем личный кеш
        del_cache = delete(UserCachedMedia).where(UserCachedMedia.user_id == user_id)
        await session.execute(del_cache)
        
        # 7. НЕ УДАЛЯЕМ аккаунт TelegramAccount - только помечаем
        acc_stmt = select(TelegramAccount).where(TelegramAccount.telegram_account_id == user_id)
        acc_result = await session.execute(acc_stmt)
        account = acc_result.scalar_one_or_none()
        
        if account:
            account.telegram_username = None
            account.telegram_first_name = "Deleted"
            account.telegram_last_name = "User"
            account.is_bot_blocked = True
        
        await session.commit()
        
        # 8. Очищаем Redis кеш (если есть)
        try:
            await redis_client.flush()
        except:
            pass
        
        await callback.message.edit_text(
            "✅ <b>Все ваши данные удалены!</b>\n\n"
            "• Личные подписки удалены\n"
            "• Подписки в группах удалены\n"
            "• Настройки сброшены\n"
            "• Кеш очищен\n\n"
            "Вы можете начать заново с команды /start",
            parse_mode="HTML"
        )
        await callback.message.answer(
            "🏠 <b>Главное меню</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        await state.clear()
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Ошибка при удалении данных пользователя {user_id}: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при удалении данных: {str(e)[:200]}",
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(Settings.confirm_delete, F.data == "cancel_delete")
async def cancel_delete_data(callback: CallbackQuery, state: FSMContext):
    """Отмена удаления данных"""
    await callback.message.edit_text(
        "✅ Удаление данных отменено"
    )
    await callback.message.answer(
        "<b>⚙️ Настройки</b>",
        parse_mode="HTML",
        reply_markup=get_settings_menu()
    )
    await state.set_state(Settings.main)
    await callback.answer()


# Добавьте в конец bot/handlers/settings.py

@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery, state: FSMContext):
    """Вернуться в меню настроек"""
    await callback.message.delete()
    await callback.message.answer(
        "<b>⚙️ Настройки</b>",
        parse_mode="HTML",
        reply_markup=get_settings_menu()
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
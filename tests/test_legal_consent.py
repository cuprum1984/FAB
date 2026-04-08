"""
Тесты для GDPR согласия (Hybrid Consent).

Проверка:
- ✅ /start без согласия — показывает запрос
- ✅ /start с согласием — показывает меню
- ✅ Нажатие "✅ Понятно" — записывает consent_given_at
- ✅ Нажатие "📄 Читать условия" — отправляет документы
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from core.models import TelegramAccount, UserPreferences
from bot.handlers.common import (
    cmd_start,
    on_consent_accept,
    on_legal_read_terms,
)
from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.fsm.state import State
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_message():
    """Создаёт фейковый Message для тестов"""
    message = MagicMock(spec=Message)
    message.from_user = User(
        id=123456,
        is_bot=False,
        first_name="Test",
        username="test_user",
        language_code="ru"
    )
    message.chat = Chat(id=123456, type="private")
    message.bot = AsyncMock()
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_callback():
    """Создаёт фейковый CallbackQuery для тестов"""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(
        id=123456,
        is_bot=False,
        first_name="Test",
        username="test_user",
        language_code="ru"
    )
    callback.message = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.bot = AsyncMock()
    callback.answer = AsyncMock()
    callback.data = "test_callback"
    return callback


@pytest.fixture
def mock_state():
    """Создаёт фейковый FSMContext"""
    state = AsyncMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    return state


@pytest.fixture
def mock_get_text_ru():
    """Функция локализации для русского языка"""
    def get_text(keys, **kwargs):
        texts = {
            ('common', 'start_return'): "👋 <b>С возвращением, {first_name}!</b>\n\n🤖 Бот готов к работе.",
            ('common', 'start_new'): "👋 <b>Добро пожаловать, {first_name}!</b>",
            ('legal', 'welcome_text'): "Текст согласия",
            ('legal', 'consent_success'): "✅ Согласие подтверждено!",
            ('legal', 'legal_title'): "📄 Условия",
        }
        key = tuple(keys) if isinstance(keys, list) else keys
        text = texts.get(key, "Unknown text")
        if '{first_name}' in text:
            text = text.format(first_name=kwargs.get('first_name', 'User'))
        return text
    return get_text


# =============================================================================
# TEST 1: /start без согласия — показывает запрос
# =============================================================================

@pytest.mark.asyncio
async def test_start_no_consent(mock_message, mock_state, db_session, mock_get_text_ru):
    """
    Новый пользователь при /start должен увидеть запрос согласия.
    
    Сценарий:
    1. Пользователь запускает /start
    2. Бот регистрирует пользователя
    3. Бот показывает запрос согласия (не главное меню)
    """
    # Вызываем хендлер
    await cmd_start(
        message=mock_message,
        state=mock_state,
        session=db_session,
        get_text=mock_get_text_ru
    )

    # Проверяем, что пользователь создан
    result = await db_session.execute(
        select(TelegramAccount).where(TelegramAccount.telegram_account_id == 123456)
    )
    user = result.scalar_one_or_none()
    
    assert user is not None, "Пользователь должен быть создан"
    assert user.consent_given_at is None, "Согласие не должно быть дано автоматически"
    
    # Проверяем, что было установлено состояние ожидания согласия
    mock_state.set_state.assert_called()


# =============================================================================
# TEST 2: /start с согласием — показывает меню
# =============================================================================

@pytest.mark.asyncio
async def test_start_with_consent(mock_message, mock_state, db_session, mock_get_text_ru):
    """
    Существующий пользователь с согласием должен увидеть главное меню.
    
    Сценарий:
    1. Пользователь существует и дал согласие
    2. Пользователь запускает /start
    3. Бот показывает главное меню (не запрос согласия)
    """
    # 1️⃣ ПОДГОТОВКА — создаём пользователя с согласием
    old_date = datetime.now(timezone.utc)
    user = TelegramAccount(
        telegram_account_id=123456,
        telegram_username="test_user",
        telegram_first_name="Test",
        consent_given_at=old_date
    )
    db_session.add(user)
    
    prefs = UserPreferences(user_id=123456, language="ru")
    db_session.add(prefs)
    await db_session.commit()

    # Вызываем хендлер
    await cmd_start(
        message=mock_message,
        state=mock_state,
        session=db_session,
        get_text=mock_get_text_ru
    )

    # Проверяем, что состояние было очищено (меню отправлено)
    mock_state.clear.assert_called()


# =============================================================================
# TEST 3: Нажатие "✅ Понятно" — записывает consent_given_at
# =============================================================================

@pytest.mark.asyncio
async def test_consent_accept(mock_callback, mock_state, db_session, mock_get_text_ru):
    """
    Нажатие кнопки "✅ Понятно" должно записать согласие в БД.
    
    Сценарий:
    1. Пользователь нажимает "✅ Понятно"
    2. Бот записывает consent_given_at
    3. Бот показывает главное меню
    """
    # 1️⃣ ПОДГОТОВКА — создаём пользователя БЕЗ согласия
    user = TelegramAccount(
        telegram_account_id=123456,
        telegram_username="test_user",
        telegram_first_name="Test",
        consent_given_at=None
    )
    db_session.add(user)
    await db_session.commit()

    # 2️⃣ ДЕЙСТВИЕ — нажимаем "✅ Понятно"
    mock_callback.data = "consent_accept"
    
    await on_consent_accept(
        callback=mock_callback,
        state=mock_state,
        session=db_session,
        get_text=mock_get_text_ru
    )

    # 3️⃣ ПРОВЕРКА — согласие записано
    await db_session.refresh(user)
    assert user.consent_given_at is not None, "Согласие должно быть записано"
    
    # Проверяем, что состояние очищено
    mock_state.clear.assert_called()
    
    # Проверяем, что ответ был отправлен
    mock_callback.answer.assert_called_with("✅ Согласие подтверждено!")


# =============================================================================
# TEST 4: Нажатие "📄 Читать условия" — отправляет документы
# =============================================================================

@pytest.mark.asyncio
async def test_legal_read_terms(mock_callback, mock_state, mock_get_text_ru):
    """
    Нажатие кнопки "📄 Читать условия" должно отправить документы.
    
    Сценарий:
    1. Пользователь нажимает "📄 Читать условия"
    2. Бот читает файл terms-privacy.md
    3. Бот отправляет документ с кнопкой "✅ Понятно"
    """
    # 1️⃣ ПОДГОТОВКА — мокаем чтение файла
    mock_file_content = "# Условия использования\n\nТекст документов..."
    
    with patch("builtins.open", new_callable=MagicMock) as mock_file:
        mock_file.return_value.__enter__.return_value.read.return_value = mock_file_content
        mock_callback.data = "legal_read_terms"
        
        await on_legal_read_terms(
            callback=mock_callback,
            state=mock_state,
            get_text=mock_get_text_ru
        )

    # 2️⃣ ПРОВЕРКА — документ отправлен
    mock_callback.message.answer.assert_called()
    call_args = mock_callback.message.answer.call_args
    
    # Получаем текст из аргументов
    if call_args and call_args[1]:
        actual_text = call_args[1].get('text', '')
    elif call_args and call_args[0]:
        actual_text = call_args[0][0]
    else:
        pytest.fail("Нет аргументов у вызова answer()")
    
    # Проверяем, что текст содержит документы
    assert mock_file_content in actual_text, f"Текст документа должен быть в сообщении. Получено: {actual_text}"
    
    # Проверяем, что callback.answer() был вызван
    mock_callback.answer.assert_called()


# =============================================================================
# TEST 5: Существующий пользователь без согласия
# =============================================================================

@pytest.mark.asyncio
async def test_existing_user_no_consent(mock_message, mock_state, db_session, mock_get_text_ru):
    """
    Существующий пользователь без согласия должен увидеть запрос.
    
    Сценарий:
    1. Пользователь существует, но consent_given_at = NULL
    2. Пользователь запускает /start
    3. Бот показывает запрос согласия (не главное меню)
    """
    # 1️⃣ ПОДГОТОВКА — создаём пользователя БЕЗ согласия
    user = TelegramAccount(
        telegram_account_id=123456,
        telegram_username="test_user",
        telegram_first_name="Test",
        consent_given_at=None
    )
    db_session.add(user)
    
    prefs = UserPreferences(user_id=123456, language="ru")
    db_session.add(prefs)
    await db_session.commit()

    # Вызываем хендлер
    await cmd_start(
        message=mock_message,
        state=mock_state,
        session=db_session,
        get_text=mock_get_text_ru
    )

    # Проверяем, что согласие НЕ дано
    await db_session.refresh(user)
    assert user.consent_given_at is None, "Согласие не должно появиться автоматически"
    
    # Проверяем, что было установлено состояние ожидания согласия
    mock_state.set_state.assert_called()

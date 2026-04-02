# bot/handlers/payment_info.py
"""
Хендлеры для обязательной информации о платежах.
Требование Telegram: /terms и /support для всех ботов с платежами.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger(__name__)

router = Router(name="payment_info")


@router.message(Command("terms"))
async def cmd_terms(message: Message, get_text):
    """
    Условия использования платежной системы.
    Требование Telegram для всех ботов с платежами.
    """
    text = (
        "📄 <b>Условия использования</b>\n\n"
        "1. <b>Добровольные пожертвования</b>\n"
        "   Все платежи через Telegram Stars являются добровольными "
        "пожертвованиями на развитие проекта.\n\n"
        "2. <b>Возврат средств</b>\n"
        "   Возврат возможен в течение 14 дней после оплаты. "
        "Для возврата напишите в поддержку.\n\n"
        "3. <b>Комиссии</b>\n"
        "   Telegram удерживает комиссию 30% с каждого платежа.\n\n"
        "4. <b>Вывод средств</b>\n"
        "   Stars конвертируются в TON через 21 день после получения.\n\n"
        "5. <b>Поддержка</b>\n"
        "   По вопросам платежей: /support\n\n"
        "<i>Полная версия: <a href='https://telegram.org/tos'>Telegram Terms of Service</a></i>"
    )
    
    await message.answer(text, disable_web_page_preview=True)


@router.message(Command("support"))
async def cmd_support(message: Message, get_text):
    """
    Контакты поддержки по платежам.
    Требование Telegram для всех ботов с платежами.
    """
    # 👇 ЗАМЕНИТЕ НА ВАШ КОНТАКТ
    support_contact = "@m84show"
    
    text = (
        "📞 <b>Поддержка по платежам</b>\n\n"
        "Если у вас возникли проблемы с оплатой:\n\n"
        f"• Напишите нам: {support_contact}\n"
        "• Или создайте тикет в группе поддержки\n\n"
        "⏰ <b>Время ответа:</b> 24-48 часов\n\n"
        "<i>Поддержка Telegram не помогает с покупками внутри бота.</i>"
    )
    
    await message.answer(text)


@router.message(Command("paysupport"))
async def cmd_paysupport(message: Message, get_text):
    """
    Альтернативная команда поддержки (требование Telegram).
    """
    await cmd_support(message, get_text)

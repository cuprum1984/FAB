#!/usr/bin/env python
"""
Бот-помощник для MyAggryBot.
Запускается отдельно от основного бота.
Версия: 1.0 (14 февраля 2026)
"""
import asyncio
import logging
import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from core.settings import settings
from core.database import init_db
from core.redis_client import redis_client
from bot.handlers.helper import router

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота-помощника"""
    logger.info("🚀 Запуск бота-помощника...")
    
    # Инициализация БД
    await init_db()
    logger.info("✅ База данных подключена")
    
    # Подключение к Redis
    await redis_client.init()
    logger.info("✅ Redis подключён")
    
    # Создаём бота и диспетчер
    bot = Bot(token=settings.BOT_TOKEN_HELPER)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключаем роутер
    dp.include_router(router)
    
    logger.info("✅ Бот-помощник запущен, начинаю прослушивание...")
    logger.info(f"🤖 Bot ID: {bot.id}")
    logger.info(f"📡 Метод получения апдейтов: polling")
    
    try:
        # ✅ ВАЖНО: разрешаем все типы апдейтов, включая от ботов
        await dp.start_polling(
            bot, 
            allowed_updates=["message", "channel_post", "edited_message", "message_reaction"]
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в polling: {e}", exc_info=True)
    finally:
        await bot.session.close()
        await redis_client.close()
        logger.info("🔌 Бот-помощник остановлен")


if __name__ == "__main__":
    asyncio.run(main())
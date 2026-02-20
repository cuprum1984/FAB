#!/usr/bin/env python
"""
Основной бот MyAggryBot.
Версия: 5.0 (17 февраля 2026)
Изменения:
- Полный переход на YouTube HTML парсер (вместо RSS)
- Обновлены импорты и компоненты
- Улучшено логирование для нового парсера
- Добавлено закрытие HTML парсера при остановке
"""

import asyncio
import logging
import sys
import os
import signal
from pathlib import Path
from datetime import datetime

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from bot.handlers import settings_handler

from core.settings import settings
from core.database import init_db, async_session, check_db_connection
from core.redis_client import redis_client, check_redis_connection
from core.services.monitoring_service import start_monitoring, stop_monitoring
from core.parser.youtube_simple import get_parser as get_youtube_parser, close_parser as close_youtube_parser
# 👇 ВАЖНО: импортируем middleware
from bot.middlewares import DBSessionMiddleware

# Импортируем хендлеры
from bot.handlers import (
    common,
    sources,
    admin,
    topics_auto,  # авто-сохранение тем
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# Для отладки YouTube HTML парсера
#youtube_html_logger = logging.getLogger('core.parser.youtube_html')
#youtube_html_logger.setLevel(logging.DEBUG if settings.ENV == "development" else logging.INFO)


# Глобальные переменные для graceful shutdown
shutdown_event = asyncio.Event()
tasks: list[asyncio.Task] = []


async def set_bot_commands(bot: Bot):
    """Установка команд бота"""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="help", description="📖 Помощь"),
        BotCommand(command="add", description="➕ Добавить канал"),
        BotCommand(command="list", description="📋 Мои источники"),
        BotCommand(command="mytopics", description="🗂️ Мои темы"),
        BotCommand(command="refresh", description="🔄 Принудительная проверка"),  # ← ЭТУ СТРОКУ
        BotCommand(command="activ", description="✅ Активировать группу"),
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    logger.info(f"✅ Установлено {len(commands)} команд")


async def check_connections() -> bool:
    """Проверка всех подключений перед запуском"""
    try:
        redis_ok = await check_redis_connection()
        if not redis_ok:
            logger.error("❌ Redis не отвечает")
            return False
        logger.info("✅ Redis подключён и работает")
        
        db_ok = await check_db_connection()
        if not db_ok:
            logger.error("❌ База данных не отвечает")
            return False
        logger.info("✅ База данных подключена и работает")
        
        # Инициализируем YouTube HTML парсер
        youtube_parser = get_youtube_parser()
        if youtube_parser:
            logger.info("✅ YouTube HTML парсер инициализирован")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке подключений: {e}")
        return False


async def on_startup(bot: Bot):
    """Действия при запуске"""
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК ОСНОВНОГО БОТА MyAggryBot")
    logger.info(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔧 Режим: {settings.ENV.upper()}")
    logger.info("=" * 50)
    
    try:
        await init_db()
        logger.info("✅ База данных инициализирована")
        
        await redis_client.init()
        logger.info("✅ Redis клиент инициализирован")
        
        if not await check_connections():
            logger.warning("⚠️ Бот будет запущен, но возможны проблемы")
        
        await set_bot_commands(bot)
        
        await start_monitoring(bot, interval_minutes=5)
        logger.info("✅ Мониторинг источников запущен")
        
        logger.info("📦 Компоненты:")
        logger.info("  • Основной бот: v5.0")
        logger.info("  • Парсер YouTube (HTML): v1.0")
        logger.info("  • Парсер Telegram: v4.1")
        logger.info("  • Мониторинг: v4.0")
        logger.info("  • Темы: авто-сохранение через Bot API")
        
        logger.info("=" * 50)
        logger.info("🤖 БОТ ГОТОВ К РАБОТЕ")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}", exc_info=True)
        raise


async def on_shutdown(bot: Bot):
    """Действия при остановке"""
    logger.info("=" * 50)
    logger.info("🛑 ОСТАНОВКА БОТА")
    logger.info(f"📅 Время остановки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    shutdown_event.set()
    
    # Останавливаем мониторинг
    try:
        await stop_monitoring()
        logger.info("✅ Мониторинг остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка при остановке мониторинга: {e}")
    
    # Закрываем YouTube HTML парсер
    try:
        await close_youtube_parser()
        logger.info("✅ YouTube простой парсер закрыт")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии YouTube HTML парсера: {e}")
    
    # Закрываем Redis
    try:
        await redis_client.close()
        logger.info("✅ Redis соединение закрыто")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии Redis: {e}")
    
    # Завершаем фоновые задачи
    if tasks:
        logger.info(f"⏳ Ожидание завершения {len(tasks)} фоновых задач...")
        for task in tasks:
            if not task.done():
                task.cancel()
        
        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5.0)
            logger.info("✅ Все фоновые задачи завершены")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Некоторые задачи не завершились вовремя")
        except Exception as e:
            logger.error(f"❌ Ошибка при завершении задач: {e}")
    
    # Закрываем сессию бота
    try:
        await bot.session.close()
        logger.info("✅ Сессия бота закрыта")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии сессии бота: {e}")
    
    logger.info("=" * 50)
    logger.info("👋 БОТ ОСТАНОВЛЕН")
    logger.info("=" * 50)


def signal_handler():
    """Обработчик сигналов для graceful shutdown"""
    logger.info("📡 Получен сигнал завершения")
    asyncio.create_task(shutdown())


async def shutdown():
    """Функция для graceful shutdown"""
    logger.info("🛑 Запуск процедуры остановки...")


async def main():
    """Главная функция"""
    
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    
    # Выбор хранилища для FSM
    if settings.ENV == "production":
        try:
            redis = await redis_client.get_client()
            storage = RedisStorage(redis)
            logger.info("✅ Используется RedisStorage (production)")
        except Exception as e:
            logger.error(f"❌ Не удалось подключиться к Redis: {e}")
            logger.warning("⚠️ Использую MemoryStorage как fallback")
            storage = MemoryStorage()
            logger.info("✅ Используется MemoryStorage (fallback)")
    else:
        storage = MemoryStorage()
        logger.info("✅ Используется MemoryStorage (режим разработки)")
    
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=False
        )
    )
    
    dp = Dispatcher(storage=storage)
    
    # 👇 👇 👇 ВАЖНО: ПОДКЛЮЧАЕМ MIDDLEWARE ДЛЯ БД 👇 👇 👇
    dp.update.middleware(DBSessionMiddleware())
    logger.info("✅ Middleware для БД подключён")
    
    # Подключаем роутеры
    dp.include_router(sources.router)
    dp.include_router(admin.router)
    dp.include_router(topics_auto.router)  # авто-сохранение тем
    dp.include_router(common.router)
    dp.include_router(settings_handler.router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Информация о боте:")
    logger.info(f"  • Имя: {bot_info.full_name}")
    logger.info(f"  • Username: @{bot_info.username}")
    logger.info(f"  • ID: {bot_info.id}")
    
    try:
        logger.info("🔄 Запуск polling...")
        
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message", 
                "callback_query", 
                "chat_member",
                "my_chat_member",
                "forum_topic_created",  # для тем
                "forum_topic_edited",    # для тем
                "forum_topic_closed",    # для тем
            ],
            handle_signals=False,
            close_bot_session=False,
        )
        
    except TelegramAPIError as e:
        logger.error(f"❌ Ошибка Telegram API: {e}", exc_info=True)
    except asyncio.CancelledError:
        logger.info("🔄 Polling отменён")
    except Exception as e:
        logger.error(f"❌ Необработанная ошибка: {e}", exc_info=True)
    finally:
        try:
            await bot.session.close()
        except:
            pass
        
        try:
            await dp.storage.close()
        except:
            pass
        
        logger.info("🏁 Бот завершил работу")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем (Ctrl+C)")
    except SystemExit:
        logger.info("👋 Системный выход")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка верхнего уровня: {e}", exc_info=True)
        sys.exit(1)
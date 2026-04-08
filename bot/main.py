#!/usr/bin/env python
"""
Основной бот MyAggryBot.
Версия: 5.2 (20 февраля 2026)
Изменения:
- Добавлена локализация для команд бота
- Команды теперь показываются на языке пользователя
"""
import asyncio
import logging
import sys
import os
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from bot.handlers import settings_handler

from core.settings import settings
from core.database import init_db, async_session, check_db_connection
from core.redis_client import redis_client, check_redis_connection
from core.services.monitoring_service import start_monitoring, stop_monitoring
from core.parser.youtube_simple import get_parser as get_youtube_parser, close_parser as close_youtube_parser
from core.models import UserPreferences
from core.utils.i18n import create_i18n
from core.tasks.dispatcher import TaskDispatcher, set_dispatcher

# 👇 Middleware
from bot.middlewares import DBSessionMiddleware
from bot.middlewares.i18n import I18nMiddleware
from bot.middlewares.group_filter import GroupCommandFilterMiddleware
from bot.middlewares.callback_filter import CallbackQueryFilterMiddleware  # 👈 НОВЫЙ

# Импортируем хендлеры
from bot.handlers import (
    common,
    sources,
    admin,
    topics_auto,
    settings_handler,
    my_sources_interactive,
    support,
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

# Глобальные переменные для graceful shutdown
shutdown_event = asyncio.Event()
tasks: list[asyncio.Task] = []
task_dispatcher: Optional[TaskDispatcher] = None


async def set_bot_commands(bot: Bot):
    """Установка команд бота с русским языком по умолчанию"""
    # Русские команды (для всех новых пользователей)
    # Оставлены только: /start, /activ, /plus, /donate
    ru_commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="activ", description="[OK] Активировать группу"),
        BotCommand(command="plus", description="➕ Добавить тему"),
        BotCommand(command="donate", description="💎 Поддержать автора"),
    ]

    # Английские команды
    en_commands = [
        BotCommand(command="start", description="🚀 Start bot"),
        BotCommand(command="activ", description="[OK] Activate group"),
        BotCommand(command="plus", description="➕ Add topic"),
        BotCommand(command="donate", description="💎 Support author"),
    ]

    # Устанавливаем русские команды как default
    await bot.set_my_commands(ru_commands, scope=BotCommandScopeDefault())
    logger.info(f"[OK] Установлены команды по умолчанию (русский)")

    # Здесь мы не можем установить команды для каждого пользователя индивидуально,
    # потому что это нужно делать при каждом запуске бота.
    # Вместо этого, команды будут обновляться при смене языка через отдельный хендлер


async def update_user_commands(bot: Bot, user_id: int, language: str):
    """Обновить команды для конкретного пользователя"""
    if language == "en":
        commands = [
            BotCommand(command="start", description="🚀 Start bot"),
            BotCommand(command="activ", description="[OK] Activate group"),
            BotCommand(command="plus", description="➕ Add topic"),
            BotCommand(command="donate", description="💎 Support author"),
        ]
    else:
        commands = [
            BotCommand(command="start", description="🚀 Запустить бота"),
            BotCommand(command="activ", description="[OK] Активировать группу"),
            BotCommand(command="plus", description="➕ Добавить тему"),
            BotCommand(command="donate", description="💎 Поддержать автора"),
        ]

    scope = BotCommandScopeChat(chat_id=user_id)
    await bot.set_my_commands(commands, scope=scope)
    logger.info(f"[OK] Обновлены команды для пользователя {user_id}: {language}")


async def check_connections() -> bool:
    """Проверка всех подключений перед запуском"""
    try:
        redis_ok = await check_redis_connection()
        if not redis_ok:
            logger.error("[ERROR] Redis не отвечает")
            return False
        logger.info("[OK] Redis подключён и работает")
        
        db_ok = await check_db_connection()
        if not db_ok:
            logger.error("[ERROR] База данных не отвечает")
            return False
        logger.info("[OK] База данных подключена и работает")
        
        # Инициализируем YouTube HTML парсер
        youtube_parser = get_youtube_parser()
        if youtube_parser:
            logger.info("[OK] YouTube HTML парсер инициализирован")
        
        return True
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при проверке подключений: {e}")
        return False


async def on_startup(bot: Bot):
    """Действия при запуске"""
    global task_dispatcher

    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК ОСНОВНОГО БОТА MyAggryBot")
    logger.info(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔧 Режим: {settings.ENV.upper()}")
    logger.info("=" * 50)

    try:
        await init_db()
        logger.info("[OK] База данных инициализирована")

        await redis_client.init()
        logger.info("[OK] Redis клиент инициализирован")

        if not await check_connections():
            logger.warning("[WARN] Бот будет запущен, но возможны проблемы")

        await set_bot_commands(bot)

        # ✅ ЗАПУСК ЧЕРЕЗ TASKDISPATCHER
        task_dispatcher = TaskDispatcher(bot)
        set_dispatcher(task_dispatcher)
        asyncio.create_task(task_dispatcher.start_all(), name="task_dispatcher_start")

        logger.info("[OK] Мониторинг источников запущен через TaskDispatcher")

        logger.info("📦 Компоненты:")
        logger.info("  • Основной бот: v5.2")
        logger.info("  • Парсер YouTube (HTML): v1.0")
        logger.info("  • Парсер Telegram: v4.1")
        logger.info("  • Мониторинг: v4.0")
        logger.info("  • Локализация: i18n (en/ru)")
        logger.info("  • Темы: авто-сохранение через Bot API")
        logger.info("  • TaskDispatcher: v6.1")

        logger.info("=" * 50)
        logger.info("[BOT] БОТ ГОТОВ К РАБОТЕ")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"[ERROR] Критическая ошибка при запуске: {e}", exc_info=True)
        raise


async def on_shutdown(bot: Bot):
    """Действия при остановке"""
    global task_dispatcher

    logger.info("=" * 50)
    logger.info("🛑 ОСТАНОВКА БОТА")
    logger.info(f"📅 Время остановки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    shutdown_event.set()

    # ✅ ОСТАНОВКА ЧЕРЕЗ TASKDISPATCHER
    if task_dispatcher:
        try:
            await task_dispatcher.stop_all()
            logger.info("[OK] TaskDispatcher остановлен")
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при остановке TaskDispatcher: {e}")

    # Останавливаем мониторинг (для обратной совместимости)
    try:
        await stop_monitoring()
        logger.info("[OK] Мониторинг остановлен")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при остановке мониторинга: {e}")

    # Закрываем YouTube HTML парсер
    try:
        await close_youtube_parser()
        logger.info("[OK] YouTube простой парсер закрыт")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при закрытии YouTube HTML парсера: {e}")

    # Закрываем Redis
    try:
        await redis_client.close()
        logger.info("[OK] Redis соединение закрыто")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при закрытии Redis: {e}")

    # Завершаем фоновые задачи
    if tasks:
        logger.info(f"⏳ Ожидание завершения {len(tasks)} фоновых задач...")
        for task in tasks:
            if not task.done():
                task.cancel()

        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5.0)
            logger.info("[OK] Все фоновые задачи завершены")
        except asyncio.TimeoutError:
            logger.warning("[WARN] Некоторые задачи не завершились вовремя")
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при завершении задач: {e}")

    # Закрываем сессию бота
    try:
        await bot.session.close()
        logger.info("[OK] Сессия бота закрыта")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при закрытии сессии бота: {e}")

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
            
            # ✅ TTL из настроек (300 = 5 мин, 86400 = 24 часа, 0 = без TTL)
            state_ttl = settings.FSM_STATE_TTL if settings.FSM_STATE_TTL > 0 else None
            
            storage = RedisStorage(
                redis,
                state_ttl=state_ttl
            )
            ttl_str = f"{state_ttl} сек" if state_ttl else "без TTL"
            logger.info(f"[OK] Используется RedisStorage с TTL {ttl_str} (production)")
        except Exception as e:
            logger.error(f"[ERROR] Не удалось подключиться к Redis: {e}")
            logger.warning("[WARN] Использую MemoryStorage как fallback")
            storage = MemoryStorage()
            logger.info("[OK] Используется MemoryStorage (fallback)")
    else:
        storage = MemoryStorage()
        logger.info("[OK] Используется MemoryStorage (режим разработки)")
    
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=False
        )
    )
    
    dp = Dispatcher(storage=storage)

    # 👇 ВАЖНО: ПРАВИЛЬНЫЙ ПОРЯДОК MIDDLEWARE 👇
    dp.message.middleware(DBSessionMiddleware())      # 1. Сначала БД
    dp.callback_query.middleware(DBSessionMiddleware())  # 1. Для callback тоже БД
    dp.message.middleware(GroupCommandFilterMiddleware())  # 👈 Команды в группах/ЛС
    dp.callback_query.middleware(CallbackQueryFilterMiddleware())  # 👈 Callback только в ЛС
    dp.message.middleware(I18nMiddleware())           # 2. Потом i18n для сообщений
    dp.callback_query.middleware(I18nMiddleware())    # 3. И для callback (ОДИН РАЗ!)
    logger.info("[OK] Middleware для БД, i18n и фильтрации подключены")

    # Подключаем роутеры
    dp.include_router(common.router)
    dp.include_router(my_sources_interactive.router)  # Интерактивные источники (РАНЬШЕ sources!)
    dp.include_router(sources.router)
    dp.include_router(admin.router)
    dp.include_router(topics_auto.forum_router)  # Служебные события тем
    dp.include_router(topics_auto.router)  # Обычные сообщения
    dp.include_router(support.router)  # Поддержка (донаты) — РАНЬШЕ settings!
    dp.include_router(settings_handler.router)  # Настройки
    logger.info("[OK] Роутеры подключены")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # =========================================
    # ПОДКЛЮЧЕНИЕ К TELEGRAM API
    # =========================================
    try:
        bot_info = await bot.get_me()
        logger.info(f"[OK] Успешное подключение к Telegram API")
        logger.info(f"[BOT] Информация о боте:")
        logger.info(f"  - Имя: {bot_info.full_name}")
        logger.info(f"  - Username: @{bot_info.username}")
        logger.info(f"  - ID: {bot_info.id}")
    except Exception as e:
        logger.error(f"[ERROR] Не удалось подключиться к Telegram API: {e}")
        logger.warning("[WARN] Возможные причины:")
        logger.warning("  - Нет доступа к api.telegram.org (проверьте интернет)")
        logger.warning("  - Требуется прокси (если Telegram заблокирован)")
        logger.warning("  - Неверный токен бота в .env")
        logger.warning("[INFO] Для разработки можно запустить тесты без бота: pytest tests/ -v")
        return  # Завершаем программу, если нет подключения
    
    # =========================================
    # ЗАПУСК POLLING
    # =========================================
    try:
        logger.info("[LOOP] Запуск polling...")

        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "chat_member",
                "my_chat_member",
                "forum_topic_created",
                "forum_topic_edited",
                "forum_topic_closed",
            ],
            handle_signals=False,
            close_bot_session=False,
        )
        
    except TelegramAPIError as e:
        logger.error(f"[ERROR] Ошибка Telegram API: {e}", exc_info=True)
    except asyncio.CancelledError:
        logger.info("[INFO] Polling отменён")
    except OSError as e:
        # Ошибки сети (DNS, подключение)
        logger.error(f"[ERROR] Ошибка сети: {e}", exc_info=True)
        logger.error("[INFO] Проверьте:")
        logger.error("  - Подключение к интернету")
        logger.error("  - Доступность api.telegram.org")
        logger.error("  - Настройки прокси (если требуется)")
    except Exception as e:
        logger.error(f"[ERROR] Необработанная ошибка: {e}", exc_info=True)
    finally:
        try:
            await bot.session.close()
        except:
            pass
        
        try:
            await dp.storage.close()
        except:
            pass
        
        logger.info("[END] Бот завершил работу")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем (Ctrl+C)")
    except SystemExit:
        logger.info("👋 Системный выход")
    except Exception as e:
        logger.error(f"[ERROR] Критическая ошибка верхнего уровня: {e}", exc_info=True)
        sys.exit(1)
# core/tasks/dispatcher.py
"""
TaskDispatcher - диспетчер фоновых задач.
Централизованное управление запуском и остановкой задач.
"""
import asyncio
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """
    Диспетчер задач для управления фоновыми процессами.
    
    Отвечает за:
    - Запуск всех фоновых задач из одной точки
    - Graceful shutdown при остановке бота
    - Отслеживание состояния задач
    """

    def __init__(self, bot):
        self.bot = bot
        self.tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._is_running = False

    async def start_all(self):
        """
        Запустить все фоновые задачи.
        Вызывается из bot/main.py при старте бота.
        """
        if self._is_running:
            logger.warning("⚠️ TaskDispatcher уже запущен")
            return

        self._is_running = True
        self._shutdown_event.clear()

        logger.info("=" * 50)
        logger.info("🚀 ЗАПУСК ФОНОВЫХ ЗАДАЧ")
        logger.info("=" * 50)

        # Запускаем мониторинг источников
        await self._start_monitoring()

        logger.info(f"[OK] Запущено задач: {len(self.tasks)}")
        logger.info("=" * 50)

    async def stop_all(self):
        """
        Остановить все фоновые задачи (graceful shutdown).
        Вызывается из bot/main.py при остановке бота.
        """
        if not self._is_running:
            return

        logger.info("=" * 50)
        logger.info("🛑 ОСТАНОВКА ФОНОВЫХ ЗАДАЧ")
        logger.info("=" * 50)

        self._is_running = False
        self._shutdown_event.set()

        # Отменяем все задачи
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Ждём завершения задач
        if self.tasks:
            logger.info(f"⏳ Ожидание завершения {len(self.tasks)} задач...")

            try:
                results = await asyncio.gather(*self.tasks, return_exceptions=True)

                cancelled = sum(1 for r in results if isinstance(r, asyncio.CancelledError))
                errors = sum(1 for r in results if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError))

                logger.info(f"[OK] Задачи завершены: {cancelled} отменено, {errors} с ошибками")

            except Exception as e:
                logger.error(f"❌ Ошибка при остановке задач: {e}")

        self.tasks.clear()
        logger.info("=" * 50)

    async def _start_monitoring(self):
        """Запустить задачу мониторинга источников."""
        from core.services.monitoring.base import MonitoringService

        try:
            monitoring = MonitoringService(self.bot)

            async def run_monitoring():
                await monitoring.start(interval_minutes=5)

            task = asyncio.create_task(run_monitoring(), name="monitoring_task")
            self.tasks.append(task)

            logger.info("[OK] Запущен мониторинг источников")

        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {e}", exc_info=True)

    def get_task_info(self) -> dict:
        """Получить информацию о задачах."""
        return {
            "is_running": self._is_running,
            "task_count": len(self.tasks),
            "tasks": [
                {
                    "name": task.get_name(),
                    "done": task.done(),
                    "cancelled": task.cancelled()
                }
                for task in self.tasks
            ]
        }

    async def wait_for_shutdown(self):
        """Ждать сигнала остановки."""
        await self._shutdown_event.wait()


# Глобальный экземпляр (опционально)
_dispatcher: Optional[TaskDispatcher] = None


def get_dispatcher() -> Optional[TaskDispatcher]:
    """Получить глобальный экземпляр диспетчера."""
    return _dispatcher


def set_dispatcher(dispatcher: TaskDispatcher):
    """Установить глобальный экземпляр диспетчера."""
    global _dispatcher
    _dispatcher = dispatcher

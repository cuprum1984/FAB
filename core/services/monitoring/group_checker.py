# core/services/monitoring/group_checker.py
"""
Проверка статуса групп (2 раза в день).
"""
import asyncio
import logging

from sqlalchemy import select

from core.models import ManagedGroup
from core.database import async_session

logger = logging.getLogger(__name__)


class GroupChecker:
    """Проверка статуса групп."""

    def __init__(self, bot, monitoring_service):
        self.bot = bot
        self.monitoring = monitoring_service

    async def check_groups_status(self, session):
        """Проверить статус всех активных групп (доступны ли они)"""
        logger.info("🏢 Проверяю статус групп...")

        try:
            # Получаем все активные группы
            stmt = select(ManagedGroup).where(ManagedGroup.is_bot_active_in_group == True)
            result = await session.execute(stmt)
            groups = result.scalars().all()

            logger.info(f"📊 Найдено активных групп: {len(groups)}")

            for group in groups:
                try:
                    # Пробуем получить информацию о группе
                    await self.bot.get_chat(group.telegram_chat_id)
                    logger.debug(f"✅ Группа {group.telegram_chat_id} доступна")

                except Exception as e:
                    error_text = str(e).lower()

                    # Если группа не найдена - помечаем как неактивную
                    if "chat not found" in error_text or "group not found" in error_text:
                        logger.warning(f"🏚️ Группа {group.telegram_chat_id} не найдена (удалена?), помечаю неактивной")
                        group.is_bot_active_in_group = False

                    elif "bot was kicked" in error_text or "forbidden" in error_text:
                        logger.warning(f"👢 Бот удалён из группы {group.telegram_chat_id}, помечаю неактивной")
                        group.is_bot_active_in_group = False

                    else:
                        logger.error(f"❌ Ошибка при проверке группы {group.telegram_chat_id}: {e}")

            await session.commit()
            logger.info(f"✅ Проверка групп завершена, обновлено групп: {len(groups)}")

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка при проверке групп: {e}")

    async def schedule_groups_check(self):
        """Запускать проверку групп 2 раза в день (каждые 12 часов)"""
        while self.monitoring.is_running:
            try:
                async with async_session() as session:
                    await self.check_groups_status(session)

                # Ждём 12 часов до следующей проверки
                logger.info("⏳ Следующая проверка групп через 12 часов")
                for _ in range(12 * 3600):  # 12 часов в секундах
                    if not self.monitoring.is_running:
                        break
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ Ошибка в schedule_groups_check: {e}")
                await asyncio.sleep(3600)  # Если ошибка, ждём час и пробуем снова

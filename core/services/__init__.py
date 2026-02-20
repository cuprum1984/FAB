# core/services/__init__.py
"""
Инициализация сервисов.
Версия: 1.2 (17 февраля 2026)
Изменения:
- Удалены все MTProto компоненты (topic_fetcher)
- Оставлены только основные сервисы
"""
from typing import Optional
from core.settings import settings

# Все сервисы импортируются напрямую:
# from core.services.destination_service import ...
# from core.services.monitoring_service import ...
# from core.services.youtube_service import ...
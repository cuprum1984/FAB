# core/redis_client.py
"""
Redis клиент для MyAggryBot.
Версия: 1.2 (14 февраля 2026)
Изменения:
- Добавлена персистентность для FakeRedis через файл
- Улучшена обработка ошибок
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import fnmatch

logger = logging.getLogger(__name__)

# Определяем окружение
IS_DEVELOPMENT = os.environ.get("ENV") != "production"

if IS_DEVELOPMENT:
    # Режим разработки - используем FileFakeRedis
    try:
        from fakeredis import FakeRedis
        logger.info("✅ FakeRedis импортирован (режим разработки)")
    except ImportError:
        logger.error("❌ FakeRedis не установлен! pip install fakeredis==2.25.0")
        raise
else:
    # Режим продакшена - нужен настоящий Redis
    import redis.asyncio as redis


class FileFakeRedis:
    """
    FakeRedis с сохранением в файл для персистентности между запусками.
    """
    def __init__(self, db_path: str = "redis_data.json"):
        self.db_path = Path(db_path)
        self.data: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """Загрузить данные из файла"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info(f"✅ Загружено {len(self.data)} записей из {self.db_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки из файла: {e}")
                self.data = {}
    
    def _save(self):
        """Сохранить данные в файл"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.debug(f"💾 Сохранено {len(self.data)} записей в {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в файл: {e}")
    
    async def get(self, key: str) -> Optional[str]:
        """Получить значение по ключу"""
        value = self.data.get(key)
        logger.debug(f"📖 GET {key}: {value}")
        return value
    
    async def setex(self, key: str, ttl: int, value: str):
        """Установить значение с TTL"""
        self.data[key] = {
            'value': value,
            'ttl': ttl,
            'expires_at': None  # в простой реализации игнорируем TTL
        }
        self._save()
        logger.debug(f"📝 SET {key}: {value}")
    
    async def delete(self, key: str):
        """Удалить ключ"""
        if key in self.data:
            del self.data[key]
            self._save()
            logger.debug(f"🗑️ DELETE {key}")
    
    async def ping(self) -> bool:
        """Проверить соединение"""
        return True
    
    async def close(self):
        """Закрыть соединение"""
        self._save()
        logger.info("🔌 FileFakeRedis закрыт")


class RedisClient:
    """Синглтон для Redis подключения"""
    _instance = None
    _redis = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def init(self):
        """Инициализация подключения"""
        if self._redis is None:
            if IS_DEVELOPMENT:
                # FileFakeRedis - сохраняет данные между запусками
                self._redis = FileFakeRedis(db_path="redis_data.json")
                logger.info("🌱 FileFakeRedis запущен (данные сохраняются в redis_data.json)")
            else:
                # Настоящий Redis для продакшена
                from core.settings import settings
                redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
                self._redis = await redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                logger.info("✅ Redis подключен (продакшен)")
        
        return self._redis
    
    @property
    async def client(self):
        """Получить клиент Redis"""
        if self._redis is None:
            await self.init()
        return self._redis
    
    async def get_client(self):
        """Получить Redis клиент (alias для client)"""
        return await self.client
    
    async def close(self):
        """Закрыть соединение"""
        if self._redis:
            if hasattr(self._redis, 'close'):
                await self._redis.close()
            self._redis = None
            logger.info("🔌 Redis соединение закрыто")

    async def keys(self, pattern: str):
        """Получить список ключей, соответствующих шаблону"""
        client = await self.client
        if hasattr(client, 'keys'):
            return await client.keys(pattern)
        # fallback for FileFakeRedis
        return [k for k in client.data.keys() if fnmatch.fnmatch(k, pattern)]

    async def delete(self, *keys):
        """Удалить указанные ключи"""
        client = await self.client
        if hasattr(client, 'delete'):
            return await client.delete(*keys)
        # fallback for FileFakeRedis
        for k in keys:
            await client.delete(k)


# Глобальный экземпляр
redis_client = RedisClient()


# ========== ФУНКЦИИ ДЛЯ ПРОВЕРКИ ==========

async def check_redis_connection() -> bool:
    """Проверить подключение к Redis"""
    try:
        client = await redis_client.get_client()
        if hasattr(client, 'ping'):
            return await client.ping()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Redis: {e}")
        return False


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С КЕШЕМ ==========

async def get_cached_last_post(username: str) -> Optional[int]:
    """Получить ID последнего поста из кеша"""
    try:
        client = await redis_client.client
        value = await client.get(f"last_post:{username}")
        if value:
            if isinstance(value, dict):
                return int(value.get('value', 0))
            return int(value)
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения кеша для @{username}: {e}")
        return None


async def set_cached_last_post(username: str, post_id: int, ttl: int = 3600):
    """Сохранить ID последнего поста в кеш (TTL 1 час)"""
    try:
        client = await redis_client.client
        if hasattr(client, 'setex'):
            await client.setex(f"last_post:{username}", ttl, str(post_id))
        else:
            await client.setex(f"last_post:{username}", ttl, str(post_id))
        logger.info(f"✅ Кеш обновлён для @{username}: {post_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения кеша для @{username}: {e}")


async def invalidate_source_cache(username: str):
    """Сбросить кеш источника"""
    try:
        client = await redis_client.client
        await client.delete(f"last_post:{username}")
        logger.debug(f"🗑️ Кеш для @{username} сброшен")
    except Exception as e:
        logger.error(f"❌ Ошибка сброса кеша для @{username}: {e}")
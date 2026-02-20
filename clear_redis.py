import redis
import asyncio
from core.redis_client import redis_client

async def clear_redis():
    """Очистить все ключи Redis"""
    client = await redis_client.client
    await client.flushall()
    print("✅ Redis очищен")

if __name__ == "__main__":
    asyncio.run(clear_redis())
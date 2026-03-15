# test_connection.py
import asyncio
import asyncpg
import redis.asyncio as redis

async def test():
    # Тест PostgreSQL
    pg = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/myaggrybot")
    version = await pg.fetchval("SELECT version()")
    print(f"✅ PostgreSQL: {version[:60]}...")
    await pg.close()
    
    # Тест Redis
    r = await redis.from_url("redis://localhost:6379/0")
    await r.set("test", "Hello from venv!")
    value = await r.get("test")
    print(f"✅ Redis: {value.decode()}")
    await r.aclose()

asyncio.run(test())
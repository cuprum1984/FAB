import asyncio
from core.parser.telegram_posts import get_new_posts

async def test_test_mab():
    print("🔍 Тестирую @testmabch...")
    
    # 1. Смотрим что приходит без last_id
    posts = await get_new_posts("testmabch", None)  # ✅ ИСПРАВЛЕНО
    print(f"📦 Всего постов: {len(posts)}")
    for p in posts[:5]:
        print(f"  - ID: {p['post_id']}, текст: {p['text'][:30]}")
    
    # 2. Проверяем с last_id=1
    posts2 = await get_new_posts("testmabch", "1")  # ✅ ИСПРАВЛЕНО
    print(f"\n🆕 Новые после ID=1: {len(posts2)} постов")
    for p in posts2:
        print(f"  + ID: {p['post_id']}")

asyncio.run(test_test_mab())
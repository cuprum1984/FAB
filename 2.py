#!/usr/bin/env python
"""
Тестовый скрипт для YouTube HTML парсера.
Использование: python 2.py <username>
Пример: python 2.py @MackNack
Пример: python 2.py @24Канал
"""

import asyncio
import sys
import logging
from core.parser.youtube_html import get_parser

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_youtube_channel(username: str):
    """Тестирует получение видео из YouTube канала через HTML"""
    
    print(f"\n🔍 Тестирую YouTube канал: @{username}")
    print("=" * 60)
    
    parser = get_parser()
    
    try:
        # 1. Определяем язык канала
        print("1️⃣ Определяю язык канала...")
        channel_language = await parser.detect_channel_language(username)
        print(f"   ✅ Язык: {channel_language}")
        
        # 2. Получаем данные канала
        print("\n2️⃣ Получаю данные канала...")
        channel_data = await parser.get_channel_data(username, channel_language)
        
        if not channel_data:
            print("   ❌ Не удалось получить данные канала")
            return
        
        print(f"   ✅ Channel ID: {channel_data['channel_id']}")
        print(f"   📺 Название: {channel_data['channel_title']}")
        print(f"   🆔 Последнее видео: {channel_data['video_id']}")
        
        from datetime import datetime
        if channel_data.get('timestamp'):
            dt = datetime.fromtimestamp(channel_data['timestamp'])
            print(f"   📅 Опубликовано: {dt.strftime('%d.%m.%Y %H:%M')}")
        
        # 3. Получаем последнее видео отдельно
        print("\n3️⃣ Получаю только последнее видео...")
        latest = await parser.get_latest_video(username, channel_language)
        if latest:
            print(f"   ✅ Видео ID: {latest['video_id']}")
            print(f"   🔗 Ссылка: {latest['url']}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await parser.close()
        print("\n🔌 Сессия закрыта")

async def main():
    if len(sys.argv) < 2:
        print("❌ Укажите username канала")
        print("Примеры:")
        print("  python 2.py @MackNack")
        print("  python 2.py @24Канал")
        return
    
    username = sys.argv[1].strip('@')
    await test_youtube_channel(username)

if __name__ == "__main__":
    asyncio.run(main())
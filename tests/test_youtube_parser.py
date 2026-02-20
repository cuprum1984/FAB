#!/usr/bin/env python
"""
Тестовый скрипт для YouTube парсера.
Запуск: python tests/test_youtube_parser.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent.parent))

from core.parser.youtube import get_parser, close_parser
from core.parser.youtube import YouTubeParser


async def test_extract_channel_id():
    """Тест извлечения channel_id из разных форматов ссылок"""
    print("\n" + "="*60)
    print("🔍 ТЕСТ 1: Извлечение channel_id")
    print("="*60)
    
    parser = YouTubeParser()
    
    test_cases = [
        # (входные данные, ожидаемый результат или None)
        ("@TheBrainDit", None),  # должен найти channel_id через HTML
        ("https://youtube.com/@TheBrainDit", None),
        ("https://youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw", "UC_x5XG1OV2P6uZZ5FSM9Ttw"),
        ("TheBrainDit", None),
        ("https://youtu.be/CXMHtw7uWwY", None),  # видео, не канал
    ]
    
    for input_str, expected in test_cases:
        print(f"\n📥 Вход: {input_str}")
        try:
            channel_id = await parser.extract_channel_id(input_str)
            print(f"📤 Результат: {channel_id}")
            
            if expected:
                if channel_id == expected:
                    print("✅ УСПЕХ: совпадает с ожидаемым")
                else:
                    print(f"❌ НЕУДАЧА: ожидалось {expected}")
            else:
                if channel_id:
                    print(f"✅ Найден channel_id: {channel_id}")
                else:
                    print("⚠️ Не найден (может быть нормой для видео/username)")
                    
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")


async def test_get_channel_info():
    """Тест получения информации о канале"""
    print("\n" + "="*60)
    print("🔍 ТЕСТ 2: Информация о канале")
    print("="*60)
    
    parser = YouTubeParser()
    
    # Тестовые channel_id
    test_channels = [
        "UC_x5XG1OV2P6uZZ5FSM9Ttw",  # Google Developers
        # "UC-lHJZR3Gqxm24_Vd_AJ5Yw",  # PewDiePie (закомментировано для примера)
    ]
    
    for channel_id in test_channels:
        print(f"\n📥 Канал: {channel_id}")
        try:
            info = await parser.get_channel_info(channel_id)
            print(f"📤 Информация:")
            for key, value in info.items():
                print(f"   {key}: {value}")
            print("✅ УСПЕХ")
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")


async def test_get_latest_videos():
    """Тест получения новых видео через RSS"""
    print("\n" + "="*60)
    print("🔍 ТЕСТ 3: Получение видео через RSS")
    print("="*60)
    
    parser = get_parser()
    
    # Тестовые каналы
    test_channels = [
        {
            "name": "Google Developers",
            "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
            "last_id": None  # None = все последние
        },
        {
            "name": "TheBrainDit (пример)",
            "channel_id": None,  # будет найдено автоматически
            "username": "@TheBrainDit",
            "last_id": None
        }
    ]
    
    for channel in test_channels:
        print(f"\n📺 Канал: {channel.get('name', 'Неизвестный')}")
        
        # Получаем channel_id если нужно
        channel_id = channel.get('channel_id')
        if not channel_id and channel.get('username'):
            channel_id = await parser.extract_channel_id(channel['username'])
            print(f"🔍 Найден channel_id: {channel_id}")
        
        if not channel_id:
            print("❌ Не удалось получить channel_id")
            continue
        
        try:
            videos = await parser.get_latest_videos(
                channel_id=channel_id,
                last_video_id=channel.get('last_id'),
                limit=5
            )
            
            print(f"📦 Найдено видео: {len(videos)}")
            
            for i, video in enumerate(videos, 1):
                print(f"\n  🎬 Видео #{i}")
                print(f"     ID: {video.get('video_id')}")
                print(f"     Название: {video.get('title')[:50]}...")
                print(f"     Ссылка: {video.get('link')}")
                print(f"     Дата: {video.get('published')}")
                if video.get('description'):
                    desc = video.get('description')[:50] + "..." if len(video.get('description', '')) > 50 else video.get('description')
                    print(f"     Описание: {desc}")
            
            print(f"\n✅ УСПЕХ: получено {len(videos)} видео")
            
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")


async def test_with_last_id():
    """Тест с указанием последнего ID"""
    print("\n" + "="*60)
    print("🔍 ТЕСТ 4: Получение только новых видео (с last_id)")
    print("="*60)
    
    parser = get_parser()
    
    # Сначала получаем все видео, чтобы взять ID последнего
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    
    print(f"\n📥 Получаем все видео канала...")
    all_videos = await parser.get_latest_videos(channel_id, limit=3)
    
    if not all_videos:
        print("❌ Нет видео для теста")
        return
    
    last_video = all_videos[-1]
    last_id = last_video.get('video_id')
    
    print(f"📦 Всего видео: {len(all_videos)}")
    print(f"🆔 Последний ID: {last_id}")
    print(f"   Название: {last_video.get('title')}")
    
    # Теперь запрашиваем только новые (должно быть 0)
    print(f"\n🔍 Запрашиваем видео новее {last_id}...")
    new_videos = await parser.get_latest_videos(
        channel_id=channel_id,
        last_video_id=last_id,
        limit=5
    )
    
    print(f"📦 Новых видео: {len(new_videos)}")
    if len(new_videos) == 0:
        print("✅ Ожидаемо: новых видео нет")
    else:
        print(f"⚠️ Найдено {len(new_videos)} видео, хотя не должно быть")


async def test_invalid_channels():
    """Тест с несуществующими каналами"""
    print("\n" + "="*60)
    print("🔍 ТЕСТ 5: Несуществующие каналы")
    print("="*60)
    
    parser = get_parser()
    
    test_inputs = [
        "@ThisChannelDefinitelyDoesNotExist123456",
        "https://youtube.com/@NonExistentChannel98765",
        "uc_nonexistent_123",
        "просто текст без смысла",
    ]
    
    for input_str in test_inputs:
        print(f"\n📥 Вход: {input_str}")
        try:
            channel_id = await parser.extract_channel_id(input_str)
            if channel_id:
                print(f"⚠️ Найден channel_id: {channel_id} (странно)")
            else:
                print(f"✅ Корректно: channel_id не найден")
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")


async def main():
    """Главная функция тестирования"""
    print("="*60)
    print("🎬 ТЕСТИРОВАНИЕ YOUTUBE ПАРСЕРА")
    print("="*60)
    
    try:
        # Тест 1: Извлечение channel_id
        await test_extract_channel_id()
        
        # Тест 2: Информация о канале
        await test_get_channel_info()
        
        # Тест 3: Получение видео
        await test_get_latest_videos()
        
        # Тест 4: Работа с last_id
        await test_with_last_id()
        
        # Тест 5: Несуществующие каналы
        await test_invalid_channels()
        
    finally:
        # Закрываем парсер
        await close_parser()
    
    print("\n" + "="*60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
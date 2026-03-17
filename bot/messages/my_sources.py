# bot/messages/my_sources.py
"""Тексты сообщений для модуля 'Мои источники'."""
from typing import List, Dict


def format_sources_overview_page(overview_data: List[Dict], page: int, total_sources: int) -> str:
    """
    Форматировать страницу обзора источников (до 5 групп на странице).
    
    Args:
        overview_data: Список групп с топиками и источниками
        page: Текущая страница (0-based)
        total_sources: Общее количество источников

    Returns:
        Отформатированный текст с HTML-разметкой
    """
    groups_per_page = 5
    total_pages = (len(overview_data) + groups_per_page - 1) // groups_per_page if overview_data else 1
    page = max(0, min(page, total_pages - 1))

    start_idx = page * groups_per_page
    end_idx = min(start_idx + groups_per_page, len(overview_data))
    page_groups = overview_data[start_idx:end_idx]

    text = f"<b>📚 Мои источники</b>\n\n"
    text += f"<b>📊 Найдено групп:</b> {len(overview_data)}\n"
    text += f"<b>📊 Всего источников:</b> {total_sources}\n\n"

    for group in page_groups:
        text += f"<b>👥 {group['chat_title']}</b> ({len(group['topics'])})\n"

        for topic in group["topics"]:
            topic_name = topic["topic_name"]
            if topic["is_general"]:
                topic_name = "💬 General"
            else:
                topic_name = f"🗨️ {topic_name}"

            sources_count = topic["sources_count"]
            text += f"   <b>{topic_name}</b> ({sources_count})\n"

            for source in topic["sources"]:
                icon = "📺" if source["source_type"] == "youtube" else "📰"
                # Обрезаем длинные имена
                name = source["name"][:25] + "..." if len(source["name"]) > 25 else source["name"]
                text += f"       {icon} {name}\n"

        text += "\n"

    if total_pages > 1:
        text += f"<i>Страница {page + 1}/{total_pages}</i>"

    return text


def format_group_tree(group_title: str, topics_data: List[Dict], total_sources: int) -> str:
    """
    Форматировать дерево группы с топиками и источниками.
    
    Args:
        group_title: Название группы
        topics_data: Список топиков с источниками
        total_sources: Общее количество источников

    Returns:
        Отформатированный текст с HTML-разметкой
    """
    text = f"<b>👥 Группа: {group_title}</b>\n\n"
    text += f"<b>📊 Найдено тем:</b> {len(topics_data)}\n"
    text += f"<b>📊 Всего источников:</b> {total_sources}\n\n"

    for topic in topics_data:
        # Формируем название топика
        if topic["is_general"]:
            topic_name = "💬 General"
        else:
            topic_name = f"🗨️ {topic['topic_name']}"

        sources_count = topic["sources_count"]
        text += f"   <b>{topic_name}</b> ({sources_count})\n"

        # Показываем источники
        for source in topic["sources"]:
            icon = "📺" if source["source_type"] == "youtube" else "📰"
            # Обрезаем длинные имена
            name = source["name"][:25] + "..." if len(source["name"]) > 25 else source["name"]
            text += f"       {icon} {name}\n"

        text += "\n"

    return text

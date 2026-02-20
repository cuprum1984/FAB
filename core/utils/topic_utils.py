# core/utils/topic_utils.py
from typing import Optional, Tuple


def generate_topic_identifier(chat_id: int, thread_id: Optional[int] = None) -> str:
    """
    Генерирует идентификатор темы.
    """
    if thread_id is None or thread_id == 0:
        return f"{chat_id}:0"
    return f"{chat_id}:{thread_id}"


def parse_topic_identifier(topic_identifier: str) -> Tuple[int, Optional[int]]:
    """
    Парсит topic_identifier, извлекая chat_id и thread_id.
    """
    if ":" not in topic_identifier:
        raise ValueError(f"Invalid topic_identifier format: {topic_identifier}")
    
    parts = topic_identifier.split(":", 1)
    try:
        chat_id = int(parts[0])
        thread_id_str = parts[1]
        
        if thread_id_str == "0":
            thread_id = None
        else:
            thread_id = int(thread_id_str)
            
        return chat_id, thread_id
    except (ValueError, IndexError) as e:
        raise ValueError(f"Cannot parse topic_identifier: {topic_identifier}") from e


def is_general_topic(topic_identifier: str) -> bool:
    """Проверяет, является ли тема General (без thread_id)."""
    try:
        _, thread_id = parse_topic_identifier(topic_identifier)
        return thread_id is None or thread_id == 0
    except ValueError:
        return False
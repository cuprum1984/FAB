# core/utils/html_formatter.py
import html
from typing import Any, Optional, List, Dict


def safe_text(text: Any) -> str:
    """
    Безопасное преобразование текста для HTML.
    
    Args:
        text: Любое значение
        
    Returns:
        Экранированная строка
    """
    if text is None:
        return ""
    return html.escape(str(text))


def format_list(items: List[Any], bullet: str = "•") -> str:
    """
    Форматирование списка в HTML.
    
    Args:
        items: Список элементов
        bullet: Символ маркера
        
    Returns:
        Отформатированный список
    """
    if not items:
        return ""
    
    result = []
    for item in items:
        result.append(f"{bullet} {safe_text(item)}")
    
    return "\n".join(result)


def format_key_value(key: str, value: Any, bold_key: bool = True) -> str:
    """
    Форматирование пары ключ-значение.
    
    Args:
        key: Ключ
        value: Значение
        bold_key: Выделять ключ жирным
        
    Returns:
        Отформатированная строка
    """
    safe_key = safe_text(key)
    safe_value = safe_text(value)
    
"""
Сервис загрузки юридических документов (условия, политика конфиденциальности).
Поддерживает мультиязычность с фоллбэком на английский.
"""
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Путь к папке с юридическими документами
LEGAL_DIR = Path(__file__).parent.parent.parent / "docs" / "legal"

# Кеш для текстов документов
_TERMS_CACHE: Dict[str, str] = {}


def preload_legal_docs() -> None:
    """
    Загружает все языковые версии юридических документов в кеш при старте бота.
    Вызывается один раз при инициализации.
    """
    if not LEGAL_DIR.exists():
        logger.warning(f"Legal directory not found: {LEGAL_DIR}")
        return

    supported_langs = ["ru", "en", "uk", "be"]
    
    for lang in supported_langs:
        file_path = LEGAL_DIR / f"{lang}.md"
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
                _TERMS_CACHE[lang] = content
                logger.info(f"Loaded legal doc: {lang}.md")
            except Exception as e:
                logger.error(f"Failed to load {lang}.md: {e}")
        else:
            logger.warning(f"Legal doc not found: {lang}.md")
    
    # Гарантируем наличие английского как фоллбэка
    if "en" not in _TERMS_CACHE:
        logger.error("English legal doc (en.md) not found - fallback will fail!")


def get_legal_text(lang: Optional[str] = None) -> str:
    """
    Возвращает текст юридических документов на указанном языке.
    
    Приоритет языков:
    1. Указанный язык (если есть в кеше)
    2. Английский (en) как основной фоллбэк
    3. Русский (ru) как вторичный фоллбэк
    4. Пустая строка с ошибкой
    
    Args:
        lang: Код языка (ru/en/uk/be). Если None — возвращается en.
        
    Returns:
        Текст документов в формате Markdown.
    """
    if not lang:
        lang = "en"
    
    lang_lower = lang.lower().strip()
    
    # Прямое попадание
    if lang_lower in _TERMS_CACHE:
        return _TERMS_CACHE[lang_lower]
    
    # Фоллбэк на английский
    if "en" in _TERMS_CACHE:
        return _TERMS_CACHE["en"]
    
    # Фоллбэк на русский
    if "ru" in _TERMS_CACHE:
        return _TERMS_CACHE["ru"]
    
    # Крайний случай
    return "⚠️ Legal documents not available. Please contact support."


def get_legal_text_for_user(user_language: Optional[str]) -> str:
    """
    Удобный враппер для получения текста с учётом языка пользователя.
    
    Args:
        user_language: Язык из профиля пользователя (может быть None).
        
    Returns:
        Текст документов на подходящем языке.
    """
    return get_legal_text(user_language)


# Экспортируемые функции
__all__ = ["preload_legal_docs", "get_legal_text", "get_legal_text_for_user"]

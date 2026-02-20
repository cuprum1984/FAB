# core/utils/i18n.py
from locales import en, ru
from typing import Dict, Any, Optional, List


class I18n:
    def __init__(self, language_code: str = 'en'):
        self.language_code = language_code
        self._translations = self._get_translations()
    
    def _get_translations(self) -> Dict:
        """Get translations for current language (defaults to English)"""
        if self.language_code == 'ru':
            return ru.MESSAGES
        return en.MESSAGES
    
    def get(self, keys: List[str], **kwargs) -> str:
        """Get translated message by keys"""
        msg = self._translations
        for key in keys:
            if isinstance(msg, dict):
                msg = msg.get(key)
            if msg is None:
                # Fallback to English
                fallback = self._get_english_fallback(keys)
                if kwargs:
                    try:
                        return fallback.format(**kwargs)
                    except:
                        return fallback
                return fallback
        
        if kwargs and isinstance(msg, str):
            try:
                return msg.format(**kwargs)
            except KeyError:
                return msg
        return msg if isinstance(msg, str) else str(msg)
    
    def _get_english_fallback(self, keys: List[str]) -> str:
        """Fallback to English if translation missing"""
        msg = en.MESSAGES
        for key in keys:
            if isinstance(msg, dict):
                msg = msg.get(key)
            if msg is None:
                return f"Missing translation: {keys}"
        return msg if isinstance(msg, str) else f"Translation error: {keys}"


def create_i18n(language_code: Optional[str] = None) -> I18n:
    """Create i18n instance with default English"""
    return I18n(language_code or 'en')
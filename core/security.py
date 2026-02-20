# core/security.py
"""
Модуль безопасности для MyAggryBot.
Версия: 1.0 (15 февраля 2026)
Отвечает за валидацию URL и защиту от SSRF.
"""
import re
import ipaddress
from urllib.parse import urlparse
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class URLSecurity:
    """Класс для проверки безопасности URL"""
    
    # Белые списки доменов
    TELEGRAM_DOMAINS = [
        't.me',
        'telegram.org',
        'telegram.me',
        'telegram.dog',
        'tdesktop.com',
        'telegram-cdn.org',
    ]
    
    YOUTUBE_DOMAINS = [
        'youtube.com',
        'youtu.be',
        'ytimg.com',
        'googlevideo.com',
        'googleusercontent.com',  # для превью
        'ggpht.com',  # для картинок
        'youtube-nocookie.com',
    ]
    
    # Полностью заблокированные домены/паттерны
    BLOCKED_DOMAINS = [
        'kinogo',
        'hdrezka',
        'lordfilm',
        'torrent',
        'pirate',
        'xxx',
        'porn',
        'sex',
        'casino',
        'betting',
    ]
    
    @classmethod
    def is_localhost(cls, url: str) -> bool:
        """
        Проверяет, ведёт ли URL на localhost или внутренний IP.
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ''
            
            # Проверка на localhost по имени
            localhost_names = ['localhost', 'localtest', 'local', 'localhost.localdomain']
            if hostname.lower() in localhost_names:
                logger.warning(f"⚠️ Обнаружен localhost: {url}")
                return True
            
            # Проверка на IPv4 localhost
            if re.match(r'^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$', hostname):
                logger.warning(f"⚠️ Обнаружен IPv4 localhost: {url}")
                return True
            
            # Проверка на IPv6 localhost
            if hostname in ['::1', '::', '0:0:0:0:0:0:0:1']:
                logger.warning(f"⚠️ Обнаружен IPv6 localhost: {url}")
                return True
            
            # Проверка на частные IP-диапазоны
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    logger.warning(f"⚠️ Обнаружен частный IP: {url}")
                    return True
            except ValueError:
                # Это доменное имя, а не IP
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки localhost: {e}")
            return True  # В случае ошибки лучше заблокировать
    
    @classmethod
    def extract_domain(cls, url: str) -> Optional[str]:
        """
        Извлекает домен из URL.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Убираем www.
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain if domain else None
        except:
            return None
    
    @classmethod
    def is_allowed_youtube(cls, url: str) -> bool:
        """
        Проверяет, разрешён ли YouTube URL.
        """
        domain = cls.extract_domain(url)
        if not domain:
            return False
        
        # Проверяем по белому списку
        for allowed in cls.YOUTUBE_DOMAINS:
            if domain == allowed or domain.endswith('.' + allowed):
                return True
        
        logger.warning(f"❌ YouTube домен не в белом списке: {domain}")
        return False
    
    @classmethod
    def is_allowed_telegram(cls, url: str) -> bool:
        """
        Проверяет, разрешён ли Telegram URL.
        """
        domain = cls.extract_domain(url)
        if not domain:
            return False
        
        for allowed in cls.TELEGRAM_DOMAINS:
            if domain == allowed or domain.endswith('.' + allowed):
                return True
        
        logger.warning(f"❌ Telegram домен не в белом списке: {domain}")
        return False
    

    @classmethod
    def is_blocked_content(cls, url: str) -> bool:
        """Проверяет, содержит ли URL признаки запрещённого контента."""
        try:
            # Проверяем только домен, а не весь URL
            domain = cls.extract_domain(url)
            if not domain:
                return False
            
            domain_lower = domain.lower()
            for blocked in cls.BLOCKED_DOMAINS:
                if blocked in domain_lower:
                    logger.warning(f"⚠️ Обнаружен запрещённый домен: {blocked}")
                    return True
        except Exception as e:
            logger.error(f"Ошибка проверки контента: {e}")
        
        return False
    
    @classmethod
    def validate_url(cls, url: str, source_type: Optional[str] = None) -> Tuple[bool, str]:
        """
        Полная проверка URL.
        
        Returns:
            (is_safe, reason)
        """
        # 1. Базовая проверка формата
        if not url.startswith(('http://', 'https://')):
            return False, "URL должен начинаться с http:// или https://"
        
        # 2. Проверка длины (защита от переполнения)
        if len(url) > 2048:
            return False, "URL слишком длинный"
        
        # 3. Проверка на localhost/внутренние IP
        if cls.is_localhost(url):
            return False, "Доступ к локальным адресам запрещён"
        
        # 4. Извлекаем домен
        domain = cls.extract_domain(url)
        if not domain:
            return False, "Не удалось извлечь домен из URL"
        
        # 5. Проверка на запрещённый контент
        if cls.is_blocked_content(url):
            return False, "Обнаружен запрещённый контент"
        
        # 6. Проверка по типу источника
        if source_type == 'telegram':
            if not cls.is_allowed_telegram(url):
                return False, "Разрешены только Telegram домены"
        
        elif source_type == 'youtube':
            if not cls.is_allowed_youtube(url):
                return False, "Разрешены только YouTube домены"
        
        elif source_type == 'rss':
            # RSS полностью блокируем
            return False, "RSS ленты временно не поддерживаются"
        
        elif source_type is None:
            # Для других типов (например, обычные ссылки) - блокируем всё кроме Telegram/YouTube
            if not (cls.is_allowed_telegram(url) or cls.is_allowed_youtube(url)):
                return False, "Разрешены только Telegram и YouTube домены"
        
        return True, "OK"
    
    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """
        Очищает входные данные от опасных символов.
        """
        # Удаляем управляющие символы
        text = re.sub(r'[\x00-\x1f\x7f]', '', text)
        
        # Ограничиваем длину
        if len(text) > 2000:
            text = text[:2000]
        
        return text.strip()
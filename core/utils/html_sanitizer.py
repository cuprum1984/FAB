# core/utils/html_sanitizer.py
"""
Санитизация HTML для Telegram parse_mode="HTML".
Версия: 6.7 (5 апреля 2026)
"""
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

logger = __import__('logging').getLogger(__name__)

# Whitelist тегов, поддерживаемых Telegram HTML
# ВАЖНО: <br> и <p> НЕ поддерживаются Telegram!
ALLOWED_TAGS = {
    'b', 'strong',          # Жирный
    'i', 'em',              # Курсив
    'u', 'ins',             # Подчёркнутый
    's', 'strike', 'del',   # Зачёркнутый
    'code',                 # Код (inline)
    'pre',                  # Блок кода
    'a',                    # Ссылки
    'blockquote',           # Цитаты
    'tg-emoji',             # Кастомные эмодзи Telegram
}

# Разрешённые схемы URL
ALLOWED_SCHEMES = {'http', 'https', 'tg', 'ton'}

# Опасные префиксы URL
DANGEROUS_PREFIXES = ('javascript:', 'data:', 'vbscript:')


def is_safe_url(url: str) -> bool:
    """
    Проверить безопасность URL.

    Args:
        url: URL для проверки

    Returns:
        True если URL безопасен
    """
    if not url or not isinstance(url, str):
        return False

    lower_url = url.lower().strip()
    if lower_url.startswith(DANGEROUS_PREFIXES):
        return False

    try:
        parsed = urlparse(url)
        return parsed.scheme.lower() in ALLOWED_SCHEMES
    except Exception:
        return False


def sanitize_telegram_html(html_text: str, max_length: int = 4000) -> str:
    """
    Очистить HTML от опасных тегов и ссылок.
    Возвращает безопасный HTML для Telegram parse_mode="HTML".

    Args:
        html_text: Исходный HTML
        max_length: Максимальная длина результата

    Returns:
        Безопасный HTML
    """
    if not html_text:
        return ""

    try:
        soup = BeautifulSoup(html_text, 'html.parser')
    except Exception as e:
        logger.warning(f"⚠️ Ошибка парсинга HTML, возвращаю экранированный текст: {e}")
        import html as html_module
        return html_module.escape(html_text)

    # 1. Заменить <br>, <br/>, <br /> на \n (Telegram не поддерживает <br>)
    for tag in list(soup.find_all(['br', 'br/'])):
        tag.replace_with('\n')

    # 2. Заменить <p> на \n\n (Telegram не поддерживает <p>)
    for tag in list(soup.find_all('p')):
        tag.insert_after('\n\n')
        tag.unwrap()

    # 2.5. Развернуть emoji-обёртки <i class="emoji"> → текст
    # Telegram API не понимает class/style на <i>
    for tag in list(soup.find_all('i')):
        tag_class = tag.get('class', [])
        if 'emoji' in tag_class:
            # Заменяем <i class="emoji"><b>🚢</b></i> → 🚢
            text = tag.get_text()
            tag.replace_with(text)

    # 3. Удалить опасные теги (используем list() чтобы избежать dictionary changed size)
    for tag in list(soup.find_all(True)):
        tag_name = tag.name.lower()

        # <br> и <p> уже должны быть обработаны, но на всякий случай
        if tag_name in ('br', 'p'):
            tag.replace_with('\n' if tag_name == 'br' else '')
            continue

        if tag_name not in ALLOWED_TAGS:
            tag.unwrap()
            continue

        # 4. Удалить class и style у ВСЕХ тегов (Telegram не поддерживает)
        for attr in ['class', 'style', 'dir']:
            if tag.get(attr):
                del tag[attr]

        # 5. Проверить ссылки
        if tag_name == 'a':
            href = tag.get('href', '').strip()

            if not href or not is_safe_url(href):
                tag.unwrap()
                continue

            # Удалить неподдерживаемые атрибуты
            for attr in ['target', 'rel', 'onclick', 'onmouseover']:
                if tag.get(attr):
                    del tag[attr]

        # 6. tg-emoji: развернуть в текст (Telegram API не принимает вложенный HTML)
        if tag_name == 'tg-emoji':
            text = tag.get_text()
            tag.replace_with(text)
            continue

        # 7. Удалить остальные атрибуты кроме разрешённых
        allowed_attrs = {'href'}  # только href для <a>
        for attr in list(tag.attrs.keys()):
            if attr not in allowed_attrs:
                del tag[attr]

    # 6. Удалить пустые блочные теги
    for tag in list(soup.find_all('blockquote')):
        if not tag.get_text().strip():
            tag.decompose()

    result = str(soup)

    # 7. Убрать множественные переносы строк (более 2 подряд)
    result = re.sub(r'\n{3,}', '\n\n', result)

    # 8. Обрезать если нужно
    if len(result) > max_length:
        result = _safe_truncate_html(result, max_length)

    return result


def _safe_truncate_html(html: str, max_length: int) -> str:
    """
    Безопасно обрезать HTML, не ломая теги.
    Если тег открыт, закрываем его.

    Args:
        html: HTML для обрезки
        max_length: Максимальная длина

    Returns:
        Обрезанный HTML с закрытыми тегами
    """
    if len(html) <= max_length:
        return html

    # Обрезаем
    truncated = html[:max_length - 3]

    # Закрываем открытые теги
    open_tags = []
    tag_pattern = re.compile(r'<(/?)(\w+)(?:\s+[^>]*)?/?>')

    for match in tag_pattern.finditer(truncated):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2).lower()

        # Самозакрывающиеся теги
        if tag_name in ('br', 'hr', 'img', 'input', 'meta', 'link'):
            continue

        if is_closing:
            # Закрывающий тег — убираем из стека
            if open_tags and open_tags[-1] == tag_name:
                open_tags.pop()
        else:
            # Открывающий тег — добавляем в стек
            open_tags.append(tag_name)

    # Добавляем закрывающие теги в обратном порядке
    result = truncated
    for tag_name in reversed(open_tags):
        result += f'</{tag_name}>'

    return result + "..."


def html_to_plain_text(html_text: str) -> str:
    """
    Преобразовать HTML в plain text (для fallback режима).
    Удаляет все теги, оставляет только текст.

    Args:
        html_text: HTML для преобразования

    Returns:
        Plain text без тегов
    """
    if not html_text:
        return ""

    try:
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    except Exception:
        return html_text

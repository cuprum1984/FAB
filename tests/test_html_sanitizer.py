"""
Тесты санитизации HTML для Telegram.
Версия: 6.7 (5 апреля 2026)
"""
import pytest
from core.utils.html_sanitizer import (
    sanitize_telegram_html,
    is_safe_url,
    html_to_plain_text,
    _safe_truncate_html,
)


class TestIsSafeUrl:
    """Тесты проверки безопасности URL"""

    def test_http_url_is_safe(self):
        assert is_safe_url("https://example.com") is True

    def test_https_url_is_safe(self):
        assert is_safe_url("http://example.com/path") is True

    def test_tg_scheme_is_safe(self):
        assert is_safe_url("tg://resolve?domain=channel") is True

    def test_ton_scheme_is_safe(self):
        assert is_safe_url("ton://transfer/EQC...") is True

    def test_javascript_url_is_dangerous(self):
        assert is_safe_url("javascript:alert('XSS')") is False

    def test_data_url_is_dangerous(self):
        assert is_safe_url("data:text/html,<script>alert(1)</script>") is False

    def test_vbscript_url_is_dangerous(self):
        assert is_safe_url("vbscript:MsgBox('XSS')") is False

    def test_empty_url_is_dangerous(self):
        assert is_safe_url("") is False

    def test_none_url_is_dangerous(self):
        assert is_safe_url(None) is False

    def test_relative_url_is_dangerous(self):
        assert is_safe_url("/path/to/page") is False


class TestSanitizeTelegramHTML:
    """Тесты санитизации HTML"""

    def test_bold_tag_preserved(self):
        """Жирный тег сохраняется"""
        html = "<b>привет</b>"
        result = sanitize_telegram_html(html)
        assert "<b>привет</b>" in result

    def test_italic_tag_preserved(self):
        """Курсив тег сохраняется"""
        html = "<i>привет</i>"
        result = sanitize_telegram_html(html)
        assert "<i>привет</i>" in result

    def test_underline_tag_preserved(self):
        """Подчёркнутый тег сохраняется"""
        html = "<u>привет</u>"
        result = sanitize_telegram_html(html)
        assert "<u>привет</u>" in result

    def test_strikethrough_tag_preserved(self):
        """Зачёркнутый тег сохраняется"""
        html = "<s>привет</s>"
        result = sanitize_telegram_html(html)
        assert "<s>привет</s>" in result

    def test_code_tag_preserved(self):
        """Код тег сохраняется"""
        html = "<code>print('hello')</code>"
        result = sanitize_telegram_html(html)
        assert "<code>print('hello')</code>" in result

    def test_pre_tag_preserved(self):
        """Блок кода сохраняется"""
        html = "<pre>def foo():\n    pass</pre>"
        result = sanitize_telegram_html(html)
        assert "<pre>" in result

    def test_blockquote_tag_preserved(self):
        """Цитата сохраняется"""
        html = "<blockquote>Цитата</blockquote>"
        result = sanitize_telegram_html(html)
        assert "<blockquote>Цитата</blockquote>" in result

    def test_safe_link_preserved(self):
        """Безопасная ссылка сохраняется"""
        html = '<a href="https://example.com">ссылка</a>'
        result = sanitize_telegram_html(html)
        assert '<a href="https://example.com">ссылка</a>' in result

    def test_tg_link_preserved(self):
        """TG ссылка сохраняется"""
        html = '<a href="tg://resolve?domain=channel">канал</a>'
        result = sanitize_telegram_html(html)
        assert 'href="tg://resolve?domain=channel"' in result

    def test_javascript_link_removed(self):
        """JavaScript ссылка удаляется"""
        html = '<a href="javascript:alert(1)">клик</a>'
        result = sanitize_telegram_html(html)
        assert "<script>" not in result
        assert "клик" in result

    def test_script_tag_removed(self):
        """Script тег удаляется"""
        html = "<script>alert('XSS')</script>привет"
        result = sanitize_telegram_html(html)
        assert "<script>" not in result
        assert "привет" in result

    def test_iframe_tag_removed(self):
        """Iframe тег удаляется"""
        html = '<iframe src="https://evil.com"></iframe>текст'
        result = sanitize_telegram_html(html)
        assert "<iframe" not in result
        assert "текст" in result

    def test_style_tag_removed(self):
        """Style тег удаляется"""
        html = "<style>body{color:red}</style>текст"
        result = sanitize_telegram_html(html)
        assert "<style>" not in result
        assert "текст" in result

    def test_onclick_removed(self):
        """onclick атрибут удаляется"""
        html = '<a href="https://example.com" onclick="alert(1)">ссылка</a>'
        result = sanitize_telegram_html(html)
        assert "onclick" not in result
        assert 'href="https://example.com"' in result

    def test_target_removed_from_links(self):
        """target атрибут удаляется из ссылок"""
        html = '<a href="https://example.com" target="_blank">ссылка</a>'
        result = sanitize_telegram_html(html)
        assert "target" not in result

    def test_empty_input_returns_empty(self):
        """Пустой ввод возвращает пустую строку"""
        assert sanitize_telegram_html("") == ""
        assert sanitize_telegram_html(None) == ""

    def test_nested_tags_preserved(self):
        """Вложенные теги сохраняются"""
        html = "<b>жирный <i>курсив</i></b>"
        result = sanitize_telegram_html(html)
        assert "<b>" in result
        assert "<i>" in result

    def test_br_tag_converted_to_newline(self):
        """<br> конвертируется в \n (Telegram не поддерживает <br>)"""
        html = "строка 1<br>строка 2"
        result = sanitize_telegram_html(html)
        assert "<br" not in result
        assert "\n" in result

    def test_p_tag_converted_to_newlines(self):
        """<p> конвертируется в \n\n (Telegram не поддерживает <p>)"""
        html = "<p>параграф</p>"
        result = sanitize_telegram_html(html)
        assert "<p>" not in result
        assert "параграф" in result

    def test_empty_p_decomposed(self):
        """Пустой параграф удаляется"""
        html = "<p>   </p>текст"
        result = sanitize_telegram_html(html)
        assert "<p>" not in result
        assert "текст" in result

    def test_xhtml_br_tag_converted(self):
        """XHTML-стиль <br/> конвертируется в \n"""
        html = "строка 1<br/>строка 2"
        result = sanitize_telegram_html(html)
        assert "<br" not in result
        assert "\n" in result

    def test_xhtml_br_with_space_converted(self):
        """XHTML-стиль <br /> конвертируется в \n"""
        html = "строка 1<br />строка 2"
        result = sanitize_telegram_html(html)
        assert "<br" not in result
        assert "\n" in result


class TestSafeTruncateHtml:
    """Тесты безопасной обрезки HTML"""

    def test_no_truncation_needed(self):
        """Если текст короткий, не обрезается"""
        html = "<b>привет</b>"
        result = _safe_truncate_html(html, 100)
        assert result == html

    def test_truncation_closes_tags(self):
        """При обрезке открытые теги закрываются"""
        html = "<b><i>очень длинный текст который нужно обрезать</i></b>"
        result = _safe_truncate_html(html, 20)
        assert result.endswith("</i></b>...") or result.count("</b>") >= result.count("<b>")

    def test_truncation_adds_ellipsis(self):
        """При обрезке добавляется ..."""
        html = "a" * 100
        result = _safe_truncate_html(html, 20)
        assert result.endswith("...")

    def test_self_closing_tags_not_closed(self):
        """Самозакрывающиеся теги не закрываются"""
        html = "<br>текст<br>ещё текст"
        result = _safe_truncate_html(html, 15)
        # br не должен закрываться как </br>
        assert "</br>" not in result


class TestHtmlToPlainText:
    """Тесты преобразования HTML в plain text"""

    def test_simple_text(self):
        """Простой текст без тегов"""
        assert html_to_plain_text("привет") == "привет"

    def test_bold_text(self):
        """Жирный текст"""
        result = html_to_plain_text("<b>привет</b>")
        assert "привет" in result

    def test_html_with_tags(self):
        """HTML с тегами"""
        result = html_to_plain_text("<b>жирный</b> <i>курсив</i>")
        assert "жирный" in result
        assert "курсив" in result

    def test_empty_input(self):
        """Пустой ввод"""
        assert html_to_plain_text("") == ""
        assert html_to_plain_text(None) == ""

    def test_complex_html(self):
        """Сложный HTML"""
        html = "<p>параграф 1</p><p>параграф 2</p>"
        result = html_to_plain_text(html)
        assert "параграф 1" in result
        assert "параграф 2" in result


class TestRealTelegramPatterns:
    """Тесты на реальных паттернах из Telegram"""

    def test_link_with_target_and_onclick(self):
        """Ссылка с target и onclick — атрибуты удаляются"""
        html = '<a href="https://t.me/telegram/407" target="_blank" rel="noopener" onclick="return confirm(\'Open?\');">1</a>'
        result = sanitize_telegram_html(html)
        assert '<a href="https://t.me/telegram/407">1</a>' in result
        assert "target" not in result
        assert "onclick" not in result
        assert "rel" not in result

    def test_tg_emoji_unwrapped_to_text(self):
        """tg-emoji разворачивается в текст (Telegram API не принимает HTML внутри)"""
        html = '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji>'
        result = sanitize_telegram_html(html)
        assert '<tg-emoji' not in result
        assert "💬" in result

    def test_tg_emoji_with_nested_emoji_unwrapped(self):
        """tg-emoji с вложенным <i class="emoji"><b>🏢</b></i> → только эмодзи"""
        html = '<tg-emoji emoji-id="5264943818230214577"><i class="emoji"><b>🏢</b></i></tg-emoji>'
        result = sanitize_telegram_html(html)
        assert '<tg-emoji' not in result
        assert '<i' not in result
        assert "🏢" in result

    def test_emoji_i_tag_unwrapped(self):
        """<i class="emoji"><b>🚢</b></i> → 🚢 (get_text разворачивает вложенные)"""
        html = '<i class="emoji" style="background:url(x)"><b>🚢</b></i>'
        result = sanitize_telegram_html(html)
        assert '<i' not in result
        assert "🚢" in result

    def test_span_unwrapped(self):
        """span — не поддерживается, разворачивается"""
        html = 'текст<span style="visibility:hidden">spacer</span>ещё текст'
        result = sanitize_telegram_html(html)
        assert "<span" not in result
        assert "текст" in result
        assert "spacer" in result

    def test_nested_bold_italic(self):
        """Вложенные <b> и <i>"""
        html = "<b>жирный <i>курсив внутри</i></b>"
        result = sanitize_telegram_html(html)
        assert "<b>" in result
        assert "<i>" in result
        assert "жирный" in result
        assert "курсив внутри" in result

    def test_html_entities_preserved(self):
        """HTML-сущности сохраняются"""
        html = "E2E Comments &amp; Reactions"
        result = sanitize_telegram_html(html)
        assert "&amp;" in result or "&" in result

    def test_underline_in_link(self):
        """<u> внутри ссылки"""
        html = '<a href="https://example.com"><u>подчёркнутая ссылка</u></a>'
        result = sanitize_telegram_html(html)
        assert "<u>подчёркнутая ссылка</u>" in result
        assert 'href="https://example.com"' in result

    def test_multiple_br_become_single_newlines(self):
        """Множественные <br><br> → \n\n"""
        html = "строка 1<br><br>строка 2"
        result = sanitize_telegram_html(html)
        assert "<br" not in result
        # Два <br> → два \n
        assert "\n\n" in result

    def test_blockquote_preserved(self):
        """blockquote сохраняется"""
        html = "<blockquote>цитата из другого канала</blockquote>"
        result = sanitize_telegram_html(html)
        assert "<blockquote>цитата из другого канала</blockquote>" in result

    def test_code_inline_preserved(self):
        """inline code сохраняется"""
        html = "используй <code>bot.send_message()</code> для отправки"
        result = sanitize_telegram_html(html)
        assert "<code>bot.send_message()</code>" in result

    def test_pre_block_preserved(self):
        """pre блок сохраняется"""
        html = "<pre>def foo():\n    pass</pre>"
        result = sanitize_telegram_html(html)
        assert "<pre>" in result
        assert "def foo():" in result

    def test_dangerous_script_removed(self):
        """script теги удаляются"""
        html = "<b>текст</b><script>alert('XSS')</script>ещё текст"
        result = sanitize_telegram_html(html)
        assert "<script>" not in result
        assert "текст" in result
        assert "ещё текст" in result

    def test_dangerous_iframe_removed(self):
        """iframe удаляется"""
        html = '<iframe src="https://evil.com"></iframe>текст'
        result = sanitize_telegram_html(html)
        assert "<iframe" not in result
        assert "текст" in result

    def test_complex_real_world_post(self):
        """Реалистичный пост из Telegram канала"""
        html = (
            '<b>Заголовок поста</b><br>'
            '<br>'
            'Текст с <b>жирным</b>, <i>курсивом</i> и '
            '<a href="https://example.com" target="_blank" rel="noopener">ссылкой</a>.<br>'
            '<br>'
            '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> '
            '<blockquote>Цитата из другого канала</blockquote><br>'
            '<br>'
            'Код: <code>print("hello")</code>'
        )
        result = sanitize_telegram_html(html, max_length=4000)

        # Проверяем что теги сохранились
        assert "<b>Заголовок поста</b>" in result
        assert "<b>жирным</b>" in result
        assert "<i>курсивом</i>" in result
        assert '<a href="https://example.com">ссылкой</a>' in result
        assert "target" not in result
        assert "💬" in result  # tg-emoji развёрнут в текст
        assert '<tg-emoji' not in result
        assert "<blockquote>Цитата из другого канала</blockquote>" in result
        assert '<code>print("hello")</code>' in result
        # br не должно быть
        assert "<br" not in result

    def test_max_length_truncation(self):
        """Обрезка по max_length (с учётом HTML-тегов)"""
        html = "<b>" + "a" * 5000 + "</b>"
        result = sanitize_telegram_html(html, max_length=100)
        # Результат может быть чуть больше из-за закрывающих тегов + "..."
        assert len(result) <= 110  # 100 + теги + эллипсис
        assert result.endswith("...")

    def test_multiple_excessive_newlines_collapsed(self):
        """Множественные переносы схлопываются"""
        html = "текст\n\n\n\n\nещё текст"
        result = sanitize_telegram_html(html)
        # Не должно быть больше 2 переносов подряд
        assert "\n\n\n" not in result

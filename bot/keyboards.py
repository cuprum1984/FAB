# bot/keyboards.py
# ⚠️ ВНИМАНИЕ: Этот файл устарел!
# Клавиатуры перенесены в модуль bot/keyboards/
# Используйте: from bot.keyboards import get_main_menu_inline, ...

# Для обратной совместимости импортируем из нового модуля
from bot.keyboards.main_menu import get_main_menu_inline, GetTextFunc
from bot.keyboards.my_sources import get_topics_tree_kb
from bot.keyboards.admin import (
    get_admin_panel_menu_inline,
    get_groups_inline_kb,
    get_topics_inline_kb,
)
from bot.keyboards.settings import (
    get_settings_menu_inline,
    get_language_menu,
    get_back_to_settings_kb,
    get_confirm_delete_kb,
)
from bot.keyboards.sources import (
    get_confirm_channel_kb,
    get_cancel_kb,
    get_source_list_kb,
    get_confirm_delete_source_kb,
)
from bot.keyboards.destinations import get_destinations_inline_kb

# Для обратной совместимости
__all__ = [
    'get_main_menu_inline',
    'get_admin_panel_menu_inline',
    'get_destinations_inline_kb',
    'get_groups_inline_kb',
    'get_topics_inline_kb',
    'get_settings_menu_inline',
    'get_confirm_channel_kb',
    'get_cancel_kb',
    'get_language_menu',
    'get_back_to_settings_kb',
    'get_confirm_delete_kb',
    'get_source_list_kb',
    'get_confirm_delete_source_kb',
    'get_topics_tree_kb',
    'GetTextFunc',
]

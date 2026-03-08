# locales/uk.py
# -*- coding: utf-8 -*-

MESSAGES = {
    # ========== COMMON (common.py) ==========
    "common": {
        "start_new": "👋 <b>Ласкаво просимо, {first_name}!</b>\n\n"
                     "🤖 <b>MyAggryBot</b> - автоматична доставка контенту з Telegram та YouTube каналів у ваші групи.\n\n"
                     "<b>📌 Що вміє бот:</b>\n"
                     "• Додавати Telegram канали (@username)\n"
                     "• Додавати YouTube канали (за посиланням)\n"
                     "• Надсилати нові дописи в теми груп\n"
                     "• Працювати з кількома групами\n\n"
                     "<b>🔧 Для початку:</b>\n"
                     "1. Додайте бота в групу та зробіть адміністратором\n"
                     "2. У групі введіть команду /activ\n"
                     "3. Повертайтеся сюди та натисніть '📥 Додати канал'",

        "start_return": "👋 <b>З поверненням, {first_name}!</b>\n\n🤖 Бот готовий до роботи.",

        "help": "<b>📖 Довідка MyAggryBot</b>\n\n"
                "<b>🔧 Основні команди:</b>\n"
                "• /start - запуск бота\n"
                "• /activ - активувати групу\n"
                "• /plus - активувати тему в групі\n"
                "• /help - ця довідка\n"
                "• /add - додати канал\n"
                "• /list - мої джерела\n"
                "• /mytopics - мої теми\n\n"
                "• Інформаційний канал: <a href=\"https://t.me/MyAggryBot_Info\">@MyAggryBot_Info</a>\n\n"
                "• Задати питання: <a href=\"https://t.me/test_mab_q\">@MyAggryBot_Q</a>\n\n"
                "<b>📺 YouTube канали:</b>\n"
                "• Тільки за повним посиланням\n"
                "• Приклад: https://youtube.com/@TheBrainDit\n\n"
                "<b>📱 Telegram канали:</b>\n"
                "• За @username або посиланням\n"
                "• Приклад: @durov\n\n"
                "<b>👥 Робота з групами:</b>\n"
                "• Додайте бота в групу\n"
                "• Зробіть адміністратором\n"
                "• Введіть /activ у групі. Якщо тема в групі одна (General) - введіть /plus\n\n"
                "<b>📚 Робота з темами:</b>\n"
                "• Створивши групу, увімкніть теми в налаштуваннях групи, створіть тему.\n"
                "• Для реєстрації теми введіть команду /plus\n\n"
                "<b>❓ Часті питання:</b>\n"
                "• Чому не додається YouTube? - потрібне повне посилання\n"
                "• Як часто перевіряються канали ТГ? - кожні 5 хвилин (тестовий режим)\n"
                "• Як часто перевіряються канали Youtube? - кожні 30 хвилин (тестовий режим)\n"
                "<b>❓ Що працює:</b>\n"
                "• Тільки кнопка - Додати канал.\n"
                "• Ну й сам парсинг.\n",

        "cancel": "❌ Дію скасовано.",
        "no_active_action": "❌ Немає активної дії.",
        "menu": "🏠 <b>Головне меню</b>",
        "error": "❌ Сталася помилка. Спробуйте пізніше.",
    },

    # ========== REFRESH (common.py) ==========
    "refresh": {
        "success": "🔄 <b>Інтерфейс оновлено, {first_name}!</b>\n\n"
                   "🤖 <b>MyAggryBot</b> готовий до роботи.\n\n",
    },

    # ========== KEYBOARDS (keyboards.py) ==========
    "keyboards": {
        # Main menu
        "main_menu": {
            "add_channel": "✚ Додати канал",
            "my_sources": "📚 Мої джерела",
            "my_feed": "📰 Моя стрічка",
            "overview": "📰 Огляд",
            "settings": "⚙️ Налаштування",
            "admin_panel": "👨‍💼 Адмін-панель",
            "help": "❓ Довідка",
            "refresh": "🔄 Оновити",
            "placeholder": "Оберіть дію...",
        },

        # Main menu title (for back buttons)
        "main_menu_title": "🏠 Головне меню",

        "admin_menu": {
            "manage_groups": "👥 Управління групами",
            "manage_topics": "🗂️ Управління темами",
            "statistics": "📊 Статистика",
            "monitoring": "🔍 Моніторинг",
            "back": "← Назад",
            "placeholder": "Адмін дії...",
        },

        "groups_menu": {
            "add_group": "➕ Додати групу",
            "back": "← Назад",
            "main_menu_title": "🏠 Головне меню",
            "placeholder": "Оберіть групу...",
            "active_prefix": "✅",
            "inactive_prefix": "❌",
        },

        "destinations": {
            "general_emoji": "💬",
            "topic_emoji": "🗨️",
            "group_emoji": "👥",
            "separator": "────────────",
            "cancel": "❌ Скасування",
            "refresh": "🔄 Оновити список",
            "placeholder": "Куди надсилати дописи?...",
        },

        "destinations_inline": {
            "prev": "◀️ Назад",
            "next": "Вперед ▶️",
            "noop": "⏺️",
        },

        "cancel": "❌ Скасування",
        "back": "← Назад",
        "back_to_groups": "🔙 До груп",
        "back_to_topics": "🔙 До тем",
        "back_to_sources": "🔙 До джерел",
        "back_to_settings": "← Назад у налаштування",
        "back_to_main": "🔙 В головне меню",

        "confirm_add": "✅ Так, додати",
        "edit_title": "✏️ Змінити назву",
        "cancel_add": "❌ Ні, скасувати",

        "settings_menu": {
            "language": "🌐 Мова / Language",
            "delete_data": "🗑️ Видалити мої дані",
            "back": "← Назад",
            "placeholder": "Налаштування...",
        },

        "language_menu": {
            "en": "English",
            "ru": "Русский",
            "uk": "Українська",
            "be": "Беларуская",
            "back": "← Назад",
            "prompt": "Оберіть мову:",
        },

        "confirm_delete": "✅ ТАК, видалити все",
        "cancel_delete": "❌ НІ, скасування",

        "sources_list": {
            "view_source": "📰 {name}",
            "delete": "❌ Видалити",
            "prev": "◀️ Назад",
            "next": "Вперед ▶️",
            "close": "❌ Закрити",
            "page": "{current}/{total}",
            "noop": "⏺️",
        },
    },

    # ========== ADMIN (admin.py) ==========
    "admin": {
        "panel": "👨‍💼 <b>Адмін-панель</b>",
        "manage_groups": "👥 Управління групами",
        "no_groups": "<b>❌ У вас немає активних груп.</b>\n\n"
                     "Додайте групу командою /activ у потрібній групі.",
        "groups_found": "<b>👥 Управління групами</b>\n\n"
                        "Знайдено груп: <b>{count}</b>\n\n"
                        "Оберіть групу для управління:",
        "select_from_list": "❌ Будь ласка, оберіть групу зі списку вище.",
        "no_title": "Без назви",
        "group_info": "<b>👥 Управління групою</b>\n\n"
                      "<b>📛 Назва:</b> {name}\n"
                      "<b>🆔 ID:</b> <code>{chat_id}</code>\n"
                      "<b>📊 Статус:</b> {status}\n\n"
                      "<b>🗂️ Зареєстровані теми:</b>\n{topics}\n"
                      "<b>⚡ Доступні дії:</b>\n"
                      "• /activ — переактивувати групу\n"
                      "• /plus — зареєструвати поточну тему\n"
                      "• /mytopics — список всіх тем\n"
                      "• /add — додати канал в групу",
        "group_active": "✅ Активна",
        "group_inactive": "❌ Неактивна",
        "no_topics": "<i>Немає зареєстрованих тем</i>\n",
        "topic_item": "{i}. <b>{name}</b>{thread_info}\n",
        "general_topic": " (General)",

        # /activ command
        "activ_group_only": "❌ Команда працює тільки в групах.",
        "activ_not_admin": "❌ Тільки адміністратори групи можуть активувати бота.",
        "activ_check_failed": "❌ Не вдалося перевірити ваші права в групі: {error}",
        "activ_bot_not_admin": "<b>❌ Бот повинен бути адміністратором групи.</b>\n\n"
                               "Додайте бота як адміністратора з правами:\n"
                               "• <b>Надсилання повідомлень</b> — обов'язково\n"
                               "• <b>Управління темами</b> — для роботи з форумами",
        "activ_bot_no_permission": "<b>❌ Бот повинен мати право публікувати повідомлення.</b>\n\n"
                                   "Будь ласка, дайте боту право 'Надсилання повідомлень'.",
        "activ_bot_not_member": "❌ Бот не є учасником цієї групи: {error}",
        "activ_reactivated": "<b>✅ Група реактивована!</b>\n\n"
                             "<b>📛 Назва:</b> {name}",
        "activ_already_active": "<b>✅ Група вже активна</b>\n\n"
                                "<b>📛 Назва:</b> {name}",
        "activ_success": "<b>✅ Група активована!</b>\n\n"
                         "<b>📛 Назва:</b> {name}\n"
                         "<b>🆔 ID:</b> <code>{chat_id}</code>\n"
                         "<b>🗂️ Створена тема:</b> General\n\n"
                         "<b>🎯 Тепер можна:</b>\n"
                         "• Додавати канали через /add\n"
                         "• Реєструвати теми через /plus\n"
                         "• Управляти через Адмін-панель",
        "activ_error": "<b>❌ Помилка при активації групи:</b>\n<code>{error}</code>",

        "activ_success_dm": "<b>✅ Група активована!</b>\n\n"
                            "Група '<b>{name}</b>' успішно активована.\n\n"
                            "Тепер ви можете управляти нею через адмін-панель:",

        # /mytopics command
        "mytopics_title": "<b>🗂️ Ваші зареєстровані теми</b>\n\n",
        "mytopics_no_groups": "<b>❌ Немає активних груп</b>\n\n"
                              "<i>Спочатку активуйте групу через /activ</i>",
        "mytopics_group_header": "<b>👥 {name}</b>:\n",
        "mytopics_item": "  {emoji} <b>{name}</b>{thread_info}\n",
        "mytopics_general": "💬",
        "mytopics_topic": "🗨️",
        "mytopics_no_topics": "<i>Немає зареєстрованих тем</i>\n\n",
        "mytopics_total": "<b>📊 Всього тем:</b> {count}\n\n"
                          "<b>📌 Як додати тему:</b>\n"
                          "1. Перейдіть в тему в Telegram\n"
                          "2. Напишіть команду <code>/plus</code>\n"
                          "3. Бот зареєструє тему\n\n"
                          "<i>Після реєстрації теми можна додавати в неї джерела через /add</i>",

        # /plus command
        "plus_not_in_topic": "<b>❌ Ця команда працює тільки всередині теми!</b>\n\n"
                             "1. Перейдіть в потрібну тему\n"
                             "2. Напишіть команду <code>/plus</code>\n\n"
                             "<i>Якщо це General тема, вона вже повинна бути створена автоматично при /activ</i>",
        "plus_group_not_active": "<b>❌ Група не активована!</b>\n\n"
                                 "Спочатку активуйте групу командою <code>/activ</code>",
        "plus_not_admin": "❌ Тільки адміністратори можуть реєструвати теми.",
        "plus_error": "❌ Помилка перевірки прав: {error}",
        "plus_already_exists": "<b>✅ Тема вже зареєстрована!</b>\n\n"
                               "• <b>📛 Назва:</b> {name}\n"
                               "• <b>🆔 ID теми:</b> {thread_id}\n"
                               "• <b>🔗 Ідентифікатор:</b> <code>{identifier}</code>",
        "plus_not_found": "⚠️ <b>Не вдалося знайти назву теми в базі.</b>\n\n"
                          "Тема буде зареєстрована як <b>'{name}'</b>.\n"
                          "При наступному перейменуванні назва оновиться автоматично.",
        "plus_success": "<b>✅ Тема зареєстрована!</b>\n\n"
                        "• <b>📛 Назва:</b> {name}\n"
                        "• <b>🆔 ID теми:</b> {thread_id}\n"
                        "• <b>🔗 Ідентифікатор:</b> <code>{identifier}</code>",
        "plus_error_db": "<b>❌ Помилка при реєстрації теми:</b>\n<code>{error}</code>",
    },

    # ========== SOURCES (sources.py) ==========
    "sources": {
        "add_no_groups": "<b>❌ Спочатку додайте хоча б одну групу через Адмін-панель.</b>\n\n"
                         "1. Додайте бота в групу\n"
                         "2. Зробіть його адміністратором\n"
                         "3. У групі введіть команду /activ",
        "add_prompt": "<b>📥 Додавання каналу</b>\n\n"
                      "<b>Введіть username каналу або посилання:</b>\n\n"
                      "<b>📌 Приклади:</b>\n"
                      "• @durov\n"
                      "• durov\n"
                      "• https://t.me/durov\n"
                      "• https://youtube.com/@TheBrainDit\n"
                      "• @ОбманутыйРоссиянин (кирилиця)\n\n"
                      "<i>YouTube канали — за посиланням або @username</i>",
        "add_cancelled": "❌ Додавання скасовано.",

        "youtube_invalid_link": "<b>❌ Це посилання на відео, а не на канал</b>\n\n"
                                "Введіть посилання на канал, наприклад:\n"
                                "https://youtube.com/@TheBrainDit",
        "youtube_checking": "<b>🔍 Перевіряю YouTube канал...</b>",
        "youtube_blocked": "<b>❌ YouTube канал заблоковано</b>\n\n"
                           "Причина: {reason}\n\n"
                           "Будь ласка, використайте інший канал.",
        "youtube_retry": "⚠️ Перша спроба не вдалася для @{username}, пробую через 3 сек...",
        "youtube_failed": "<b>❌ Не вдалося отримати дані каналу</b>\n\n"
                          "⏳ <i>YouTube може гальмувати при першому зверненні.\n"
                          "Якщо не вийде одразу — бот повторить спробу автоматично.</i>\n"
                          "Перевірте посилання. Приклад: https://youtube.com/@TheBrainDit",
        "youtube_found": "<b>✅ Знайдено YouTube канал!</b>\n\n"
                         "• <b>Назва:</b> {title}\n"
                         "• <b>Username:</b> @{username}\n"
                         "• <b>Останнє відео:</b> {video_id}\n"
                         "• <b>Посилання:</b> https://youtu.be/{video_id}\n\n"
                         "<b>Додати цей канал?</b>",

        "telegram_invalid_domain": "<b>❌ Недопустиме посилання</b>\n\n"
                                   "Дозволені тільки посилання на Telegram канали.",
        "telegram_invalid_username": "<b>❌ Невірний формат username</b>\n\n"
                                     "Вимоги: 5-32 символи, літери a-z, цифри 0-9, підкреслення\n"
                                     "Приклад: @durov, durov, https://t.me/durov",
        "telegram_checking": "<b>🔍 Перевіряю Telegram канал...</b>",
        "telegram_not_found": "<b>❌ Канал не знайдено</b>\n\nПомилка: {error}",
        "telegram_no_posts": "<b>❌ Не вдалося отримати допис з каналу @{username}</b>",
        "telegram_found": "<b>✅ Інформація про канал</b>\n\n"
                          "• Username: @{username}\n"
                          "• Назва: {title}\n"
                          "• Останній допис ID: {post_id}\n\n"
                          "<b>Додати цей канал?</b>",

        "add_confirm": "<b>Додати цей канал?</b>",
        "add_saving": "✅ Канал знайдено!\n"
                      "📥 Останній допис ID: {post_id}\n\n"
                      "⏳ Зберігаю...",
        "add_saving_telegram": "✅ Telegram канал знайдено!\n"
                               "📥 Зберігаю канал @{username}\n"
                               "📝 Останній допис ID: {post_id}\n\n"
                               "⏳ Обробка...",
        "add_saving_youtube": "✅ YouTube канал знайдено!\n"
                              "📥 Зберігаю канал @{username}\n"
                              "📝 Останнє відео ID: {video_id}\n\n"
                              "⏳ Обробка...",
        "add_saved": "📌 Тепер оберіть групу/тему для надсилання останнього допису:",
        "add_select_group": "📚 <b>Оберіть групу</b>\n\n"
                            "📌 На наступному кроці ви зможете обрати тему всередині групи.",
        "add_select_topic": "🗨️ <b>Оберіть тему в групі \"{group_title}\"</b>\n\n"
                            "📌 Сюди надходитимуть нові дописи.",

        "destination_not_found": "❌ Не вдалося розпізнати вибір. Будь ласка, оберіть зі списку:",
        "destination_use_inline": "⚠️ Будь ласка, оберіть групу/тему з inline-клавіатури вище.",
        "destination_already_exists": "✅ Цей канал вже додано в {destination}.",
        "destination_success_telegram": "✅ Канал @{username} успішно додано!\n\n"
                                        "📥 Надіслано останній допис (ID: {post_id})\n"
                                        "🎯 Призначення: {destination}\n\n"
                                        "⏳ Наступні дописи надходитимуть автоматично кожні 5 хвилин.",
        "destination_success_youtube": "✅ YouTube канал @{username} успішно додано!\n\n"
                                       "📥 Надіслано останнє відео (ID: {video_id})\n"
                                       "🎯 Призначення: {destination}\n\n"
                                       "⏳ Наступні відео надходитимуть автоматично (кожні 30 хвилин).",
        "destination_error": "❌ Помилка при додаванні каналу: {error}",

        "list_no_groups": "<b>❌ Немає активних груп</b>\n\n"
                          "<i>Спочатку додайте групу через Адмін-панель або командою /activ</i>",
        "list_empty": "<b>📭 Список джерел порожній</b>\n\n"
                      "<i>Ви ще не додали жодного джерела.</i>\n\n"
                      "<b>📌 Як додати:</b>\n"
                      "1. Натисніть '📥 Додати канал'\n"
                      "2. Введіть username каналу\n"
                      "3. Оберіть групу для надсилання",
        "list_title": "<b>📚 Ваші підписки по групах</b>\n\n",
        "list_group_header": "👥Група - <b>{name}</b>\n",
        "list_separator": "    ─────────────────\n",
        "list_topic_general": "💬Топік - <b>{name}</b>\n",
        "list_topic": "🗨️Топік - <b>{name}</b>\n",
        "list_source": "        {icon} {link}\n",
        "list_more": "<i>... і ще {count} джерел</i>\n\n",
        "list_total": "<b>📊 Всього підписок:</b> {total}\n"
                      "<b>👥 Всього груп:</b> {groups}\n\n"
                      "<b>🔧 Управління:</b> Оберіть джерело для управління",
        "list_page_empty": "<i>Немає джерел на цій сторінці</i>\n\n",
        "list_closed": "✅ Список джерел закрито",

        "error_no_type": "❌ Помилка: не вказано тип джерела",
        "error_no_username": "❌ Помилка: не вказано username каналу",
        "error_no_channel_id": "❌ Помилка: не вказано ID каналу",
        "error_no_groups": "❌ Помилка: немає доступних груп",
        "error_no_groups_short": "❌ Немає активних груп",
        "error_general": "❌ Сталася помилка: {error}",

        "delete_not_found": "❌ Підписка не знайдена",
        "delete_success": "✅ Підписка видалена",
        "delete_error": "❌ Помилка при видаленні підписки",
    },

    # ========== TOPICS AUTO (topics_auto.py) ==========
    "topics_auto": {
        "topic_created": "📌 Створено нову тему: '{name}' (ID: {thread_id})",
        "topic_edited": "🔄 Тему перейменовано: '{name}' (ID: {thread_id})",
        "topic_closed": "🔒 Тему закрито (ID: {thread_id})",
    },

    # ========== SETTINGS (settings_handler.py) ==========
    "settings": {
        "title": "<b>⚙️ Налаштування</b>\n\n"
                 "👤 <b>Мова:</b> {lang}\n"
                 "📊 <b>Статистика:</b>\n"
                 "• Особистих підписок: ?\n"
                 "• Груп: ?\n\n"
                 "<i>Оберіть дію:</i>",

        "language_prompt": "<b>🌐 Оберіть мову</b>\n\n"
                           "English\n"
                           "Русский\n"
                           "Українська",
        "language_changed": "✅ Мову змінено на {lang}",
        "language_en": "English",
        "language_ru": "Русский",
        "language_uk": "Українська",
        "language_be": "Беларуская",
        "language_back": "← Назад у налаштування",

        "delete_warning": "<b>⚠️ УВАГА!</b>\n\n"
                          "Ви збираєтеся видалити <b>ВСІ СВОЇ ДАНІ</b> з бота:\n\n"
                          "• 🗂️ Всі особисті підписки\n"
                          "• 👥 Вихід з усіх груп (якщо ви адміністратор)\n"
                          "• ⚙️ Всі налаштування\n"
                          "• 💾 Весь кеш\n\n"
                          "ТЕСТ!!!\n"
                          "<b>Цю дію НЕМОЖЛИВО скасувати!</b>\n\n"
                          "Групи, де ви не адміністратор, залишаться активними для інших користувачів.\n\n"
                          "Ви впевнені?",
        "delete_success": "✅ <b>Всі ваші дані видалено!</b>\n\n"
                          "• Особисті підписки видалено\n"
                          "• Підписки в групах видалено\n"
                          "• Налаштування скинуто\n"
                          "• Кеш очищено\n\n"
                          "Ви можете почати заново з команди /start",
        "delete_cancelled": "✅ Видалення даних скасовано",
        "delete_error": "❌ Помилка при видаленні даних: {error}",
    },

    # ========== MIDDLEWARE MESSAGES ==========
    "middleware": {
        "group_only_command": (
            "⚠️ Команди /activ та /plus працюють тільки в групах та темах!\n\n"
            "1. Додайте бота в групу\n"
            "2. Зробіть його адміністратором\n"
            "3. У групі введіть /activ\n"
            "4. У потрібній темі введіть /plus"
        ),

        "private_only_command": (
            "⚠️ Ця команда доступна тільки в особистих повідомленнях з ботом.\n"
            "Напишіть мені в особисті: @MyAggryBot"
        ),
    },
}

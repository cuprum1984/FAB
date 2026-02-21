# locales/en.py
# -*- coding: utf-8 -*-
# DEFAULT LANGUAGE - ENGLISH

MESSAGES = {
    # ========== COMMON (common.py) ==========
    "common": {
        "start_new": "👋 <b>Welcome, {first_name}!</b>\n\n"
                     "🤖 <b>MyAggryBot</b> - automatic content delivery from Telegram and YouTube channels to your groups.\n\n"
                     "<b>📌 What the bot can do:</b>\n"
                     "• Add Telegram channels (@username)\n"
                     "• Add YouTube channels (by link)\n"
                     "• Send new posts to group topics\n"
                     "• Work with multiple groups\n\n"
                     "<b>🔧 To get started:</b>\n"
                     "1. Add the bot to a group and make it admin\n"
                     "2. In the group, enter the /activ command\n"
                     "3. Return here and click '📥 Add channel'",
        
        "start_return": "👋 <b>Welcome back, {first_name}!</b>\n\n🤖 Bot is ready to work.",
        
        "help": "<b>📖 MyAggryBot Help</b>\n\n"
                "<b>🔧 Main commands:</b>\n"
                "• /start - start the bot\n"
                "• /activ - activate a group\n"
                "• /plus - activate a topic in the group\n"
                "• /help - this help\n"
                "• /add - add a channel\n"
                "• /list - my sources\n"
                "• /mytopics - my topics\n\n"
                "• Info channel: <a href=\"https://t.me/MyAggryBot_Info\">@MyAggryBot_Info</a>\n\n"
                "• Ask questions: <a href=\"https://t.me/test_mab_q\">@MyAggryBot_Q</a>\n\n"
                "<b>📺 YouTube channels:</b>\n"
                "• Only full links\n"
                "• Example: https://youtube.com/@TheBrainDit\n\n"
                "<b>📱 Telegram channels:</b>\n"
                "• By @username or link\n"
                "• Example: @durov\n\n"
                "<b>👥 Working with groups:</b>\n"
                "• Add the bot to a group\n"
                "• Make it admin\n"
                "• Enter /activ in the group\n\n"
                "<b>📚 Working with topics:</b>\n"
                "• After creating a group, enable topics in group settings, create a topic.\n"
                "• To register a topic, enter the /plus command\n\n"
                "<b>❓ FAQ:</b>\n"
                "• Why won't YouTube add? - need a full link\n"
                "• How often are Telegram channels checked? - every 5 minutes (test mode)\n"
                "• How often are YouTube channels checked? - every 30 minutes (test mode)\n"
                "<b>❓ What works:</b>\n"
                "• Only the 'Add channel' button.\n"
                "• And the parsing itself.\n",
        
        "cancel": "❌ Action cancelled.",
        "no_active_action": "❌ No active action.",
        "menu": "🏠 <b>Main Menu</b>",
        "error": "❌ An error occurred. Please try again later.",
    },
    
    # ========== REFRESH (common.py) ==========
    "refresh": {
        "success": "🔄 <b>Interface refreshed, {first_name}!</b>\n\n"
                   "🤖 <b>MyAggryBot</b> is ready to work.\n\n"
                   "<b>📌 Quick commands:</b>\n"
                   "• /add — add a channel\n"
                   "• /list — my sources\n"
                   "• /help — help",
    },
    
    # ========== KEYBOARDS (keyboards.py) ==========
    "keyboards": {
        # Main menu
        "main_menu": {
            "add_channel": "📥 Add channel",
            "my_sources": "📚 My sources",
            "my_feed": "📰 My feed",
            "settings": "⚙️ Settings",
            "admin_panel": "👨‍💼 Admin panel",
            "help": "❓ Help",
            "refresh": "🔄 Refresh",
            "placeholder": "Choose action...",
        },
        
        # Main menu title (for back buttons)
        "main_menu_title": "🏠 Main menu",  # ← ДОБАВЛЕНО
        
        # Admin panel
        "admin_menu": {
            "manage_groups": "👥 Manage groups",
            "manage_topics": "🗂️ Manage topics",
            "statistics": "📊 Statistics",
            "monitoring": "🔍 Monitoring",
            "back": "← Back",
            "placeholder": "Admin actions...",
        },
        
        # Groups menu
        "groups_menu": {
            "add_group": "➕ Add group",
            "back": "← Back",
            "main_menu_title": "🏠 Main menu",
            "placeholder": "Choose a group...",
            "active_prefix": "✅",
            "inactive_prefix": "❌",
        },
        
        # Destinations menu (groups/topics)
        "destinations": {
            "general_emoji": "💬",
            "topic_emoji": "🗨️",
            "group_emoji": "👥",
            "separator": "────────────",
            "cancel": "❌ Cancel",
            "refresh": "🔄 Refresh list",
            "placeholder": "Where to send posts?...",
        },
        
        # Cancel/back
        "cancel": "❌ Cancel",
        "back": "← Back",
        "back_to_settings": "← Back to settings",  # ← ДОБАВЛЕНО
        
        # Confirmations
        "confirm_add": "✅ Yes, add",
        "edit_title": "✏️ Change title",
        "cancel_add": "❌ No, cancel",
        
        # Settings
        "settings_menu": {
            "language": "🌐 Language",
            "delete_data": "🗑️ Delete my data",
            "back": "← Back",
            "placeholder": "Settings...",
        },
        
        # Language menu
        "language_menu": {
            "en": "English",
            "ru": "Русский",
            "back": "← Back",
        },
        
        # Delete confirmation
        "confirm_delete": "✅ YES, delete everything",
        "cancel_delete": "❌ NO, cancel",
        
        # Sources list
        "sources_list": {
            "view_source": "📰 {name}",
            "delete": "❌ Delete",
            "prev": "◀️ Back",
            "next": "Next ▶️",
            "close": "❌ Close",
            "page": "{current}/{total}",
            "noop": "⏺️",
        },
    },
    
    # ========== ADMIN (admin.py) ==========
    "admin": {
        "panel": "👨‍💼 <b>Admin Panel</b>",
        "manage_groups": "👥 Manage groups",
        "no_groups": "<b>❌ You have no active groups.</b>\n\n"
                     "Add a group using the /activ command in the desired group.",
        "groups_found": "<b>👥 Manage groups</b>\n\n"
                        "Groups found: <b>{count}</b>\n\n"
                        "Choose a group to manage:",
        "select_from_list": "❌ Please select a group from the list above.",
        "no_title": "No title",
        "group_info": "<b>👥 Managing group</b>\n\n"
                      "<b>📛 Name:</b> {name}\n"
                      "<b>🆔 ID:</b> <code>{chat_id}</code>\n"
                      "<b>📊 Status:</b> {status}\n\n"
                      "<b>🗂️ Registered topics:</b>\n{topics}\n"
                      "<b>⚡ Available actions:</b>\n"
                      "• /activ — reactivate group\n"
                      "• /plus — register current topic\n"
                      "• /mytopics — list all topics\n"
                      "• /add — add channel to group",
        "group_active": "✅ Active",
        "group_inactive": "❌ Inactive",
        "no_topics": "<i>No registered topics</i>\n",
        "topic_item": "{i}. <b>{name}</b>{thread_info}\n",
        "general_topic": " (General)",
        
        # /activ command
        "activ_group_only": "❌ This command only works in groups.",
        "activ_not_admin": "❌ Only group administrators can activate the bot.",
        "activ_check_failed": "❌ Failed to verify your rights in the group: {error}",
        "activ_bot_not_admin": "<b>❌ The bot must be a group administrator.</b>\n\n"
                               "Add the bot as an administrator with permissions:\n"
                               "• <b>Send Messages</b> — required\n"
                               "• <b>Manage Topics</b> — to work with forums",
        "activ_bot_no_permission": "<b>❌ The bot must have permission to send messages.</b>\n\n"
                                   "Please give the bot 'Send Messages' permission.",
        "activ_bot_not_member": "❌ Bot is not a member of this group: {error}",
        "activ_reactivated": "<b>✅ Group reactivated!</b>\n\n"
                             "<b>📛 Name:</b> {name}",
        "activ_already_active": "<b>✅ Group is already active</b>\n\n"
                                "<b>📛 Name:</b> {name}",
        "activ_success": "<b>✅ Group activated!</b>\n\n"
                         "<b>📛 Name:</b> {name}\n"
                         "<b>🆔 ID:</b> <code>{chat_id}</code>\n"
                         "<b>🗂️ Created topic:</b> General\n\n"
                         "<b>🎯 Now you can:</b>\n"
                         "• Add channels via /add\n"
                         "• Register topics via /plus\n"
                         "• Manage via Admin Panel",
        "activ_error": "<b>❌ Error activating group:</b>\n<code>{error}</code>",
        
        # /mytopics command
        "mytopics_title": "<b>🗂️ Your registered topics</b>\n\n",
        "mytopics_no_groups": "<b>❌ No active groups</b>\n\n"
                              "<i>First activate a group via /activ</i>",
        "mytopics_group_header": "<b>👥 {name}</b>:\n",
        "mytopics_item": "  {emoji} <b>{name}</b>{thread_info}\n",
        "mytopics_general": "💬",
        "mytopics_topic": "🗨️",
        "mytopics_no_topics": "<i>No registered topics</i>\n\n",
        "mytopics_total": "<b>📊 Total topics:</b> {count}\n\n"
                          "<b>📌 How to add a topic:</b>\n"
                          "1. Go to the topic in Telegram\n"
                          "2. Type the command <code>/plus</code>\n"
                          "3. The bot will register the topic\n\n"
                          "<i>After registering a topic, you can add sources to it via /add</i>",
        
        # /plus command
        "plus_not_in_topic": "<b>❌ This command only works inside a topic!</b>\n\n"
                             "1. Go to the desired topic\n"
                             "2. Type the command <code>/plus</code>\n\n"
                             "<i>If this is the General topic, it should already be created automatically with /activ</i>",
        "plus_group_not_active": "<b>❌ Group not activated!</b>\n\n"
                                 "First activate the group with the <code>/activ</code> command",
        "plus_not_admin": "❌ Only administrators can register topics.",
        "plus_error": "❌ Error checking permissions: {error}",
        "plus_already_exists": "<b>✅ Topic already registered!</b>\n\n"
                               "• <b>📛 Name:</b> {name}\n"
                               "• <b>🆔 Topic ID:</b> {thread_id}\n"
                               "• <b>🔗 Identifier:</b> <code>{identifier}</code>",
        "plus_not_found": "⚠️ <b>Could not find topic name in database.</b>\n\n"
                          "Topic will be registered as <b>'{name}'</b>.\n"
                          "The name will update automatically on next rename.",
        "plus_success": "<b>✅ Topic registered!</b>\n\n"
                        "• <b>📛 Name:</b> {name}\n"
                        "• <b>🆔 Topic ID:</b> {thread_id}\n"
                        "• <b>🔗 Identifier:</b> <code>{identifier}</code>",
        "plus_error_db": "<b>❌ Error registering topic:</b>\n<code>{error}</code>",
    },
    
    # ========== SOURCES (sources.py) ==========
    "sources": {
        # Add channel
        "add_no_groups": "<b>❌ First add at least one group via Admin Panel.</b>\n\n"
                         "1. Add the bot to a group\n"
                         "2. Make it an administrator\n"
                         "3. In the group, enter the /activ command",
        "add_prompt": "<b>📥 Adding a channel</b>\n\n"
                      "<b>Enter the channel username or link:</b>\n\n"
                      "<b>📌 Examples:</b>\n"
                      "• @durov\n"
                      "• durov\n"
                      "• https://t.me/durov\n"
                      "• https://youtube.com/@TheBrainDit\n"
                      "• @ОбманутыйРоссиянин (Cyrillic)\n\n"
                      "<i>YouTube channels — by link or @username</i>",
        "add_cancelled": "❌ Addition cancelled.",
        
        # YouTube processing
        "youtube_invalid_link": "<b>❌ This is a video link, not a channel</b>\n\n"
                                "Enter a channel link, for example:\n"
                                "https://youtube.com/@TheBrainDit",
        "youtube_checking": "<b>🔍 Checking YouTube channel...</b>",
        "youtube_blocked": "<b>❌ YouTube channel blocked</b>\n\n"
                           "Reason: {reason}\n\n"
                           "Please use a different channel.",
        "youtube_retry": "⚠️ First attempt failed for @{username}, trying again in 3 seconds...",
        "youtube_failed": "<b>❌ Could not get channel data</b>\n\n"
                          "⏳ <i>YouTube may be slow on first request.\n"
                          "If it doesn't work immediately, the bot will retry automatically.</i>\n"
                          "Check the link. Example: https://youtube.com/@TheBrainDit",
        "youtube_found": "<b>✅ YouTube channel found!</b>\n\n"
                         "• <b>Name:</b> {title}\n"
                         "• <b>Username:</b> @{username}\n"
                         "• <b>Last video:</b> {video_id}\n"
                         "• <b>Link:</b> https://youtu.be/{video_id}\n\n"
                         "<b>Add this channel?</b>",
        
        # Telegram processing
        "telegram_invalid_domain": "<b>❌ Invalid link</b>\n\n"
                                   "Only Telegram channel links are allowed.",
        "telegram_invalid_username": "<b>❌ Invalid username format</b>\n\n"
                                     "Requirements: 5-32 characters, letters a-z, numbers 0-9, underscore\n"
                                     "Example: @durov, durov, https://t.me/durov",
        "telegram_checking": "<b>🔍 Checking Telegram channel...</b>",
        "telegram_not_found": "<b>❌ Channel not found</b>\n\nError: {error}",
        "telegram_no_posts": "<b>❌ Could not get post from channel @{username}</b>",
        "telegram_found": "<b>✅ Channel information</b>\n\n"
                          "• Username: @{username}\n"
                          "• Name: {title}\n"
                          "• Last post ID: {post_id}\n\n"
                          "<b>Add this channel?</b>",
        
        # Common
        "add_confirm": "<b>Add this channel?</b>",
        "add_saving": "✅ Channel found!\n"
                      "📥 Last post ID: {post_id}\n\n"
                      "⏳ Saving...",
        "add_saving_telegram": "✅ Telegram channel found!\n"
                               "📥 Saving channel @{username}\n"
                               "📝 Last post ID: {post_id}\n\n"
                               "⏳ Processing...",
        "add_saving_youtube": "✅ YouTube channel found!\n"
                              "📥 Saving channel @{username}\n"
                              "📝 Last video ID: {video_id}\n\n"
                              "⏳ Processing...",
        "add_saved": "📌 Now choose a group/topic to send the last post to:",
        
        # Destination choice
        "destination_not_found": "❌ Could not recognize your choice. Please select from the list:",
        "destination_already_exists": "✅ This channel is already added to {destination}.",
        "destination_success_telegram": "✅ Channel @{username} successfully added!\n\n"
                                        "📥 Last post sent (ID: {post_id})\n"
                                        "🎯 Destination: {destination}\n\n"
                                        "⏳ Next posts will arrive automatically every 5 minutes.",
        "destination_success_youtube": "✅ YouTube channel @{username} successfully added!\n\n"
                                       "📥 Last video sent (ID: {video_id})\n"
                                       "🎯 Destination: {destination}\n\n"
                                       "⏳ Next videos will arrive automatically (every 30 minutes).",
        "destination_error": "❌ Error adding channel: {error}",
        
        # Sources list (/list)
        "list_no_groups": "<b>❌ No active groups</b>\n\n"
                          "<i>First add a group via Admin Panel or /activ command</i>",
        "list_empty": "<b>📭 Source list is empty</b>\n\n"
                      "<i>You haven't added any sources yet.</i>\n\n"
                      "<b>📌 How to add:</b>\n"
                      "1. Click '📥 Add channel'\n"
                      "2. Enter the channel username\n"
                      "3. Choose a group to send to",
        "list_title": "<b>📚 Your subscriptions by group</b>\n\n",
        "list_group_header": "👥Group - <b>{name}</b>\n",
        "list_separator": "    ─────────────────\n",
        "list_topic_general": "💬Topic - <b>{name}</b>\n",
        "list_topic": "🗨️Topic - <b>{name}</b>\n",
        "list_source": "        {icon} {link}\n",
        "list_more": "<i>... and {count} more sources</i>\n\n",
        "list_total": "<b>📊 Total subscriptions:</b> {total}\n"
                      "<b>👥 Total groups:</b> {groups}\n\n"
                      "<b>🔧 Management:</b> Select a source to manage",
        "list_page_empty": "<i>No sources on this page</i>\n\n",
        "list_closed": "✅ Source list closed",
        
        # Errors
        "error_no_type": "❌ Error: source type not specified",
        "error_no_username": "❌ Error: channel username not specified",
        "error_no_channel_id": "❌ Error: channel ID not specified",
        "error_no_groups": "❌ Error: no available groups",
        "error_no_groups_short": "❌ No active groups",
        "error_general": "❌ An error occurred: {error}",
        
        # Delete source
        "delete_not_found": "❌ Subscription not found",
        "delete_success": "✅ Subscription deleted",
        "delete_error": "❌ Error deleting subscription",
    },
    
    # ========== TOPICS AUTO (topics_auto.py) ==========
    "topics_auto": {
        "topic_created": "📌 New topic created: '{name}' (ID: {thread_id})",
        "topic_edited": "🔄 Topic renamed: '{name}' (ID: {thread_id})",
        "topic_closed": "🔒 Topic closed (ID: {thread_id})",
    },
    
    # ========== SETTINGS (settings_handler.py) ==========
    "settings": {
        "title": "<b>⚙️ Settings</b>\n\n"
                 "👤 <b>Language:</b> {lang}\n"
                 "📊 <b>Statistics:</b>\n"
                 "• Personal subscriptions: ?\n"
                 "• Groups: ?\n\n"
                 "<i>Choose an action:</i>",
        
        # Language
        "language_prompt": "<b>🌐 Choose language</b>\n\n"
                           "English\n"
                           "Русский",
        "language_changed": "✅ Language changed to {lang}",
        "language_en": "English",
        "language_ru": "Русский",
        "language_back": "← Back to settings",
        
        # Delete data
        "delete_warning": "<b>⚠️ WARNING!</b>\n\n"
                          "You are about to delete <b>ALL YOUR DATA</b> from the bot:\n\n"
                          "• 🗂️ All personal subscriptions\n"
                          "• 👥 Leave all groups (if you are an admin)\n"
                          "• ⚙️ All settings\n"
                          "• 💾 All cache\n\n"
                          "<b>This action CANNOT be undone!</b>\n\n"
                          "Groups where you are not an admin will remain active for other users.\n\n"
                          "Are you sure?",
        "delete_success": "✅ <b>All your data has been deleted!</b>\n\n"
                          "• Personal subscriptions deleted\n"
                          "• Group subscriptions deleted\n"
                          "• Settings reset\n"
                          "• Cache cleared\n\n"
                          "You can start over with the /start command",
        "delete_cancelled": "✅ Deletion cancelled",
        "delete_error": "❌ Error deleting data: {error}",
    },
    
    # ========== HTML FORMATTER (html_formatter.py) ==========
    # Note: This is just utility functions, no user-facing messages
    
    # ========== TOPIC UTILS (topic_utils.py) ==========
    # Note: This is just utility functions, no user-facing messages
}
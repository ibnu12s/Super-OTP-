from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Get admin main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("👥 Kelola User", callback_data="admin_users")],
        [InlineKeyboardButton("⚙️ HeroSMS Settings", callback_data="admin_hero_sms")],
        [InlineKeyboardButton("💳 Qrispy Settings", callback_data="admin_qrispy")],
        [InlineKeyboardButton("🤖 Bot Settings", callback_data="admin_bot")],
        [InlineKeyboardButton("📊 Statistik", callback_data="admin_bot_stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("❌ Tutup Panel", callback_data="close_admin")]
    ]
    return InlineKeyboardMarkup(keyboard)

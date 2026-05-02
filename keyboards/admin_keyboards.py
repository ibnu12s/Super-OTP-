"""
Admin Keyboards for HeroSMS Bot
Contains all admin panel keyboard layouts
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Main admin panel keyboard"""
    keyboard = [
        [InlineKeyboardButton("👥 Kelola User", callback_data="admin_users")],
        [InlineKeyboardButton("⚙️ HeroSMS Settings", callback_data="admin_herosms")],
        [InlineKeyboardButton("💳 Qrispy Settings", callback_data="admin_qrispy")],
        [InlineKeyboardButton("🤖 Bot Settings", callback_data="admin_bot")],
        [InlineKeyboardButton("📊 Statistik", callback_data="admin_bot_stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 Refresh Cache", callback_data="admin_refresh_cache")],
        [InlineKeyboardButton("❌ Tutup Panel", callback_data="close_admin")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_users_keyboard(page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """User management keyboard with pagination"""
    keyboard = [
        [
            InlineKeyboardButton("🔍 Cari User", callback_data="admin_search_user"),
            InlineKeyboardButton("➕ Tambah Saldo", callback_data="admin_add_balance")
        ],
        [
            InlineKeyboardButton("🔨 Ban User", callback_data="admin_ban_user"),
            InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_user")
        ],
        [
            InlineKeyboardButton("📋 List User", callback_data="admin_list_users"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh_users")
        ]
    ]
    
    # Pagination if needed
    if total_pages > 1:
        pagination_row = []
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton("◀️", callback_data=f"admin_users_page_{page - 1}")
            )
        pagination_row.append(
            InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop")
        )
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton("▶️", callback_data=f"admin_users_page_{page + 1}")
            )
        keyboard.append(pagination_row)
    
    keyboard.append([InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_herosms_settings_keyboard() -> InlineKeyboardMarkup:
    """HeroSMS API settings keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔄 Update API Key", callback_data="admin_update_herosms_key")],
        [InlineKeyboardButton("💰 Cek Balance", callback_data="admin_check_balance")],
        [InlineKeyboardButton("📊 Cek Harga", callback_data="admin_check_prices")],
        [InlineKeyboardButton("📱 Cek Layanan", callback_data="admin_check_services")],
        [InlineKeyboardButton("🌍 Cek Negara", callback_data="admin_check_countries")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_qrispy_settings_keyboard() -> InlineKeyboardMarkup:
    """Qrispy API settings keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔄 Update API Token", callback_data="admin_update_qrispy_token")],
        [InlineKeyboardButton("🔄 Update Webhook Secret", callback_data="admin_update_webhook_secret")],
        [InlineKeyboardButton("💰 Cek Balance Merchant", callback_data="admin_check_merchant_balance")],
        [InlineKeyboardButton("📊 Lihat Transaksi", callback_data="admin_view_transactions")],
        [InlineKeyboardButton("🧪 Test Webhook", callback_data="admin_test_webhook")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    """General admin settings keyboard"""
    keyboard = [
        [InlineKeyboardButton("💰 Min/Max Top Up", callback_data="admin_set_topup_limits")],
        [InlineKeyboardButton("🏷️ Default Currency", callback_data="admin_set_currency")],
        [InlineKeyboardButton("🔧 Maintenance Mode", callback_data="admin_toggle_maintenance")],
        [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="admin_edit_welcome")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Statistics keyboard"""
    keyboard = [
        [InlineKeyboardButton("📊 Hari Ini", callback_data="admin_stats_today")],
        [InlineKeyboardButton("📅 Minggu Ini", callback_data="admin_stats_week")],
        [InlineKeyboardButton("📆 Bulan Ini", callback_data="admin_stats_month")],
        [InlineKeyboardButton("📈 Semua Waktu", callback_data="admin_stats_all")],
        [InlineKeyboardButton("📋 Export CSV", callback_data="admin_export_csv")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Broadcast confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Kirim", callback_data="admin_broadcast_confirm"),
            InlineKeyboardButton("❌ Batal", callback_data="admin_broadcast_cancel")
        ],
        [
            InlineKeyboardButton("👁️ Preview", callback_data="admin_broadcast_preview")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """User-specific actions keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("💰 Tambah Saldo", callback_data=f"admin_add_balance_{user_id}"),
            InlineKeyboardButton("🔨 Ban", callback_data=f"admin_ban_{user_id}")
        ],
        [
            InlineKeyboardButton("📱 Lihat Aktivasi", callback_data=f"admin_user_activations_{user_id}"),
            InlineKeyboardButton("💳 Lihat Transaksi", callback_data=f"admin_user_transactions_{user_id}")
        ],
        [
            InlineKeyboardButton("📧 Kirim Pesan", callback_data=f"admin_message_{user_id}"),
            InlineKeyboardButton("👤 Detail", callback_data=f"admin_user_detail_{user_id}")
        ],
        [InlineKeyboardButton("◀️ Kembali", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)

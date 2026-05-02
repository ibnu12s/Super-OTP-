from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database.db import Database
from services.hero_sms_api import hero_sms_api
from services.qrispy_api import qrispy_api
from keyboards.admin_keyboards import get_admin_main_keyboard
import logging

logger = logging.getLogger(__name__)
db = Database()

class AdminHandlers:
    @staticmethod
    async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin panel"""
        telegram_id = update.effective_user.id
        user = await db.get_user_by_telegram_id(telegram_id)
        
        if not user or not user.is_admin:
            await update.message.reply_text("❌ Akses ditolak!")
            return
        
        await update.message.reply_text(
            "🔧 *Admin Panel*\n\n"
            "Selamat datang di panel admin.\n"
            "Silakan pilih menu:",
            parse_mode='Markdown',
            reply_markup=get_admin_main_keyboard()
        )
    
    @staticmethod
    async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manage users"""
        query = update.callback_query
        await query.answer()
        
        users = await db.get_all_users(page=1, limit=20)
        
        user_list = "*👥 Daftar User*\n\n"
        
        for user in users:
            status_emoji = "🟢" if user.status.value == "active" else "🔴"
            user_list += (
                f"{status_emoji} ID: {user.telegram_id}\n"
                f"Nama: {user.first_name}\n"
                f"Saldo: Rp {user.balance:,.0f}\n"
                f"Status: {user.status.value}\n\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔍 Cari User", callback_data="admin_search_user")],
            [InlineKeyboardButton("➕ Tambah Saldo User", callback_data="admin_add_balance")],
            [InlineKeyboardButton("🔨 Ban/Unban User", callback_data="admin_ban_user")],
            [InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")]
        ]
        
        await query.message.reply_text(
            user_list,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def admin_hero_sms_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """HeroSMS API settings"""
        query = update.callback_query
        await query.answer()
        
        # Get current settings
        api_key = await db.get_setting("herosms_api_key")
        balance_response = await hero_sms_api.get_balance()
        
        settings_text = (
            "*⚙️ Pengaturan HeroSMS API*\n\n"
            f"API Key: {api_key[:10]}...{api_key[-10:] if api_key and len(api_key) > 20 else '****'}\n"
            f"Status: {'✅ Aktif' if balance_response and 'ACCESS_BALANCE' in str(balance_response) else '❌ Error'}\n"
            f"Balance: {balance_response if balance_response else 'Error'}\n\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Update API Key", callback_data="admin_update_herosms_key")],
            [InlineKeyboardButton("💰 Cek Balance", callback_data="admin_check_balance")],
            [InlineKeyboardButton("📊 Cek Harga", callback_data="admin_check_prices")],
            [InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")]
        ]
        
        await query.message.reply_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def admin_qrispy_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Qrispy API settings"""
        query = update.callback_query
        await query.answer()
        
        api_token = await db.get_setting("qrispy_api_token")
        webhook_secret = await db.get_setting("qrispy_webhook_secret")
        
        settings_text = (
            "*💳 Pengaturan Qrispy API*\n\n"
            f"API Token: {api_token[:10]}...{api_token[-10:] if api_token and len(api_token) > 20 else '****'}\n"
            f"Webhook Secret: {'********' if webhook_secret else 'Belum diatur'}\n"
            f"Webhook URL: {config.WEBHOOK_URL}/webhook/qrispy\n\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Update API Token", callback_data="admin_update_qrispy_token")],
            [InlineKeyboardButton("🔄 Update Webhook Secret", callback_data="admin_update_webhook_secret")],
            [InlineKeyboardButton("💰 Cek Balance Merchant", callback_data="admin_check_merchant_balance")],
            [InlineKeyboardButton("📊 Lihat Transaksi", callback_data="admin_view_transactions")],
            [InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")]
        ]
        
        await query.message.reply_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def admin_bot_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot settings"""
        query = update.callback_query
        await query.answer()
        
        settings_text = (
            "*🤖 Pengaturan Bot*\n\n"
            f"Minimum Top Up: Rp {config.MINIMUM_TOPUP:,.0f}\n"
            f"Maximum Top Up: Rp {config.MAXIMUM_TOPUP:,.0f}\n"
            f"Default Currency: {config.DEFAULT_CURRENCY}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Update Bot Settings", callback_data="admin_update_bot_settings")],
            [InlineKeyboardButton("📊 Statistik", callback_data="admin_bot_stats")],
            [InlineKeyboardButton("◀️ Kembali", callback_data="admin_main")]
        ]
        
        await query.message.reply_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def admin_bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot statistics"""
        query = update.callback_query
        await query.answer()
        
        total_users = await db.get_user_count()
        total_transactions = await db.get_transaction_count()
        total_revenue = await db.get_total_revenue()
        
        stats_text = (
            "*📊 Statistik Bot*\n\n"
            f"Total User: {total_users}\n"
            f"Total Transaksi: {total_transactions}\n"
            f"Total Revenue: Rp {total_revenue or 0:,.0f}\n"
        )
        
        await query.message.reply_text(stats_text, parse_mode='Markdown')
    
    @staticmethod
    async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message to all users"""
        await update.message.reply_text(
            "📢 Masukkan pesan yang ingin Anda broadcast:\n"
            "Kirim /cancel untuk membatalkan."
        )
        return "ADMIN_BROADCAST"
    
    @staticmethod
    async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process broadcast message"""
        message = update.message.text
        
        if message == "/cancel":
            await update.message.reply_text("❌ Broadcast dibatalkan.")
            return ConversationHandler.END
        
        users = await db.get_all_users(limit=1000)
        
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"📢 *Pengumuman*\n\n{message}",
                    parse_mode='Markdown'
                )
                success_count += 1
            except Exception:
                fail_count += 1
                continue
        
        await update.message.reply_text(
            f"✅ Broadcast selesai!\n\n"
            f"Berhasil: {success_count}\n"
            f"Gagal: {fail_count}"
        )
        
        return ConversationHandler.END
    
    @staticmethod
    async def admin_update_herosms_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update HeroSMS API key"""
        await update.message.reply_text(
            "🔑 Masukkan API Key HeroSMS yang baru:\n"
            "Kirim /cancel untuk membatalkan."
        )
        return "ADMIN_UPDATE_HEROSMS_KEY"
    
    @staticmethod
    async def process_update_herosms_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process update HeroSMS API key"""
        new_key = update.message.text
        
        if new_key == "/cancel":
            await update.message.reply_text("❌ Update dibatalkan.")
            return ConversationHandler.END
        
        await db.update_setting("herosms_api_key", new_key)
        
        # Update global settings
        config.HEROSMS_API_KEY = new_key
        
        await update.message.reply_text("✅ API Key HeroSMS berhasil diperbarui!")
        return ConversationHandler.END

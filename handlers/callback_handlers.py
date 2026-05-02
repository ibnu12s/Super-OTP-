"""
Callback Handlers for HeroSMS Bot
Handles all inline keyboard callback queries
"""

import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.db import Database
from services.hero_sms_api import hero_sms_api

logger = logging.getLogger(__name__)
db = Database()

class CallbackHandlers:
    """Centralized callback query handlers"""
    
    @staticmethod
    async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle main menu navigation"""
        from keyboards.user_keyboards import get_main_menu_keyboard
        
        query = update.callback_query
        await query.answer()
        
        await query.message.edit_text(
            "🏠 *Menu Utama*\n\nSilakan pilih menu di bawah:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
    
    @staticmethod
    async def handle_sms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle SMS retrieval callback"""
        query = update.callback_query
        await query.answer("🔄 Mengambil SMS...")
        
        activation_id = query.data.replace("sms_", "")
        
        sms_response = await hero_sms_api.get_all_sms(int(activation_id))
        
        if sms_response.get("data"):
            sms_list = sms_response["data"]
            
            sms_text = f"*📨 SMS untuk Aktivasi #{activation_id}*\n\n"
            
            for i, sms in enumerate(sms_list, 1):
                sms_type = sms.get('type', 'sms')
                type_emoji = "📱" if sms_type == "sms" else "📞"
                
                sms_text += (
                    f"{i}. {type_emoji} *{sms.get('phoneFrom', 'Unknown')}*\n"
                    f"   📝 `{sms.get('text', 'No text')}`\n"
                    f"   🔢 Kode: `{sms.get('code', 'No code')}`\n"
                    f"   📅 {sms.get('date', 'Unknown')}\n\n"
                )
            
            if not sms_list:
                sms_text += "Belum ada SMS diterima.\n"
        else:
            sms_text = "❌ Tidak ada SMS atau aktivasi tidak ditemukan."
        
        await query.message.reply_text(
            sms_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"sms_{activation_id}"),
                    InlineKeyboardButton("✅ Selesai", callback_data=f"finish_{activation_id}")
                ],
                [InlineKeyboardButton("◀️ Kembali", callback_data="check_status")]
            ])
        )
    
    @staticmethod
    async def handle_copy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle copy code callback"""
        query = update.callback_query
        
        # Extract code from callback data
        data_parts = query.data.replace("copy_", "").split("_", 1)
        if len(data_parts) >= 2:
            code = data_parts[1]
            await query.answer(f"Kode: {code}\n(Tersalin ke clipboard)", show_alert=True)
        else:
            await query.answer("Gagal menyalin kode", show_alert=True)
    
    @staticmethod
    async def handle_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pagination navigation"""
        query = update.callback_query
        await query.answer()
        
        # This is handled by specific conversation handlers
        # This is a fallback for orphaned pagination callbacks
        await query.message.edit_text(
            "⏰ Sesi telah berakhir. Silakan mulai ulang.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
            ])
        )
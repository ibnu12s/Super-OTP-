# bot.py (KODE LENGKAP PERBAIKAN)
import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    Defaults
)
from telegram.constants import ParseMode

from config import settings
from database.db import Database
from handlers.user_handlers import UserHandlers
from handlers.admin_handlers import AdminHandlers
from handlers.callback_handlers import CallbackHandlers
from webhook_server import start_webhook_server

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Reduce noise from other loggers
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Database instance
db = Database()

# Conversation States
(
    # Buy Number Flow
    SELECT_SERVICE_FLOW,
    SEARCH_SERVICE_FLOW,
    SELECT_COUNTRY_FLOW,
    SELECT_OPERATOR_FLOW,
    SELECT_OFFER_FLOW,
    CONFIRM_PURCHASE_FLOW,
    
    # Registration/Login Flow
    REGISTER_PASSWORD,
    LOGIN_PASSWORD,
    
    # Top Up Flow
    TOPUP_AMOUNT,
    TOPUP_PAYMENT,
    
    # Admin Flows
    ADMIN_MAIN,
    ADMIN_USERS,
    ADMIN_ADD_BALANCE,
    ADMIN_BAN_USER,
    ADMIN_BROADCAST,
    ADMIN_UPDATE_HEROSMS_KEY,
    ADMIN_UPDATE_QRISPY_TOKEN,
    ADMIN_UPDATE_WEBHOOK_SECRET,
    ADMIN_SETTINGS,
    ADMIN_HEROSMS_SETTINGS,
    ADMIN_QRISPY_SETTINGS,
    ADMIN_BOT_SETTINGS,
    ADMIN_STATS,
    ADMIN_SEARCH_USER,
) = range(25)


class HeroSMSBot:
    """Main Bot Application Class"""
    
    def __init__(self):
        self.app: Optional[Application] = None
        self.start_time = time.time()
        self.user_handler = UserHandlers()
        self.admin_handler = AdminHandlers()
        self.callback_handler = CallbackHandlers()
        
    async def initialize(self):
        """Initialize bot application"""
        logger.info("=" * 60)
        logger.info("🚀 Initializing HeroSMS Bot...")
        logger.info("=" * 60)
        
        # Initialize database
        try:
            await db.initialize()
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            sys.exit(1)
        
        # Build application with custom defaults
        defaults = Defaults(
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            block=False
        )
        
        self.app = (
            ApplicationBuilder()
            .token(settings.BOT_TOKEN)
            .defaults(defaults)
            .concurrent_updates(True)
            .connection_pool_size(100)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .build()
        )
        
        # Register all handlers
        self._register_handlers()
        
        # Register error handler
        self.app.add_error_handler(self._error_handler)
        
        logger.info("✅ Bot initialized successfully")
        
    def _register_handlers(self):
        """Register all command and conversation handlers"""
        
        logger.info("📝 Registering handlers...")
        
        # =====================================================================
        # BASIC COMMANDS
        # =====================================================================
        
        basic_commands = [
            ("start", self.user_handler.start),
            ("help", self.user_handler.help_command),
            ("balance", self.user_handler.check_balance),
            ("profile", self.user_handler.profile),
            ("history", self.user_handler.history),
            ("status", self.user_handler.check_activation_status),
            ("admin", self.admin_handler.admin_panel),
        ]
        
        for command, handler in basic_commands:
            self.app.add_handler(CommandHandler(command, handler))
        
        # =====================================================================
        # BUY NUMBER CONVERSATION FLOW (REAL-TIME, INFINITE SCROLL)
        # =====================================================================
        
        buy_number_conv = ConversationHandler(
            entry_points=[
                CommandHandler("buy", self.user_handler.buy_number_start),
                CallbackQueryHandler(
                    self.user_handler.buy_number_start,
                    pattern="^buy_number$"
                )
            ],
            states={
                # Service Selection
                SELECT_SERVICE_FLOW: [
                    CallbackQueryHandler(
                        self.user_handler.handle_service_selection,
                        pattern="^(service_|services_page_|search_service|back_to_main|all_services|popular_services)"
                    ),
                ],
                
                # Service Search
                SEARCH_SERVICE_FLOW: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.user_handler.handle_service_search
                    ),
                    CommandHandler("cancel", self._cancel_operation),
                ],
                
                # Country Selection
                SELECT_COUNTRY_FLOW: [
                    CallbackQueryHandler(
                        self.user_handler.handle_country_selection,
                        pattern="^(country_|countries_page_|back_to_services)"
                    ),
                ],
                
                # Operator Selection
                SELECT_OPERATOR_FLOW: [
                    CallbackQueryHandler(
                        self.user_handler.handle_operator_selection,
                        pattern="^(operator_|any_operator|back_to_countries)"
                    ),
                ],
                
                # Offer/Tier Selection
                SELECT_OFFER_FLOW: [
                    CallbackQueryHandler(
                        self.user_handler.handle_offer_selection,
                        pattern="^(tier_|back_to_operators)"
                    ),
                ],
                
                # Purchase Confirmation
                CONFIRM_PURCHASE_FLOW: [
                    CallbackQueryHandler(
                        self.user_handler.confirm_purchase,
                        pattern="^(confirm_purchase|cancel_purchase|back_to_tiers)"
                    ),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel_operation),
                CommandHandler("start", self.user_handler.start),
                CallbackQueryHandler(
                    self.user_handler.back_to_main,
                    pattern="^back_to_main$"
                ),
            ],
            allow_reentry=True,
            name="buy_number_conversation",
            persistent=False,
        )
        self.app.add_handler(buy_number_conv)
        
        # =====================================================================
        # REGISTRATION CONVERSATION FLOW
        # =====================================================================
        
        register_conv = ConversationHandler(
            entry_points=[
                CommandHandler("register", self.user_handler.start),
            ],
            states={
                REGISTER_PASSWORD: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.user_handler.register_password
                    ),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel_operation),
            ],
            allow_reentry=True,
            name="register_conversation",
        )
        self.app.add_handler(register_conv)
        
        # =====================================================================
        # LOGIN CONVERSATION FLOW
        # =====================================================================
        
        login_conv = ConversationHandler(
            entry_points=[
                CommandHandler("login", self.user_handler.login),
            ],
            states={
                LOGIN_PASSWORD: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.user_handler.verify_login
                    ),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel_operation),
            ],
            allow_reentry=True,
            name="login_conversation",
        )
        self.app.add_handler(login_conv)
        
        # =====================================================================
        # TOP UP CONVERSATION FLOW
        # =====================================================================
        
        topup_conv = ConversationHandler(
            entry_points=[
                CommandHandler("topup", self.user_handler.topup_start),
                CallbackQueryHandler(
                    self.user_handler.topup_start,
                    pattern="^topup$"
                ),
            ],
            states={
                TOPUP_AMOUNT: [
                    CallbackQueryHandler(
                        self.user_handler.topup_amount_selection,
                        pattern="^(10000|20000|50000|100000|200000|500000|custom_amount|back_to_main)$"
                    ),
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.user_handler.topup_custom_amount
                    ),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel_operation),
                CallbackQueryHandler(
                    self.user_handler.back_to_main,
                    pattern="^back_to_main$"
                ),
            ],
            allow_reentry=True,
            name="topup_conversation",
        )
        self.app.add_handler(topup_conv)
        
        # =====================================================================
        # ADMIN CONVERSATION FLOWS
        # =====================================================================
        
        # Admin Main Flow
        admin_conv = ConversationHandler(
            entry_points=[
                CommandHandler("admin", self.admin_handler.admin_panel),
            ],
            states={
                ADMIN_MAIN: [
                    CallbackQueryHandler(
                        self.admin_handler.handle_admin_menu,
                        pattern="^(admin_users|admin_herosms|admin_qrispy|admin_bot|admin_bot_stats|admin_broadcast|close_admin)$"
                    ),
                ],
                ADMIN_BROADCAST: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.admin_handler.process_broadcast
                    ),
                    CommandHandler("cancel", self._cancel_operation),
                ],
                ADMIN_UPDATE_HEROSMS_KEY: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.admin_handler.update_herosms_key
                    ),
                    CommandHandler("cancel", self._cancel_operation),
                ],
                ADMIN_UPDATE_QRISPY_TOKEN: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.admin_handler.update_qrispy_token
                    ),
                    CommandHandler("cancel", self._cancel_operation),
                ],
                ADMIN_UPDATE_WEBHOOK_SECRET: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.admin_handler.update_webhook_secret
                    ),
                    CommandHandler("cancel", self._cancel_operation),
                ],
                ADMIN_ADD_BALANCE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.admin_handler.process_add_balance
                    ),
                    CommandHandler("cancel", self._cancel_operation),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel_operation),
            ],
            allow_reentry=True,
            name="admin_conversation",
        )
        self.app.add_handler(admin_conv)
        
        # =====================================================================
        # CALLBACK QUERY HANDLERS (GLOBAL)
        # =====================================================================
        
        # Top up callbacks
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.check_topup_status,
                pattern="^check_topup_"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.cancel_topup,
                pattern="^cancel_topup_"
            )
        )
        
        # History callbacks
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.activation_history,
                pattern="^activation_history$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.transaction_history,
                pattern="^transaction_history$"
            )
        )
        
        # Activation management callbacks
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.check_activation_status,
                pattern="^check_status$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                CallbackHandlers.handle_sms_callback,
                pattern="^sms_"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.finish_activation,
                pattern="^finish_"
            )
        )
        
        # Profile callbacks
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.profile,
                pattern="^profile$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.check_balance,
                pattern="^check_balance$"
            )
        )
        
        # Navigation callbacks
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.buy_number_start,
                pattern="^buy_number$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.topup_start,
                pattern="^topup$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.history,
                pattern="^history$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.user_handler.help_command,
                pattern="^help$"
            )
        )
        
        # No operation callback (for display-only buttons)
        self.app.add_handler(
            CallbackQueryHandler(
                self._handle_noop,
                pattern="^noop$"
            )
        )
        
        # Main menu callback
        self.app.add_handler(
            CallbackQueryHandler(
                self._handle_main_menu,
                pattern="^main_menu$"
            )
        )
        
        # =====================================================================
        # ACTIVATION COMMANDS
        # =====================================================================
        
        self.app.add_handler(
            CommandHandler("sms", self.user_handler.get_sms_list)
        )
        self.app.add_handler(
            CommandHandler("finish", self.user_handler.finish_activation)
        )
        self.app.add_handler(
            CommandHandler("cancel_activation", self.user_handler.cancel_activation)
        )
        
        # =====================================================================
        # FALLBACK HANDLER (Unknown commands)
        # =====================================================================
        
        self.app.add_handler(
            MessageHandler(
                filters.COMMAND,
                self._handle_unknown_command
            )
        )
        
        # =====================================================================
        # TEXT MESSAGE HANDLER (for non-command text)
        # =====================================================================
        
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_text_message
            )
        )
        
        logger.info("✅ All handlers registered successfully")
    
    # ========================================================================
    # CALLBACK HANDLERS
    # ========================================================================
    
    @staticmethod
    async def _handle_noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle no-operation callbacks (display only)"""
        query = update.callback_query
        await query.answer()
        # Do nothing, just acknowledge the callback
    
    @staticmethod
    async def _handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle back to main menu"""
        query = update.callback_query
        await query.answer()
        
        from keyboards.user_keyboards import get_main_menu_keyboard
        
        await query.message.edit_text(
            "🏠 *Menu Utama*\n\n"
            "Silakan pilih menu di bawah:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
    
    @staticmethod
    async def _cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation"""
        from keyboards.user_keyboards import get_main_menu_keyboard
        
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "❌ *Operasi Dibatalkan*\n\n"
                "Kembali ke menu utama.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ *Operasi Dibatalkan*\n\n"
                "Kembali ke menu utama.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
        
        # Clear conversation data
        context.user_data.pop('buy_session', None)
        context.user_data.pop('registration', None)
        context.user_data.pop('topup_data', None)
        
        return ConversationHandler.END
    
    @staticmethod
    async def _handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands"""
        command = update.message.text.split()[0]
        
        await update.message.reply_text(
            f"❓ *Perintah Tidak Dikenal:* `{command}`\n\n"
            "Gunakan /help untuk melihat daftar perintah.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    async def _handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle random text messages"""
        text = update.message.text
        
        # Check if user is in a conversation
        if context.user_data.get('buy_session'):
            # User might be trying to search
            return
        
        # Friendly response
        greetings = ['hai', 'halo', 'hello', 'hi', 'hey', 'p', 'ping', 'test']
        if text.lower() in greetings:
            await update.message.reply_text(
                f"👋 Hai! Gunakan /help untuk melihat perintah yang tersedia.\n"
                f"Atau gunakan tombol di bawah:",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "🤔 Saya tidak mengerti pesan Anda.\n"
                "Gunakan /help untuk bantuan atau pilih menu di bawah:",
                reply_markup=get_main_menu_keyboard()
            )
    
    # ========================================================================
    # ERROR HANDLER
    # ========================================================================
    
    async def _error_handler(self, update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(f"Exception while handling update: {context.error}", exc_info=context.error)
        
        # Get error info
        error = context.error
        error_message = str(error)
        error_type = type(error).__name__
        
        # Log the error
        logger.error(f"Update {update} caused error {error_type}: {error_message}")
        
        # Notify user if possible
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ *Terjadi Kesalahan*\n\n"
                    "Maaf, terjadi kesalahan saat memproses permintaan Anda.\n"
                    "Silakan coba lagi atau hubungi admin.\n\n"
                    f"📝 Error: `{error_type}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif update and update.callback_query:
                await update.callback_query.answer(
                    "❌ Terjadi kesalahan. Silakan coba lagi.",
                    show_alert=True
                )
                await update.callback_query.message.reply_text(
                    "❌ Terjadi kesalahan. Gunakan /start untuk memulai ulang."
                )
        except Exception as notify_error:
            logger.error(f"Failed to notify user about error: {notify_error}")
        
        # Notify admin about critical errors
        try:
            if settings.ADMIN_USER_IDS:
                for admin_id in settings.ADMIN_USER_IDS:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"🚨 *Bot Error*\n\n"
                            f"Time: `{datetime.now().isoformat()}`\n"
                            f"Error: `{error_type}`\n"
                            f"Message: `{error_message[:500]}`\n\n"
                            f"Update: `{str(update)[:500]}`"
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
        except Exception:
            pass
    
    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    async def start_webhook(self):
        """Start bot in webhook mode"""
        logger.info("🌐 Starting bot in Webhook mode...")
        
        webhook_url = f"{settings.WEBHOOK_URL}/{settings.BOT_TOKEN}"
        
        try:
            # Delete any existing webhook
            await self.app.bot.delete_webhook()
            
            # Set new webhook
            await self.app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
                max_connections=100,
                secret_token=settings.BOT_TOKEN
            )
            
            logger.info(f"✅ Webhook set: {webhook_url}")
            
            # Start the application with webhook
            await self.app.run_webhook(
                listen=settings.WEBHOOK_LISTEN,
                port=settings.WEBHOOK_PORT,
                url_path=settings.BOT_TOKEN,
                webhook_url=webhook_url,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to start webhook: {e}")
            raise
    
    async def start_polling(self):
        """Start bot in polling mode (for development)"""
        logger.info("🔄 Starting bot in Polling mode...")
        
        try:
            # Delete any existing webhook
            await self.app.bot.delete_webhook(drop_pending_updates=True)
            
            # Start polling
            await self.app.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
                poll_interval=1.0,
                timeout=30
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to start polling: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down bot...")
        
        try:
            if self.app:
                # Stop the application
                await self.app.stop()
                
                # Remove webhook if in webhook mode
                if settings.BOT_MODE == "webhook":
                    await self.app.bot.delete_webhook()
                
                # Close database connections
                await db.close()
                
            logger.info("✅ Bot shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def run(self):
        """Run the bot"""
        await self.initialize()
        
        # Start webhook server in background
        if settings.BOT_MODE == "webhook":
            import threading
            webhook_thread = threading.Thread(
                target=start_webhook_server,
                daemon=True,
                name="WebhookServer"
            )
            webhook_thread.start()
            logger.info("🌐 Webhook server started in background")
        
        # Print startup info
        await self._print_startup_info()
        
        try:
            # Run based on mode
            if settings.BOT_MODE == "webhook":
                await self.start_webhook()
            else:
                await self.start_polling()
                
        except KeyboardInterrupt:
            logger.info("⚠️ Received keyboard interrupt")
        except Exception as e:
            logger.error(f"❌ Bot runtime error: {e}")
        finally:
            await self.shutdown()
    
    async def _print_startup_info(self):
        """Print startup information"""
        try:
            bot_info = await self.app.bot.get_me()
            
            logger.info("=" * 60)
            logger.info(f"🤖 Bot Name: {bot_info.first_name}")
            logger.info(f"👤 Username: @{bot_info.username}")
            logger.info(f"🆔 Bot ID: {bot_info.id}")
            logger.info(f"🌐 Mode: {settings.BOT_MODE.upper()}")
            logger.info(f"📡 Webhook URL: {settings.WEBHOOK_URL}")
            logger.info(f"🔗 HeroSMS API: {settings.HEROSMS_API_URL}")
            logger.info(f"💳 Qrispy API: {settings.QRISPY_API_URL}")
            logger.info(f"👑 Admin IDs: {settings.ADMIN_USER_IDS}")
            logger.info(f"💾 Database: PostgreSQL")
            logger.info(f"⏰ Start Time: {datetime.now().isoformat()}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")


# ============================================================================
# CALLBACK HANDLERS (Separate file for organization)
# ============================================================================

class CallbackHandlers:
    """Additional callback handlers"""
    
    @staticmethod
    async def handle_sms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle SMS callback from status menu"""
        query = update.callback_query
        await query.answer()
        
        activation_id = query.data.replace("sms_", "")
        
        from services.hero_sms_api import hero_sms_api
        
        loading_msg = await query.message.reply_text(
            "🔄 *Mengambil SMS...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        sms_response = await hero_sms_api.get_all_sms(int(activation_id))
        
        await loading_msg.delete()
        
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


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def setup_signal_handlers(bot_instance: HeroSMSBot):
    """Setup signal handlers for graceful shutdown"""
    
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("⚠️ Received shutdown signal")
        for task in asyncio.all_tasks(loop):
            task.cancel()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: asyncio.create_task(bot_instance.shutdown()))


async def main():
    """Main async function"""
    bot = HeroSMSBot()
    
    # Setup signal handlers
    setup_signal_handlers(bot)
    
    # Run bot
    await bot.run()


if __name__ == "__main__":
    try:
        # Set event loop policy for Windows
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Run main
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("🏁 Bot process terminated")
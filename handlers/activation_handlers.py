"""
Activation Handlers for HeroSMS Bot
Manages all activation-related operations:
- Activation status monitoring
- SMS retrieval and forwarding
- Activation lifecycle management
- Auto-expiry handling
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.db import Database
from services.hero_sms_api import hero_sms_api

logger = logging.getLogger(__name__)
db = Database()

class ActivationHandlers:
    """Handles all activation-related operations"""
    
    # Cache untuk monitoring aktivasi
    _monitoring_tasks: Dict[str, asyncio.Task] = {}
    _activation_cache: Dict[str, Dict] = {}
    
    @staticmethod
    async def start_activation_monitoring(
        user_id: int,
        activation_id: str,
        context: ContextTypes.DEFAULT_TYPE,
        check_interval: int = 15
    ):
        """
        Start monitoring an activation for SMS reception
        Automatically checks for new SMS and notifies user
        
        Args:
            user_id: Telegram user ID
            activation_id: HeroSMS activation ID
            context: Bot context
            check_interval: Seconds between checks
        """
        task_key = f"{user_id}_{activation_id}"
        
        # Cancel existing monitoring for this activation
        if task_key in ActivationHandlers._monitoring_tasks:
            ActivationHandlers._monitoring_tasks[task_key].cancel()
        
        # Create monitoring task
        task = asyncio.create_task(
            ActivationHandlers._monitor_activation(
                user_id, activation_id, context, check_interval
            )
        )
        ActivationHandlers._monitoring_tasks[task_key] = task
        
        logger.info(f"Started monitoring activation {activation_id} for user {user_id}")
    
    @staticmethod
    async def stop_activation_monitoring(user_id: int, activation_id: str):
        """Stop monitoring an activation"""
        task_key = f"{user_id}_{activation_id}"
        
        if task_key in ActivationHandlers._monitoring_tasks:
            ActivationHandlers._monitoring_tasks[task_key].cancel()
            del ActivationHandlers._monitoring_tasks[task_key]
            logger.info(f"Stopped monitoring activation {activation_id} for user {user_id}")
    
    @staticmethod
    async def _monitor_activation(
        user_id: int,
        activation_id: str,
        context: ContextTypes.DEFAULT_TYPE,
        check_interval: int
    ):
        """
        Background task to monitor activation status
        Checks for new SMS and status changes
        """
        last_sms_count = 0
        max_checks = 80  # Maximum checks before stopping (20 minutes at 15s interval)
        checks_done = 0
        
        try:
            while checks_done < max_checks:
                await asyncio.sleep(check_interval)
                checks_done += 1
                
                # Get activation status
                status_response = await hero_sms_api.get_status_v2(int(activation_id))
                
                if not status_response:
                    continue
                
                # Get SMS list
                sms_response = await hero_sms_api.get_all_sms(int(activation_id))
                
                if sms_response.get("data"):
                    sms_list = sms_response["data"]
                    current_count = len(sms_list)
                    
                    # Check for new SMS
                    if current_count > last_sms_count:
                        new_sms = sms_list[last_sms_count:]
                        
                        for sms in new_sms:
                            await ActivationHandlers._send_sms_notification(
                                user_id, activation_id, sms, context
                            )
                        
                        last_sms_count = current_count
                
                # Check if activation is completed or cancelled
                if isinstance(status_response, dict):
                    status = status_response.get("status", "")
                    
                    if status in ["STATUS_OK", "STATUS_CANCEL"]:
                        # Stop monitoring
                        logger.info(f"Activation {activation_id} ended with status: {status}")
                        
                        if status == "STATUS_OK":
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=(
                                    f"✅ *Aktivasi Selesai!*\n\n"
                                    f"🆔 ID: `{activation_id}`\n"
                                    f"Status: *COMPLETED*\n\n"
                                    "Aktivasi telah berhasil diselesaikan."
                                ),
                                parse_mode=ParseMode.MARKDOWN
                            )
                        
                        break
                        
        except asyncio.CancelledError:
            logger.info(f"Monitoring cancelled for activation {activation_id}")
        except Exception as e:
            logger.error(f"Error monitoring activation {activation_id}: {e}")
        finally:
            # Clean up
            task_key = f"{user_id}_{activation_id}"
            ActivationHandlers._monitoring_tasks.pop(task_key, None)
    
    @staticmethod
    async def _send_sms_notification(
        user_id: int,
        activation_id: str,
        sms_data: Dict,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Send SMS notification to user"""
        sms_type = sms_data.get('type', 'sms')
        sms_from = sms_data.get('phoneFrom', 'Unknown')
        sms_text = sms_data.get('text', '')
        sms_code = sms_data.get('code', '')
        sms_date = sms_data.get('date', '')
        
        type_emoji = "📱" if sms_type == "sms" else "📞"
        
        message = (
            f"{type_emoji} *SMS Diterima!*\n\n"
            f"🆔 Aktivasi: `{activation_id}`\n"
            f"📤 Dari: *{sms_from}*\n"
        )
        
        if sms_code:
            message += f"🔢 Kode: `{sms_code}`\n"
        
        if sms_text:
            message += f"📝 Pesan: `{sms_text}`\n"
        
        if sms_date:
            message += f"📅 Waktu: {sms_date}\n"
        
        # Create keyboard for quick actions
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📋 Salin Kode" if sms_code else "📋 Salin Pesan",
                    callback_data=f"copy_{activation_id}_{sms_code or sms_text[:50]}"
                )
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"sms_{activation_id}"),
                InlineKeyboardButton("✅ Selesai", callback_data=f"finish_{activation_id}")
            ]
        ])
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            logger.info(f"SMS notification sent to user {user_id} for activation {activation_id}")
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
    
    @staticmethod
    async def get_activation_details(activation_id: str) -> Optional[Dict]:
        """Get comprehensive activation details"""
        try:
            # Get status V2
            status_response = await hero_sms_api.get_status_v2(int(activation_id))
            
            # Get all SMS
            sms_response = await hero_sms_api.get_all_sms(int(activation_id))
            
            # Get reactivation price
            price_response = await hero_sms_api.reactivation_price(int(activation_id))
            
            details = {
                'activation_id': activation_id,
                'status': status_response if isinstance(status_response, dict) else {},
                'sms_list': sms_response.get('data', []) if sms_response else [],
                'reactivation_price': price_response.get('data', {}).get('price') if price_response else None,
                'last_updated': datetime.now().isoformat()
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting activation details for {activation_id}: {e}")
            return None
    
    @staticmethod
    async def handle_activation_expiry(user_id: int, activation_id: str):
        """Handle expired activation"""
        logger.info(f"Activation {activation_id} expired for user {user_id}")
        
        # Update database
        await db.update_activation_status(activation_id, "expired")
        
        # Stop monitoring
        await ActivationHandlers.stop_activation_monitoring(user_id, activation_id)
    
    @staticmethod
    async def reactivate_number(
        user_id: int,
        activation_id: str,
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """
        Attempt to reactivate a number
        Returns True if successful
        """
        try:
            # Check reactivation price
            price_response = await hero_sms_api.reactivation_price(int(activation_id))
            
            if not price_response or "error" in price_response:
                logger.warning(f"Cannot reactivate {activation_id}: {price_response}")
                return False
            
            reactivation_price = price_response.get('data', {}).get('price', 0)
            
            # Check user balance
            user = await db.get_user_by_telegram_id(user_id)
            if not user or user.balance < reactivation_price:
                logger.warning(f"Insufficient balance for reactivation: {user_id}")
                return False
            
            # Reactivate
            reactivate_response = await hero_sms_api.reactivate(int(activation_id))
            
            if reactivate_response and "activationId" in reactivate_response:
                # Deduct balance
                new_balance = user.balance - reactivation_price
                await db.update_user_balance(user_id, new_balance)
                
                # Record transaction
                await db.create_transaction({
                    'user_id': user_id,
                    'type': 'purchase',
                    'amount': -reactivation_price,
                    'balance_before': user.balance,
                    'balance_after': new_balance,
                    'description': f"Reactivation {activation_id}",
                    'status': 'completed'
                })
                
                # Start monitoring
                await ActivationHandlers.start_activation_monitoring(
                    user_id, activation_id, context
                )
                
                logger.info(f"Reactivation successful: {activation_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Reactivation error for {activation_id}: {e}")
            return False
    
    @staticmethod
    async def get_active_activations_count(user_id: int) -> int:
        """Get count of active activations for a user"""
        try:
            active_response = await hero_sms_api.get_active_activations()
            
            if active_response.get("status") == "success" and active_response.get("data"):
                # Count activations for this user from local DB
                activations = await db.get_user_activations(user_id, limit=100)
                active_count = sum(
                    1 for a in activations
                    if a.status and a.status.value in ['pending', 'waiting_code', 'code_received']
                )
                return active_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting active count for user {user_id}: {e}")
            return 0
    
    @staticmethod
    async def bulk_check_activations(user_ids: List[int]) -> Dict[int, List[Dict]]:
        """
        Check activations for multiple users
        Used by admin panel
        """
        results = {}
        
        for user_id in user_ids:
            activations = await db.get_user_activations(user_id, limit=10)
            results[user_id] = [
                {
                    'activation_id': a.activation_id,
                    'service': a.service_name,
                    'country': a.country_name,
                    'phone': a.phone_number,
                    'status': a.status.value if a.status else 'unknown',
                    'cost': a.cost,
                    'created_at': a.created_at.isoformat() if a.created_at else None
                }
                for a in activations
            ]
        
        return results
    
    @staticmethod
    async def auto_cancel_expired_activations():
        """
        Background task to cancel expired activations
        Should be run periodically (e.g., every 5 minutes)
        """
        try:
            # Get all pending activations
            activations = await db.get_all_pending_activations()
            
            cancelled_count = 0
            for activation in activations:
                if activation.activation_end_time:
                    # Check if expired
                    if datetime.now() > activation.activation_end_time:
                        try:
                            # Cancel via API
                            await hero_sms_api.cancel_activation(int(activation.activation_id))
                            
                            # Update database
                            await db.update_activation_status(activation.activation_id, "expired")
                            
                            # Stop monitoring
                            await ActivationHandlers.stop_activation_monitoring(
                                activation.user_id,
                                activation.activation_id
                            )
                            
                            cancelled_count += 1
                            logger.info(f"Auto-cancelled expired activation: {activation.activation_id}")
                            
                        except Exception as e:
                            logger.error(f"Failed to cancel activation {activation.activation_id}: {e}")
            
            if cancelled_count > 0:
                logger.info(f"Auto-cancelled {cancelled_count} expired activations")
            
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error in auto_cancel_expired_activations: {e}")
            return 0


# Background task scheduler for activation management
class ActivationScheduler:
    """Scheduler for activation-related background tasks"""
    
    _instance = None
    _is_running = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def start(cls, context: ContextTypes.DEFAULT_TYPE):
        """Start the activation scheduler"""
        if cls._is_running:
            return
        
        cls._is_running = True
        
        # Start auto-cancel task
        asyncio.create_task(cls._auto_cancel_loop(context))
        
        # Start monitoring recovery task
        asyncio.create_task(cls._monitoring_recovery_loop(context))
        
        logger.info("Activation scheduler started")
    
    @classmethod
    async def stop(cls):
        """Stop the activation scheduler"""
        cls._is_running = False
        logger.info("Activation scheduler stopped")
    
    @classmethod
    async def _auto_cancel_loop(cls, context: ContextTypes.DEFAULT_TYPE):
        """Loop to auto-cancel expired activations every 5 minutes"""
        while cls._is_running:
            try:
                await ActivationHandlers.auto_cancel_expired_activations()
            except Exception as e:
                logger.error(f"Auto-cancel loop error: {e}")
            
            await asyncio.sleep(300)  # 5 minutes
    
    @classmethod
    async def _monitoring_recovery_loop(cls, context: ContextTypes.DEFAULT_TYPE):
        """Loop to recover monitoring for active activations"""
        while cls._is_running:
            try:
                # Get all users with active activations
                active_activations = await db.get_all_active_activations()
                
                for activation in active_activations:
                    task_key = f"{activation.user_id}_{activation.activation_id}"
                    
                    # Resume monitoring if not already running
                    if task_key not in ActivationHandlers._monitoring_tasks:
                        await ActivationHandlers.start_activation_monitoring(
                            activation.user_id,
                            activation.activation_id,
                            context
                        )
                        logger.info(f"Recovered monitoring for activation {activation.activation_id}")
                
            except Exception as e:
                logger.error(f"Monitoring recovery error: {e}")
            
            await asyncio.sleep(60)  # 1 minute
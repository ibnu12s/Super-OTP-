"""
Authentication and Authorization Middleware for HeroSMS Bot
Handles:
- User authentication checks
- Admin authorization
- Session management
- Rate limiting
- User status validation
"""

import time
import logging
from functools import wraps
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.db import Database

logger = logging.getLogger(__name__)
db = Database()

# Rate limiting storage
_rate_limit_storage: Dict[int, Dict[str, Any]] = {}

class AuthMiddleware:
    """Authentication middleware for Telegram bot handlers"""
    
    # Cache TTL in seconds
    USER_CACHE_TTL = 300  # 5 minutes
    SESSION_TTL = 3600    # 1 hour
    
    # Rate limiting settings
    MAX_REQUESTS_PER_MINUTE = 30
    MAX_PURCHASES_PER_HOUR = 10
    MAX_TOPUPS_PER_HOUR = 5
    
    def __init__(self):
        self._user_cache: Dict[int, Dict[str, Any]] = {}
        self._session_cache: Dict[str, Dict[str, Any]] = {}
    
    async def authenticate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[Dict]:
        """
        Authenticate user and return user data
        Returns None if authentication fails
        """
        user = update.effective_user
        
        if not user:
            logger.warning("No effective user found")
            return None
        
        telegram_id = user.id
        
        # Check cache first
        cached = self._get_cached_user(telegram_id)
        if cached:
            return cached
        
        # Get from database
        try:
            db_user = await db.get_user_by_telegram_id(telegram_id)
            
            if not db_user:
                logger.info(f"User not registered: {telegram_id}")
                return None
            
            if db_user.status.value == "banned":
                logger.warning(f"Banned user attempted access: {telegram_id}")
                return None
            
            # Build user data
            user_data = {
                'id': db_user.id,
                'telegram_id': db_user.telegram_id,
                'username': db_user.username,
                'first_name': db_user.first_name,
                'last_name': db_user.last_name,
                'balance': db_user.balance,
                'is_admin': db_user.is_admin,
                'status': db_user.status.value,
                'created_at': db_user.created_at
            }
            
            # Cache user data
            self._cache_user(telegram_id, user_data)
            
            return user_data
            
        except Exception as e:
            logger.error(f"Authentication error for user {telegram_id}: {e}")
            return None
    
    def _get_cached_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user from cache if valid"""
        cached = self._user_cache.get(telegram_id)
        
        if cached:
            if time.time() - cached['cached_at'] < self.USER_CACHE_TTL:
                return cached['data']
            else:
                # Expired
                del self._user_cache[telegram_id]
        
        return None
    
    def _cache_user(self, telegram_id: int, user_data: Dict):
        """Cache user data"""
        self._user_cache[telegram_id] = {
            'data': user_data,
            'cached_at': time.time()
        }
    
    def clear_user_cache(self, telegram_id: int):
        """Clear cached user data"""
        self._user_cache.pop(telegram_id, None)
    
    async def check_rate_limit(self, telegram_id: int, action_type: str) -> bool:
        """
        Check if user has exceeded rate limits
        Returns True if rate limit exceeded
        """
        now = time.time()
        
        if telegram_id not in _rate_limit_storage:
            _rate_limit_storage[telegram_id] = {
                'requests': [],
                'purchases': [],
                'topups': []
            }
        
        user_limits = _rate_limit_storage[telegram_id]
        
        # Clean old entries
        user_limits['requests'] = [t for t in user_limits['requests'] if now - t < 60]
        user_limits['purchases'] = [t for t in user_limits['purchases'] if now - t < 3600]
        user_limits['topups'] = [t for t in user_limits['topups'] if now - t < 3600]
        
        # Check limits
        if len(user_limits['requests']) >= self.MAX_REQUESTS_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for user {telegram_id}: requests/min")
            return True
        
        if action_type == 'purchase' and len(user_limits['purchases']) >= self.MAX_PURCHASES_PER_HOUR:
            logger.warning(f"Purchase limit exceeded for user {telegram_id}")
            return True
        
        if action_type == 'topup' and len(user_limits['topups']) >= self.MAX_TOPUPS_PER_HOUR:
            logger.warning(f"Topup limit exceeded for user {telegram_id}")
            return True
        
        # Record action
        user_limits['requests'].append(now)
        if action_type == 'purchase':
            user_limits['purchases'].append(now)
        elif action_type == 'topup':
            user_limits['topups'].append(now)
        
        return False


# Singleton instance
auth_middleware = AuthMiddleware()


# ============================================================================
# DECORATORS
# ============================================================================

def require_auth(func: Callable):
    """
    Decorator to require authentication for handler
    Automatically checks user authentication and injects user data
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = await auth_middleware.authenticate(update, context)
        
        if not user:
            if update.callback_query:
                await update.callback_query.answer(
                    "❌ Anda harus login terlebih dahulu!\nGunakan /start untuk mendaftar.",
                    show_alert=True
                )
            else:
                await update.message.reply_text(
                    "❌ *Akses Ditolak*\n\n"
                    "Anda harus terdaftar untuk menggunakan fitur ini.\n"
                    "Gunakan /start untuk mendaftar.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # Check rate limit
        action_type = _get_action_type(func.__name__)
        is_limited = await auth_middleware.check_rate_limit(user['telegram_id'], action_type)
        
        if is_limited:
            if update.callback_query:
                await update.callback_query.answer(
                    "⏳ Terlalu banyak permintaan. Silakan tunggu sebentar.",
                    show_alert=True
                )
            else:
                await update.message.reply_text(
                    "⏳ *Rate Limit Tercapai*\n\n"
                    "Anda telah mencapai batas permintaan.\n"
                    "Silakan tunggu beberapa saat sebelum mencoba lagi.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # Inject user data into context
        context.user_data['authenticated_user'] = user
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def require_admin(func: Callable):
    """
    Decorator to require admin privileges
    Must be used together with @require_auth
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = context.user_data.get('authenticated_user')
        
        if not user:
            if update.callback_query:
                await update.callback_query.answer(
                    "❌ Anda harus login terlebih dahulu!",
                    show_alert=True
                )
            else:
                await update.message.reply_text(
                    "❌ Anda harus login terlebih dahulu!"
                )
            return
        
        if not user.get('is_admin'):
            logger.warning(f"Non-admin user {user['telegram_id']} attempted admin access")
            
            if update.callback_query:
                await update.callback_query.answer(
                    "🚫 Akses ditolak! Admin only.",
                    show_alert=True
                )
            else:
                await update.message.reply_text(
                    "🚫 *Akses Ditolak*\n\n"
                    "Fitur ini hanya tersedia untuk admin.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def check_user_status(func: Callable):
    """
    Decorator to check user status (active/banned)
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = context.user_data.get('authenticated_user')
        
        if not user:
            return await func(update, context, *args, **kwargs)
        
        if user.get('status') == 'banned':
            if update.callback_query:
                await update.callback_query.answer(
                    "🚫 Akun Anda telah dibanned!",
                    show_alert=True
                )
            else:
                await update.message.reply_text(
                    "🚫 *Akun Dibanned*\n\n"
                    "Akun Anda telah dibanned.\n"
                    "Hubungi admin untuk informasi lebih lanjut.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def validate_session(func: Callable):
    """
    Decorator to validate user session
    Checks if session is still valid and refreshes if needed
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = context.user_data.get('authenticated_user')
        
        if user:
            # Check if session needs refresh
            last_activity = context.user_data.get('last_activity', 0)
            now = time.time()
            
            if now - last_activity > AuthMiddleware.SESSION_TTL:
                # Refresh from database
                db_user = await db.get_user_by_telegram_id(user['telegram_id'])
                
                if db_user:
                    # Update cached data
                    user['balance'] = db_user.balance
                    user['status'] = db_user.status.value
                    auth_middleware._cache_user(user['telegram_id'], user)
                
                context.user_data['last_activity'] = now
            else:
                context.user_data['last_activity'] = now
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_action_type(handler_name: str) -> str:
    """Determine action type from handler name for rate limiting"""
    handler_lower = handler_name.lower()
    
    if any(word in handler_lower for word in ['buy', 'purchase', 'order']):
        return 'purchase'
    elif any(word in handler_lower for word in ['topup', 'deposit', 'add_balance']):
        return 'topup'
    else:
        return 'general'


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
Example usage in handlers:

from middleware.auth_middleware import require_auth, require_admin, check_user_status

class UserHandlers:
    
    @staticmethod
    @require_auth
    @check_user_status
    async def buy_number(update, context):
        # User is authenticated and active
        user = context.user_data['authenticated_user']
        # ... handler logic
    
    @staticmethod
    @require_auth
    @require_admin
    async def admin_panel(update, context):
        # User is authenticated AND admin
        user = context.user_data['authenticated_user']
        # ... admin logic
"""


# ============================================================================
# MIDDLEWARE CLEANUP
# ============================================================================

async def cleanup_expired_sessions():
    """Clean up expired sessions periodically"""
    while True:
        try:
            now = time.time()
            
            # Clean rate limit storage
            for user_id in list(_rate_limit_storage.keys()):
                user_limits = _rate_limit_storage[user_id]
                user_limits['requests'] = [t for t in user_limits['requests'] if now - t < 60]
                user_limits['purchases'] = [t for t in user_limits['purchases'] if now - t < 3600]
                user_limits['topups'] = [t for t in user_limits['topups'] if now - t < 3600]
                
                # Remove empty entries
                if not any(user_limits.values()):
                    del _rate_limit_storage[user_id]
            
            # Clean user cache
            for user_id in list(auth_middleware._user_cache.keys()):
                cached = auth_middleware._user_cache[user_id]
                if now - cached['cached_at'] > AuthMiddleware.USER_CACHE_TTL:
                    del auth_middleware._user_cache[user_id]
            
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
        
        await asyncio.sleep(300)  # Run every 5 minutes


# Import asyncio at the end to avoid circular import
import asyncio
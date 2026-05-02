"""
Handlers package for HeroSMS Bot
Contains all Telegram bot handlers for:
- User interactions (buy, topup, profile, etc.)
- Admin panel management
- Payment processing
- Activation management
- Callback handling
"""

from handlers.user_handlers import UserHandlers
from handlers.admin_handlers import AdminHandlers
from handlers.payment_handlers import app as payment_app
from handlers.activation_handlers import ActivationHandlers
from handlers.callback_handlers import CallbackHandlers

__all__ = [
    'UserHandlers',
    'AdminHandlers',
    'ActivationHandlers',
    'CallbackHandlers',
    'payment_app',
]

__version__ = '1.0.0'
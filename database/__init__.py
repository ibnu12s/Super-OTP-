"""
Database package for HeroSMS Bot
Handles all database operations including:
- User management
- Transaction tracking
- Activation management
- Settings management
"""

from database.db import Database
from database.models import (
    Base,
    User,
    Transaction,
    Topup,
    Activation,
    Service,
    Country,
    AdminSettings,
    UserStatus,
    TransactionType,
    TransactionStatus,
    ActivationStatus
)

__all__ = [
    'Database',
    'Base',
    'User',
    'Transaction',
    'Topup',
    'Activation',
    'Service',
    'Country',
    'AdminSettings',
    'UserStatus',
    'TransactionType',
    'TransactionStatus',
    'ActivationStatus',
]

__version__ = '1.0.0'
__author__ = 'HeroSMS Bot Team'
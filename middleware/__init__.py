"""
Middleware package for HeroSMS Bot
Provides middleware components for:
- Authentication and authorization
- Rate limiting
- Logging
- Session management
- Data validation
"""

from middleware.auth_middleware import (
    AuthMiddleware,
    require_auth,
    require_admin,
    check_user_status,
    validate_session,
)

__all__ = [
    'AuthMiddleware',
    'require_auth',
    'require_admin',
    'check_user_status',
    'validate_session',
]

__version__ = '1.0.0'

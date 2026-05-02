"""
Services package for HeroSMS Bot
Contains all external API integrations:
- HeroSMS API (SMS activation service)
- Qrispy API (Payment gateway)
- Webhook service (Incoming notifications)
"""

from services.hero_sms_api import HeroSMSAPI, hero_sms_api
from services.qrispy_api import QrispyAPI, qrispy_api
from services.webhook_service import WebhookService, webhook_service

__all__ = [
    'HeroSMSAPI',
    'hero_sms_api',
    'QrispyAPI',
    'qrispy_api',
    'WebhookService',
    'webhook_service',
]

__version__ = '1.0.0'
__author__ = 'HeroSMS Bot Team'
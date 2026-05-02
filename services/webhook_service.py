"""
Webhook Service for HeroSMS Bot
Manages webhook configurations and processing
"""

import hmac
import hashlib
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

class WebhookService:
    """Service for managing webhook operations"""
    
    def __init__(self):
        self.qrispy_webhook_secret = settings.QRISPY_WEBHOOK_SECRET
        self.webhook_url = settings.WEBHOOK_URL
    
    def verify_qrispy_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Qrispy webhook signature using HMAC-SHA256
        
        Args:
            payload: Raw request body bytes
            signature: X-Qrispy-Signature header value
            
        Returns:
            True if signature is valid
        """
        try:
            expected = hmac.new(
                self.qrispy_webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(expected, signature)
            
            if not is_valid:
                logger.warning("⚠️ Invalid webhook signature received")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    def verify_herosms_webhook(self, data: Dict) -> bool:
        """
        Verify HeroSMS webhook data structure
        
        Args:
            data: Webhook payload data
            
        Returns:
            True if data is valid
        """
        required_fields = ['activationId', 'service', 'text', 'country', 'receivedAt']
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field in HeroSMS webhook: {field}")
                return False
        
        return True
    
    def parse_qrispy_webhook(self, data: Dict) -> Optional[Dict]:
        """
        Parse Qrispy webhook payload
        
        Args:
            data: Webhook payload
            
        Returns:
            Parsed payment data or None if invalid
        """
        try:
            event = data.get('event')
            
            if event == 'payment.received':
                payment_data = data.get('data', {})
                
                return {
                    'event': event,
                    'qris_id': payment_data.get('qris_id'),
                    'amount': payment_data.get('amount'),
                    'received_amount': payment_data.get('received_amount'),
                    'payment_reference': payment_data.get('payment_reference'),
                    'paid_at': payment_data.get('paid_at'),
                    'unique_id': payment_data.get('unique_id')
                }
            
            elif event == 'payment.expired':
                payment_data = data.get('data', {})
                
                return {
                    'event': event,
                    'qris_id': payment_data.get('qris_id'),
                    'expired_at': payment_data.get('expired_at')
                }
            
            elif event == 'payment.cancelled':
                payment_data = data.get('data', {})
                
                return {
                    'event': event,
                    'qris_id': payment_data.get('qris_id'),
                    'cancelled_at': payment_data.get('cancelled_at')
                }
            
            else:
                logger.info(f"Unknown webhook event: {event}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing Qrispy webhook: {e}")
            return None
    
    def parse_herosms_webhook(self, data: Dict) -> Optional[Dict]:
        """
        Parse HeroSMS webhook payload
        
        Args:
            data: Webhook payload
            
        Returns:
            Parsed SMS data or None if invalid
        """
        try:
            return {
                'activation_id': data.get('activationId'),
                'service': data.get('service'),
                'text': data.get('text'),
                'code': data.get('code'),
                'country': data.get('country'),
                'received_at': data.get('receivedAt')
            }
        except Exception as e:
            logger.error(f"Error parsing HeroSMS webhook: {e}")
            return None
    
    def generate_payment_reference(self, user_id: int, amount: int) -> str:
        """
        Generate unique payment reference
        
        Args:
            user_id: Telegram user ID
            amount: Payment amount
            
        Returns:
            Unique payment reference string
        """
        timestamp = int(datetime.now().timestamp())
        return f"TOPUP-{user_id}-{amount}-{timestamp}"
    
    def parse_payment_reference(self, reference: str) -> Optional[Dict]:
        """
        Parse payment reference to extract user and amount info
        
        Args:
            reference: Payment reference string
            
        Returns:
            Parsed info or None if invalid format
        """
        try:
            parts = reference.split('-')
            
            if parts[0] == 'TOPUP' and len(parts) >= 4:
                return {
                    'type': 'topup',
                    'user_id': int(parts[1]),
                    'amount': int(parts[2]),
                    'timestamp': int(parts[3])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing payment reference: {e}")
            return None
    
    def generate_webhook_response(self, status: str, message: str) -> Dict:
        """
        Generate standardized webhook response
        
        Args:
            status: Response status (success/error)
            message: Response message
            
        Returns:
            Response dictionary
        """
        return {
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }


# Singleton instance
webhook_service = WebhookService()
import httpx
import hmac
import hashlib
import json
from typing import Dict, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)

class QrispyAPI:
    def __init__(self):
        self.api_token = settings.QRISPY_API_TOKEN
        self.webhook_secret = settings.QRISPY_WEBHOOK_SECRET
        self.base_url = settings.QRISPY_API_URL
        self.headers = {
            "X-API-Token": self.api_token,
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make HTTP request to Qrispy API"""
        async with httpx.AsyncClient() as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(f"{self.base_url}{endpoint}", 
                                               params=params, 
                                               headers=self.headers)
                elif method.upper() == "POST":
                    response = await client.post(f"{self.base_url}{endpoint}", 
                                                json=data, 
                                                headers=self.headers)
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Qrispy API Error: {e}")
                return {"error": str(e)}
    
    async def generate_qris(self, amount: int, payment_reference: Optional[str] = None, 
                           return_url: Optional[str] = None) -> Dict:
        """Generate new QRIS code for payment"""
        data = {"amount": amount}
        if payment_reference:
            data["payment_reference"] = payment_reference
        if return_url:
            data["return_url"] = return_url
        
        return await self._make_request("POST", "/api/payment/qris/generate", data=data)
    
    async def check_qris_status(self, qris_id: str) -> Dict:
        """Check payment status of a QRIS code"""
        return await self._make_request("GET", f"/api/payment/qris/{qris_id}/status")
    
    async def cancel_qris(self, qris_id: str) -> Dict:
        """Cancel a pending QRIS code"""
        return await self._make_request("POST", f"/api/payment/qris/{qris_id}/cancel")
    
    async def get_transactions(self, status: Optional[str] = None, 
                              generated_via: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None,
                              limit: int = 20) -> Dict:
        """Get paginated list of QRIS transactions"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        if generated_via:
            params["generated_via"] = generated_via
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        return await self._make_request("GET", "/api/payment/transactions", params=params)
    
    async def get_balance(self) -> Dict:
        """Check current merchant balance"""
        return await self._make_request("GET", "/api/payment/balance")
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature using HMAC-SHA256"""
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Webhook signature verification error: {e}")
            return False

# Singleton instance
qrispy_api = QrispyAPI()
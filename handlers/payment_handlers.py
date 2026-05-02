from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from database.db import Database
from services.qrispy_api import qrispy_api
import logging

logger = logging.getLogger(__name__)
db = Database()

app = FastAPI()

@app.post("/webhook/qrispy")
async def qrispy_webhook(request: Request):
    """Handle Qrispy payment webhook"""
    try:
        # Get payload and signature
        payload = await request.body()
        signature = request.headers.get("X-Qrispy-Signature")
        
        if not signature:
            raise HTTPException(status_code=400, detail="Missing signature header")
        
        # Verify signature
        if not qrispy_api.verify_webhook_signature(payload, signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        data = json.loads(payload)
        
        if data.get("event") == "payment.received":
            payment_data = data["data"]
            
            # Get payment reference to find user
            payment_ref = payment_data.get("payment_reference")
            
            if payment_ref and payment_ref.startswith("TOPUP-"):
                # Parse payment reference: TOPUP-{telegram_id}-{amount}-{timestamp}
                parts = payment_ref.split("-")
                telegram_id = int(parts[1])
                amount = int(parts[2])
                qris_id = payment_data.get("qris_id")
                
                # Update topup status
                await db.update_topup_by_qris_id(qris_id, "completed", payment_data.get("paid_at"))
                
                # Get user and update balance
                user = await db.get_user_by_telegram_id(telegram_id)
                if user:
                    new_balance = user.balance + amount
                    await db.update_user_balance(telegram_id, new_balance)
                    
                    # Create transaction record
                    await db.create_transaction({
                        'user_id': telegram_id,
                        'type': 'topup',
                        'amount': amount,
                        'balance_before': user.balance,
                        'balance_after': new_balance,
                        'description': f"Top up via QRIS - {qris_id}",
                        'status': 'completed',
                        'payment_reference': payment_ref
                    })
                    
                    logger.info(f"Payment processed: User {telegram_id}, Amount {amount}")
                    
                    # Notify user via bot (if bot instance available)
                    # You can implement this based on your architecture
                    
                    return JSONResponse({
                        "status": "success",
                        "message": "Payment processed successfully"
                    })
                else:
                    logger.error(f"User not found: {telegram_id}")
                    raise HTTPException(status_code=404, detail="User not found")
            else:
                logger.warning(f"Invalid payment reference: {payment_ref}")
                raise HTTPException(status_code=400, detail="Invalid payment reference")
        else:
            return JSONResponse({
                "status": "success",
                "message": "Event received but not processed"
            })
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/webhook/hero-sms")
async def herosms_webhook(request: Request):
    """Handle HeroSMS incoming SMS webhook"""
    try:
        data = await request.json()
        
        activation_id = data.get("activationId")
        service = data.get("service")
        text = data.get("text")
        code = data.get("code")
        country = data.get("country")
        received_at = data.get("receivedAt")
        
        logger.info(f"HeroSMS Webhook received: Activation {activation_id}, Service {service}")
        
        # Update activation in database
        if activation_id:
            await db.update_activation_sms(
                activation_id=activation_id,
                sms_code=code,
                sms_text=text
            )
        
        return JSONResponse({
            "status": "success",
            "message": "Webhook processed successfully"
        })
    
    except Exception as e:
        logger.error(f"HeroSMS webhook error: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

import uvicorn
from handlers.payment_handlers import app
from config import settings
import logging

logger = logging.getLogger(__name__)

def start_webhook_server():
    """Start FastAPI webhook server"""
    logger.info("Starting webhook server...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    start_webhook_server()
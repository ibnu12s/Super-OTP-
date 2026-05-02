from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Bot Settings
    BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"
    BOT_USERNAME: str = "YourBotUsername"
    
    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/hero_sms_bot"
    
    # HeroSMS Settings
    HEROSMS_API_URL: str = "https://hero-sms.com/api/v1"
    HEROSMS_API_KEY: str = "YOUR_HEROSMS_API_KEY"
    HEROSMS_STUB_URL: str = "https://hero-sms.com/stubs/handler_api.php"
    
    # Qrispy Settings
    QRISPY_API_URL: str = "https://api.qrispy.id"
    QRISPY_API_TOKEN: str = "YOUR_QRISPY_API_TOKEN"
    QRISPY_MERCHANT_ID: str = "YOUR_MERCHANT_ID"
    QRISPY_WEBHOOK_SECRET: str = "YOUR_WEBHOOK_SECRET"
    
    # Webhook Settings
    WEBHOOK_URL: str = "https://your-domain.com"
    WEBHOOK_PORT: int = 8443
    WEBHOOK_LISTEN: str = "0.0.0.0"
    
    # Redis Settings (for session management)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Admin Settings
    ADMIN_USER_IDS: list = [123456789]  # List of admin Telegram user IDs
    
    # Payment Settings
    DEFAULT_CURRENCY: str = "IDR"
    MINIMUM_TOPUP: int = 10000
    MAXIMUM_TOPUP: int = 10000000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
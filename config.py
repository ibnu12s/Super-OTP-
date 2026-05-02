from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Bot Settings
    BOT_TOKEN: str = "8743610980:AAGGKJ3Y_ABgeXQIoUQYkt73lAU3NG4YWq4"
    BOT_USERNAME: str = "SuperOTPMurah_bot"
    
    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/hero_sms_bot"
    
    # HeroSMS Settings
    HEROSMS_API_URL: str = "https://hero-sms.com/api/v1"
    HEROSMS_API_KEY: str = "9A127e16bb92A0d07be58b73bb597756"
    HEROSMS_STUB_URL: str = "https://hero-sms.com/stubs/handler_api.php"
    
    # Qrispy Settings
    QRISPY_API_URL: str = "https://api.qrispy.id"
    QRISPY_API_TOKEN: str = "cki_svdCcCw81k5E6M1QsfcDwv7XXkWkTxh9nKDEwlZ5V22xV026"
    QRISPY_MERCHANT_ID: str = "Super-otp"
    QRISPY_WEBHOOK_SECRET: str = "whsec_XBonmWmuOy2PHOhjoYozwEYgkoAvxMxl"
    
    # Webhook Settings
    WEBHOOK_URL: str = "https://super-otp.biz.id"
    WEBHOOK_PORT: int = 8443
    WEBHOOK_LISTEN: str = "0.0.0.0"
    
    # Redis Settings (for session management)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Admin Settings
    ADMIN_USER_IDS: list = [848395494]  # List of admin Telegram user IDs
    
    # Payment Settings
    DEFAULT_CURRENCY: str = "IDR"
    MINIMUM_TOPUP: int = 10000
    MAXIMUM_TOPUP: int = 10000000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

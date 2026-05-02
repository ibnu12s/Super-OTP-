from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, delete, func
from database.models import Base, User, Transaction, Topup, Activation, AdminSettings
from config import settings
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.engine = None
        self.session_factory = None
    
    async def initialize(self):
        """Initialize database connection"""
        try:
            self.engine = create_async_engine(
                settings.DATABASE_URL,
                echo=False,
                pool_size=20,
                max_overflow=10
            )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Initialize default settings
            await self.initialize_default_settings()
            
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    async def initialize_default_settings(self):
        """Initialize default admin settings"""
        default_settings = [
            {
                "key": "herosms_api_key",
                "value": settings.HEROSMS_API_KEY,
                "description": "HeroSMS API Key"
            },
            {
                "key": "qrispy_api_token",
                "value": settings.QRISPY_API_TOKEN,
                "description": "Qrispy API Token"
            },
            {
                "key": "qrispy_webhook_secret",
                "value": settings.QRISPY_WEBHOOK_SECRET,
                "description": "Qrispy Webhook Secret"
            },
            {
                "key": "min_topup",
                "value": str(settings.MINIMUM_TOPUP),
                "description": "Minimum top up amount"
            },
            {
                "key": "max_topup",
                "value": str(settings.MAXIMUM_TOPUP),
                "description": "Maximum top up amount"
            }
        ]
        
        for setting in default_settings:
            await self.create_or_update_setting(
                setting["key"],
                setting["value"],
                setting["description"]
            )
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.session_factory()
    
    # ========== User Methods ==========
    async def create_user(self, user_data: Dict) -> Optional[User]:
        """Create new user"""
        async with await self.get_session() as session:
            try:
                user = User(**user_data)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                return user
            except Exception as e:
                await session.rollback()
                logger.error(f"Create user error: {e}")
                return None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    async def update_user_balance(self, telegram_id: int, new_balance: float):
        """Update user balance"""
        async with await self.get_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(balance=new_balance)
            )
            await session.commit()
    
    async def get_all_users(self, page: int = 1, limit: int = 20) -> List[User]:
        """Get all users with pagination"""
        offset = (page - 1) * limit
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).offset(offset).limit(limit)
            )
            return result.scalars().all()
    
    async def get_user_count(self) -> int:
        """Get total user count"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(func.count(User.id))
            )
            return result.scalar()
    
    # ========== Transaction Methods ==========
    async def create_transaction(self, transaction_data: Dict) -> Optional[Transaction]:
        """Create new transaction"""
        async with await self.get_session() as session:
            try:
                transaction = Transaction(**transaction_data)
                session.add(transaction)
                await session.commit()
                await session.refresh(transaction)
                return transaction
            except Exception as e:
                await session.rollback()
                logger.error(f"Create transaction error: {e}")
                return None
    
    async def get_user_transactions(self, telegram_id: int, limit: int = 20) -> List[Transaction]:
        """Get user transactions"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Transaction)
                .where(Transaction.user_id == telegram_id)
                .order_by(Transaction.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_transaction_count(self) -> int:
        """Get total transaction count"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(func.count(Transaction.id))
            )
            return result.scalar()
    
    async def get_total_revenue(self) -> float:
        """Get total revenue from topups"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(func.sum(Transaction.amount))
                .where(
                    Transaction.type == "topup",
                    Transaction.status == "completed"
                )
            )
            return result.scalar() or 0.0
    
    # ========== Topup Methods ==========
    async def create_topup(self, topup_data: Dict) -> Optional[Topup]:
        """Create new topup"""
        async with await self.get_session() as session:
            try:
                topup = Topup(**topup_data)
                session.add(topup)
                await session.commit()
                await session.refresh(topup)
                return topup
            except Exception as e:
                await session.rollback()
                logger.error(f"Create topup error: {e}")
                return None
    
    async def update_topup_status(self, qris_id: str, status: str, paid_at: Optional[str] = None):
        """Update topup status"""
        async with await self.get_session() as session:
            values = {"status": status}
            if paid_at:
                values["paid_at"] = paid_at
            
            await session.execute(
                update(Topup)
                .where(Topup.qris_id == qris_id)
                .values(**values)
            )
            await session.commit()
    
    async def get_topup_by_qris_id(self, qris_id: str) -> Optional[Topup]:
        """Get topup by QRIS ID"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Topup).where(Topup.qris_id == qris_id)
            )
            return result.scalar_one_or_none()
    
    # ========== Activation Methods ==========
    async def create_activation(self, activation_data: Dict) -> Optional[Activation]:
        """Create new activation"""
        async with await self.get_session() as session:
            try:
                activation = Activation(**activation_data)
                session.add(activation)
                await session.commit()
                await session.refresh(activation)
                return activation
            except Exception as e:
                await session.rollback()
                logger.error(f"Create activation error: {e}")
                return None
    
    async def get_user_activations(self, telegram_id: int, limit: int = 20) -> List[Activation]:
        """Get user activations"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Activation)
                .where(Activation.user_id == telegram_id)
                .order_by(Activation.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def update_activation_sms(self, activation_id: str, sms_code: Optional[str], sms_text: Optional[str]):
        """Update activation with received SMS"""
        async with await self.get_session() as session:
            await session.execute(
                update(Activation)
                .where(Activation.activation_id == activation_id)
                .values(
                    sms_code=sms_code,
                    sms_text=sms_text,
                    status="code_received"
                )
            )
            await session.commit()
    
    # ========== Settings Methods ==========
    async def create_or_update_setting(self, key: str, value: str, description: Optional[str] = None):
        """Create or update admin setting"""
        async with await self.get_session() as session:
            existing = await session.execute(
                select(AdminSettings).where(AdminSettings.setting_key == key)
            )
            existing = existing.scalar_one_or_none()
            
            if existing:
                existing.setting_value = value
                if description:
                    existing.description = description
            else:
                setting = AdminSettings(
                    setting_key=key,
                    setting_value=value,
                    description=description
                )
                session.add(setting)
            
            await session.commit()
    
    async def get_setting(self, key: str) -> Optional[str]:
        """Get admin setting value"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(AdminSettings).where(AdminSettings.setting_key == key)
            )
            setting = result.scalar_one_or_none()
            return setting.setting_value if setting else None
    
    async def update_setting(self, key: str, value: str):
        """Update admin setting"""
        await self.create_or_update_setting(key, value)

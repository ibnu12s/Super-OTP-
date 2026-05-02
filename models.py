from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class UserStatus(enum.Enum):
    ACTIVE = "active"
    BANNED = "banned"
    INACTIVE = "inactive"

class TransactionType(enum.Enum):
    TOPUP = "topup"
    PURCHASE = "purchase"
    REFUND = "refund"
    BONUS = "bonus"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ActivationStatus(enum.Enum):
    PENDING = "pending"
    WAITING_CODE = "waiting_code"
    CODE_RECEIVED = "code_received"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    balance = Column(Float, default=0.0)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user")
    activations = relationship("Activation", back_populates="user")
    topups = relationship("Topup", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    payment_reference = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="transactions")

class Topup(Base):
    __tablename__ = "topups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="qris")
    qris_id = Column(String(255), nullable=True)
    qris_url = Column(Text, nullable=True)
    qris_image_url = Column(Text, nullable=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="topups")

class Activation(Base):
    __tablename__ = "activations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    activation_id = Column(String(255), nullable=True)  # HeroSMS activation ID
    service_code = Column(String(10), nullable=False)
    service_name = Column(String(255), nullable=True)
    country_id = Column(Integer, nullable=False)
    country_name = Column(String(255), nullable=True)
    operator = Column(String(100), nullable=True)
    phone_number = Column(String(50), nullable=True)
    cost = Column(Float, nullable=True)
    currency = Column(Integer, default=840)
    status = Column(Enum(ActivationStatus), default=ActivationStatus.PENDING)
    sms_code = Column(String(50), nullable=True)
    sms_text = Column(Text, nullable=True)
    can_get_another_sms = Column(Boolean, default=False)
    activation_time = Column(DateTime(timezone=True), nullable=True)
    activation_end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="activations")

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_code = Column(String(10), unique=True, nullable=False)
    service_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Country(Base):
    __tablename__ = "countries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    country_id = Column(Integer, unique=True, nullable=False)
    country_name = Column(String(255), nullable=False)
    country_name_ru = Column(String(255), nullable=True)
    country_name_zh = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AdminSettings(Base):
    __tablename__ = "admin_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(255), unique=True, nullable=False)
    setting_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
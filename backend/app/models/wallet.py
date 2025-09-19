from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base

class CryptoWallet(Base):
    __tablename__ = "crypto_wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_name = Column(String, nullable=False)
    wallet_address = Column(String, nullable=False)
    wallet_type = Column(String, nullable=False)  # bitcoin, ethereum, etc.
    current_balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

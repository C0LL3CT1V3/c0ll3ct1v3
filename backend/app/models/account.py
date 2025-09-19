from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_name = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    routing_number = Column(String, nullable=False)
    account_type = Column(String, nullable=False)  # checking, savings, business
    current_balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

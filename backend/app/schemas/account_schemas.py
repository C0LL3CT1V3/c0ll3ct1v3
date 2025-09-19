from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BankAccountBase(BaseModel):
    account_name: str
    bank_name: str
    account_number: str
    routing_number: str
    account_type: str
    current_balance: float = 0.0

class BankAccountCreate(BankAccountBase):
    pass

class BankAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    bank_name: Optional[str] = None
    current_balance: Optional[float] = None

class BankAccount(BankAccountBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

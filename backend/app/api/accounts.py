from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.account import BankAccount as BankAccountModel
from ..schemas.account_schemas import BankAccountCreate, BankAccountUpdate, BankAccount

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("/", response_model=List[BankAccount])
def get_accounts(db: Session = Depends(get_db)):
    return db.query(BankAccountModel).filter(BankAccountModel.is_active == True).all()

@router.post("/", response_model=BankAccount)
def create_account(account: BankAccountCreate, db: Session = Depends(get_db)):
    db_account = BankAccountModel(**account.dict())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/{account_id}", response_model=BankAccount)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(BankAccountModel).filter(BankAccountModel.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

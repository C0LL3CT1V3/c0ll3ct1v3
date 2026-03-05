from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.account import BankAccount as BankAccountModel
from ..models.user import User
from ..schemas.account_schemas import BankAccountCreate, BankAccountUpdate, BankAccount
from ..api.auth import get_current_auth_context, get_current_user
from ..utils.security import AuthContext, enforce_recent_mfa

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("/", response_model=List[BankAccount])
def get_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(BankAccountModel)
        .filter(BankAccountModel.is_active.is_(True), BankAccountModel.user_id == current_user.id)
        .all()
    )

@router.post("/", response_model=BankAccount)
def create_account(
    account: BankAccountCreate,
    current_user: User = Depends(get_current_user),
    auth_context: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
):
    # Treat account creation as a sensitive finance action requiring step-up MFA.
    try:
        enforce_recent_mfa(auth_context)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    db_account = BankAccountModel(**account.model_dump(), user_id=current_user.id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/{account_id}", response_model=BankAccount)
def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(BankAccountModel)
        .filter(BankAccountModel.id == account_id, BankAccountModel.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

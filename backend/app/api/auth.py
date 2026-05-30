from datetime import timedelta
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.user_schemas import UserCreate, UserLogin, User as UserSchema, Token
from ..utils.security import (
    AuthContext,
    create_access_token,
    enforce_recent_mfa,
    get_password_hash,
    verify_auth0_token,
    verify_password,
)
from ..config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

bearer_scheme = HTTPBearer(auto_error=False)

def get_user_by_email(db: Session, email: str):
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_auth0_sub(db: Session, auth0_sub: str):
    """Get user by Auth0 subject."""
    return db.query(User).filter(User.auth0_sub == auth0_sub).first()


def _provision_or_bind_user(db: Session, auth_context: AuthContext) -> User:
    """Ensure incoming Auth0 identity maps to a local user record."""
    # Existing by subject
    existing = get_user_by_auth0_sub(db, auth_context.sub)
    if existing:
        if auth_context.email and existing.email != auth_context.email:
            existing.email = auth_context.email
        if auth_context.name and existing.name != auth_context.name:
            existing.name = auth_context.name
        existing.email_verified = auth_context.email_verified
        db.commit()
        db.refresh(existing)
        return existing

    # Existing by email -> bind subject
    if auth_context.email:
        by_email = get_user_by_email(db, auth_context.email)
        if by_email and not by_email.auth0_sub:
            by_email.auth0_sub = auth_context.sub
            by_email.email_verified = auth_context.email_verified
            if auth_context.name:
                by_email.name = auth_context.name
            db.commit()
            db.refresh(by_email)
            return by_email

    # First login -> provision
    # bcrypt has a 72-byte input limit; Auth0 subject can exceed this length.
    disabled_password_seed = hashlib.sha256(auth_context.sub.encode("utf-8")).hexdigest()[:48]
    provisioned = User(
        name=auth_context.name or (auth_context.email.split("@")[0] if auth_context.email else "User"),
        email=auth_context.email or f"{auth_context.sub}@auth0.local",
        hashed_password=get_password_hash(disabled_password_seed),
        auth0_sub=auth_context.sub,
        email_verified=auth_context.email_verified,
        onboarding_completed=False,
        is_active=True,
    )
    db.add(provisioned)
    db.commit()
    db.refresh(provisioned)
    return provisioned

def authenticate_user(db: Session, email: str, password: str):
    """Authenticate a user."""
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

@router.post("/register", response_model=UserSchema)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    if not settings.enable_legacy_password_auth:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Password registration is deprecated. Use Auth0 sign-up.",
        )
    # Check if user already exists
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        name=user.name,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login a user and return access token."""
    if not settings.enable_legacy_password_auth:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Password login is deprecated. Use Auth0 login.",
        )
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

def _get_auth_context(credentials: HTTPAuthorizationCredentials) -> AuthContext:
    token = credentials.credentials
    if settings.auth_provider.lower() == "auth0":
        try:
            return verify_auth0_token(token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unsupported auth provider configuration.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Get current user from Auth0 access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise credentials_exception

    auth_context = _get_auth_context(credentials)
    user = _provision_or_bind_user(db, auth_context)
    if user is None:
        raise credentials_exception
    return user


def get_current_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    """Expose validated auth context for sensitive-route checks."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return _get_auth_context(credentials)

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.get("/session", response_model=UserSchema)
def read_user_session(current_user: User = Depends(get_current_user)):
    """Session bootstrap endpoint for Auth0-backed frontend."""
    return current_user


@router.post("/mfa/verify")
def verify_mfa_for_sensitive_action(
    auth_context: AuthContext = Depends(get_current_auth_context),
):
    """Probe endpoint to verify token has recent MFA claims."""
    try:
        enforce_recent_mfa(auth_context)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True, "mfa_verified_at": auth_context.mfa_verified_at}

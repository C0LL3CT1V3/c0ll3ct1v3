from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt import PyJWKClient
from passlib.context import CryptContext
from ..config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_mfa_markers = {"mfa", "otp", "webauthn", "totp", "sms", "push"}
_jwk_client: Optional[PyJWKClient] = None


@dataclass
class AuthContext:
    sub: str
    email: Optional[str]
    name: Optional[str]
    email_verified: bool
    claims: dict
    mfa_verified_at: Optional[int]


def _auth0_issuer() -> str:
    if settings.auth0_issuer:
        return settings.auth0_issuer.rstrip("/") + "/"
    if settings.auth0_domain:
        return f"https://{settings.auth0_domain.rstrip('/')}/"
    return ""


def _auth0_jwks_url() -> str:
    return f"{_auth0_issuer().rstrip('/')}/.well-known/jwks.json"


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(_auth0_jwks_url())
    return _jwk_client


def _claims_mfa_verified_at(claims: dict) -> Optional[int]:
    amr = claims.get("amr", [])
    if isinstance(amr, str):
        amr_values = {amr.lower()}
    elif isinstance(amr, list):
        amr_values = {str(item).lower() for item in amr}
    else:
        amr_values = set()

    acr = str(claims.get("acr", "")).lower()
    has_mfa = bool(amr_values.intersection(_mfa_markers) or "mfa" in acr)
    if not has_mfa:
        return None

    auth_time = claims.get("auth_time", claims.get("iat"))
    if auth_time is None:
        return None
    try:
        return int(auth_time)
    except (TypeError, ValueError):
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)  # legacy-only
    return encoded_jwt

def verify_auth0_token(token: str) -> AuthContext:
    """Verify Auth0 access token and return normalized auth context."""
    issuer = _auth0_issuer()
    if not settings.auth0_domain or not settings.auth0_audience or not issuer:
        raise ValueError("Auth0 configuration is incomplete.")

    signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
    algorithms = [alg.strip() for alg in settings.auth0_algorithms.split(",") if alg.strip()]
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=algorithms,
        audience=settings.auth0_audience,
        issuer=issuer,
    )

    sub = str(claims.get("sub", "")).strip()
    if not sub:
        raise ValueError("Token missing subject claim.")

    return AuthContext(
        sub=sub,
        email=claims.get("email"),
        name=claims.get("name"),
        email_verified=bool(claims.get("email_verified", False)),
        claims=claims,
        mfa_verified_at=_claims_mfa_verified_at(claims),
    )


def enforce_recent_mfa(auth_context: AuthContext) -> None:
    """Ensure claims indicate a recent MFA verification."""
    if not settings.mfa_required:
        return
    if auth_context.mfa_verified_at is None:
        raise PermissionError("mfa_required")

    now = int(datetime.now(timezone.utc).timestamp())
    age = now - auth_context.mfa_verified_at
    if age > settings.mfa_max_age_seconds:
        raise PermissionError("mfa_reauthentication_required")

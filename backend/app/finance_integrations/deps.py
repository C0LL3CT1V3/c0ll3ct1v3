
"""Resolve finance API caller identity (Auth0 JWT or local demo header)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings
from ..utils.security import verify_auth0_token
from .finance_auth import FinanceAuthContext

bearer_scheme = HTTPBearer(auto_error=False)


def require_finance_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> FinanceAuthContext:
    if settings.finance_demo_auth:
        if not x_user_id:
            raise HTTPException(status_code=401, detail="Missing X-User-Id (finance demo auth).")
        return FinanceAuthContext(user_id=x_user_id.strip(), mfa_verified_at=None)

    if settings.auth_provider.lower() == "auth0":
        if not credentials or not credentials.credentials:
            raise HTTPException(status_code=401, detail="Missing bearer token.")
        try:
            ctx = verify_auth0_token(credentials.credentials)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid bearer token.") from exc
        return FinanceAuthContext(user_id=ctx.sub, mfa_verified_at=ctx.mfa_verified_at)

    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing user identity header.")
    return FinanceAuthContext(user_id=x_user_id.strip(), mfa_verified_at=None)

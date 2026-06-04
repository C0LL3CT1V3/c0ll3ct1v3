"""Auth for /manager/* — Auth0 user sessions or automation agent key + tenant header."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.artist import Artist
from .auth import _get_auth_context, _provision_or_bind_user, bearer_scheme
from ..services.artist_service import get_artist_by_slug, get_or_create_artist


def get_manager_artist(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Artist:
    """Resolve artist from Auth0 bearer (portal) or agent key + X-Tenant-Slug (automation)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise credentials_exception

    agent_key = (settings.c0ll3ct1v3_agent_key or "").strip()
    token = credentials.credentials
    if agent_key and token == agent_key:
        tenant_slug = (request.headers.get("X-Tenant-Slug") or "").strip().lower()
        if not tenant_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-Slug header required for agent authentication.",
            )
        artist = get_artist_by_slug(db, tenant_slug)
        if not artist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artist tenant '{tenant_slug}' not found.",
            )
        return artist

    try:
        auth_context = _get_auth_context(credentials)
    except HTTPException as exc:
        raise credentials_exception from exc

    user = _provision_or_bind_user(db, auth_context)
    if user is None:
        raise credentials_exception
    return get_or_create_artist(db, user)

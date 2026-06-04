"""Signed OAuth state and token helpers for cloud import."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..models.cloud_connection import CloudConnection

STATE_TTL_SECONDS = 600
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/drive.readonly"

DROPBOX_AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
DROPBOX_SCOPES = "account_info.read files.metadata.read files.content.read"


def _state_secret() -> str:
    secret = (settings.cloud_oauth_state_secret or settings.secret_key or "cloud-oauth-dev").strip()
    if secret == "deprecated-legacy-secret-not-used-in-auth0-mode":
        return "cloud-oauth-dev-only-change-in-production"
    return secret


def sign_oauth_state(artist_id: int, provider: str) -> str:
    payload = {
        "artist_id": artist_id,
        "provider": provider,
        "exp": int(time.time()) + STATE_TTL_SECONDS,
        "n": hashlib.sha256(f"{artist_id}:{provider}:{time.time()}".encode()).hexdigest()[:16],
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_state_secret().encode(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + b"." + sig).decode().rstrip("=")


def verify_oauth_state(state: str) -> tuple[int, str]:
    try:
        padded = state + "=" * (-len(state) % 4)
        blob = base64.urlsafe_b64decode(padded.encode())
        raw, sig = blob.rsplit(b".", 1)
        expected = hmac.new(_state_secret().encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(raw.decode())
        if payload.get("exp", 0) < time.time():
            raise ValueError("expired")
        return int(payload["artist_id"]), str(payload["provider"])
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state.") from exc


def _backend_callback_url(provider: str) -> str:
    base = settings.cloud_oauth_backend_base_url.rstrip("/")
    return f"{base}/media/cloud/{provider}/callback"


def google_oauth_configured() -> bool:
    return bool(settings.google_oauth_client_id and settings.google_oauth_client_secret)


def dropbox_oauth_configured() -> bool:
    return bool(settings.dropbox_oauth_app_key and settings.dropbox_oauth_app_secret)


def build_google_authorize_url(artist_id: int) -> str:
    if not google_oauth_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured on the server.")
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": _backend_callback_url("google"),
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": sign_oauth_state(artist_id, "google"),
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def build_dropbox_authorize_url(artist_id: int) -> str:
    if not dropbox_oauth_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dropbox OAuth is not configured on the server.")
    params = {
        "client_id": settings.dropbox_oauth_app_key,
        "redirect_uri": _backend_callback_url("dropbox"),
        "response_type": "code",
        "token_access_type": "offline",
        "state": sign_oauth_state(artist_id, "dropbox"),
    }
    return f"{DROPBOX_AUTH_URL}?{urlencode(params)}"


def _upsert_connection(
    db: Session,
    *,
    artist_id: int,
    provider: str,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
    account_label: str | None,
) -> CloudConnection:
    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in) - 60)

    row = (
        db.query(CloudConnection)
        .filter(CloudConnection.artist_id == artist_id, CloudConnection.provider == provider)
        .first()
    )
    if row:
        row.access_token = access_token
        if refresh_token:
            row.refresh_token = refresh_token
        row.expires_at = expires_at
        row.account_label = account_label or row.account_label
    else:
        row = CloudConnection(
            artist_id=artist_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            account_label=account_label,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


async def exchange_google_code(db: Session, artist_id: int, code: str) -> CloudConnection:
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": _backend_callback_url("google"),
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code >= 400:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Google token exchange failed.")
        token_data = token_res.json()

        email = None
        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        if user_res.status_code < 400:
            email = user_res.json().get("email")

    return _upsert_connection(
        db,
        artist_id=artist_id,
        provider="google",
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in"),
        account_label=email,
    )


async def exchange_dropbox_code(db: Session, artist_id: int, code: str) -> CloudConnection:
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_res = await client.post(
            DROPBOX_TOKEN_URL,
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.dropbox_oauth_app_key,
                "client_secret": settings.dropbox_oauth_app_secret,
                "redirect_uri": _backend_callback_url("dropbox"),
            },
        )
        if token_res.status_code >= 400:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Dropbox token exchange failed.")
        token_data = token_res.json()

        account_label = None
        acct_res = await client.post(
            "https://api.dropboxapi.com/2/users/get_current_account",
            headers={
                "Authorization": f"Bearer {token_data['access_token']}",
            },
        )
        if acct_res.status_code < 400:
            body = acct_res.json()
            account_label = body.get("email") or body.get("name", {}).get("display_name")

    return _upsert_connection(
        db,
        artist_id=artist_id,
        provider="dropbox",
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in"),
        account_label=account_label,
    )


async def ensure_fresh_token(db: Session, conn: CloudConnection) -> str:
    if conn.expires_at and conn.expires_at > datetime.now(timezone.utc):
        return conn.access_token

    if not conn.refresh_token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=f"Reconnect your {conn.provider} account.",
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        if conn.provider == "google":
            res = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_oauth_client_id,
                    "client_secret": settings.google_oauth_client_secret,
                    "refresh_token": conn.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        elif conn.provider == "dropbox":
            res = await client.post(
                DROPBOX_TOKEN_URL,
                data={
                    "refresh_token": conn.refresh_token,
                    "grant_type": "refresh_token",
                    "client_id": settings.dropbox_oauth_app_key,
                    "client_secret": settings.dropbox_oauth_app_secret,
                },
            )
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown cloud provider.")

    if res.status_code >= 400:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=f"Reconnect your {conn.provider} account.",
        )
    data = res.json()
    conn.access_token = data["access_token"]
    if data.get("refresh_token"):
        conn.refresh_token = data["refresh_token"]
    if data.get("expires_in"):
        conn.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]) - 60)
    db.commit()
    db.refresh(conn)
    return conn.access_token


def connection_status(db: Session, artist_id: int) -> dict[str, Any]:
    rows = db.query(CloudConnection).filter(CloudConnection.artist_id == artist_id).all()
    by_provider = {r.provider: r for r in rows}
    return {
        "google": {
            "configured": google_oauth_configured(),
            "connected": "google" in by_provider,
            "account_label": by_provider.get("google").account_label if "google" in by_provider else None,
        },
        "dropbox": {
            "configured": dropbox_oauth_configured(),
            "connected": "dropbox" in by_provider,
            "account_label": by_provider.get("dropbox").account_label if "dropbox" in by_provider else None,
        },
    }


def frontend_redirect(provider: str, *, ok: bool = True, error: str | None = None) -> str:
    base = settings.cloud_oauth_frontend_redirect_url.rstrip("/")
    params = {"cloud": provider, "connected": "1" if ok else "0"}
    if error:
        params["cloud_error"] = error[:200]
    return f"{base}?{urlencode(params)}"

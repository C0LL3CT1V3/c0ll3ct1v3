"""HMAC tokens for unauthenticated EPK sim render (Playwright + iframe)."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

from fastapi import HTTPException, status

from ..config import settings

_TOKEN_TTL_SECONDS = 900


def _secret() -> bytes:
    raw = (settings.cloud_oauth_state_secret or settings.secret_key or "dev-epk-sim").encode("utf-8")
    return raw


def mint_sim_token(*, artist_id: int, draft_hash: str) -> str:
    exp = int(time.time()) + _TOKEN_TTL_SECONDS
    payload = f"{artist_id}:{draft_hash}:{exp}"
    sig = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{artist_id}.{draft_hash}.{exp}.{sig}"


def verify_sim_token(token: str) -> dict[str, Any]:
    parts = (token or "").split(".")
    if len(parts) != 4:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid sim token.")
    artist_id_s, draft_hash, exp_s, sig = parts
    try:
        artist_id = int(artist_id_s)
        exp = int(exp_s)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid sim token.") from exc
    if exp < int(time.time()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Sim token expired.")
    payload = f"{artist_id}:{draft_hash}:{exp}"
    expected = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid sim token.")
    return {"artist_id": artist_id, "draft_hash": draft_hash}

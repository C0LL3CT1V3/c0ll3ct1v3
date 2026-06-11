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


def mint_sim_token(*, artist_id: int, draft_hash: str, iteration_id: str | None = None) -> str:
    exp = int(time.time()) + _TOKEN_TTL_SECONDS
    if iteration_id:
        payload = f"{artist_id}:{draft_hash}:{iteration_id}:{exp}"
        sig = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{artist_id}.{draft_hash}.{iteration_id}.{exp}.{sig}"
    payload = f"{artist_id}:{draft_hash}:{exp}"
    sig = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{artist_id}.{draft_hash}.{exp}.{sig}"


def verify_sim_token(token: str) -> dict[str, Any]:
    parts = (token or "").split(".")
    if len(parts) not in (4, 5):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid sim token.")
    iteration_id: str | None = None
    if len(parts) == 5:
        artist_id_s, draft_hash, iteration_id, exp_s, sig = parts
    else:
        artist_id_s, draft_hash, exp_s, sig = parts
    try:
        artist_id = int(artist_id_s)
        exp = int(exp_s)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid sim token.") from exc
    if exp < int(time.time()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Sim token expired.")
    if iteration_id:
        payload = f"{artist_id}:{draft_hash}:{iteration_id}:{exp}"
    else:
        payload = f"{artist_id}:{draft_hash}:{exp}"
    expected = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid sim token.")
    out: dict[str, Any] = {"artist_id": artist_id, "draft_hash": draft_hash}
    if iteration_id:
        out["iteration_id"] = iteration_id
    return out


def sim_render_url(*, artist_id: int, draft_hash: str, iteration_id: str | None = None) -> str:
    token = mint_sim_token(artist_id=artist_id, draft_hash=draft_hash, iteration_id=iteration_id)
    return f"{settings.epk_sim_base_url.rstrip('/')}/manager/epk/sim/render?token={token}"

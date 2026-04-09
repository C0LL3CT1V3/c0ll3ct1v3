
"""MFA step-up and finance-scoped auth context."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException

from ..config import settings
from .audit import audit_event

_CHALLENGE_TTL_SECONDS = 300
_challenge_store: dict[str, dict[str, int | str]] = {}


@dataclass
class FinanceAuthContext:
    user_id: str
    mfa_verified_at: int | None


def _cleanup_expired_challenges() -> None:
    now = int(time.time())
    stale = [cid for cid, payload in _challenge_store.items() if int(payload["expires_at"]) <= now]
    for cid in stale:
        _challenge_store.pop(cid, None)


def parse_allowed_methods() -> list[str]:
    return [m.strip() for m in settings.finance_mfa_methods_allowed.split(",") if m.strip()]


def create_step_up_challenge(user_id: str, reason: str) -> str:
    _cleanup_expired_challenges()
    challenge_id = secrets.token_urlsafe(24)
    now = int(time.time())
    _challenge_store[challenge_id] = {
        "user_id": user_id,
        "reason": reason,
        "created_at": now,
        "expires_at": now + _CHALLENGE_TTL_SECONDS,
    }
    audit_event("mfa_challenge_created", user_id, {"challenge_id": challenge_id, "reason": reason})
    return challenge_id


def verify_step_up_challenge(user_id: str, challenge_id: str, otp_code: str) -> tuple[int, int]:
    _cleanup_expired_challenges()
    payload = _challenge_store.get(challenge_id)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired challenge.")
    if payload["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Challenge does not belong to this user.")
    if otp_code != settings.finance_mfa_demo_otp:
        audit_event("mfa_challenge_failed", user_id, {"challenge_id": challenge_id})
        raise HTTPException(status_code=401, detail="MFA verification failed.")

    now = int(time.time())
    expires_at = now + settings.mfa_max_age_seconds
    _challenge_store.pop(challenge_id, None)
    audit_event("mfa_challenge_verified", user_id, {"challenge_id": challenge_id})
    return now, expires_at


def require_recent_mfa(
    auth_context: FinanceAuthContext,
    x_mfa_verified_at: str | None = Header(default=None, alias="X-Mfa-Verified-At"),
) -> None:
    if not settings.finance_mfa_consumer_enforced:
        return
    if not settings.finance_mfa_step_up_for_plaid_link:
        return
    verified_at = auth_context.mfa_verified_at
    if verified_at is None and x_mfa_verified_at:
        try:
            verified_at = int(x_mfa_verified_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid MFA timestamp header.") from exc

    if verified_at is None:
        audit_event("mfa_missing_for_sensitive_action", auth_context.user_id, {"action": "plaid_link_token_create"})
        raise HTTPException(status_code=403, detail="mfa_required")

    now = int(time.time())
    age_seconds = now - verified_at
    if age_seconds > settings.mfa_max_age_seconds:
        audit_event(
            "mfa_stale_for_sensitive_action",
            auth_context.user_id,
            {"age_seconds": str(age_seconds)},
        )
        raise HTTPException(status_code=403, detail="mfa_reauthentication_required")

"""Webhook verification and replay-safe event handling helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from ..config import settings

_event_store: dict[str, int] = {}
_EVENT_STORE_TTL_SECONDS = 7 * 24 * 60 * 60


@dataclass
class EventRecord:
    source: str
    event_id: str
    event_type: str
    payload_redacted: dict[str, Any]
    received_at: int
    replayed: bool


def _cleanup_expired_events(now: int) -> None:
    stale_keys = [key for key, expires_at in _event_store.items() if expires_at <= now]
    for key in stale_keys:
        _event_store.pop(key, None)


def dedupe_event(source: str, event_id: str) -> bool:
    """
    Return True if this event id was already seen.

    In production replace this with durable DB-backed dedupe using webhook_events.
    """
    now = int(time.time())
    _cleanup_expired_events(now)
    dedupe_key = f"{source}:{event_id}"
    if dedupe_key in _event_store:
        return True
    _event_store[dedupe_key] = now + _EVENT_STORE_TTL_SECONDS
    return False


def _compute_square_signature(signature_key: str, notification_url: str, raw_body: str) -> str:
    payload = f"{notification_url}{raw_body}".encode("utf-8")
    digest = hmac.new(signature_key.encode("utf-8"), payload, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def verify_square_signature(raw_body: str, header_signature: str) -> bool:
    signature_key = settings.square_webhook_signature_key.strip()
    notification_url = settings.square_webhook_url.strip()
    if not signature_key or not notification_url:
        return False
    expected = _compute_square_signature(signature_key, notification_url, raw_body)
    return hmac.compare_digest(expected, header_signature.strip())


def redact_payload(payload: Any) -> dict[str, Any]:
    """
    Recursive redaction for webhook payloads.

    Keep this local to avoid importing from scripts package at runtime.
    """

    def _is_sensitive_key(key: str) -> bool:
        lowered = key.lower()
        return lowered in {
            "token",
            "access_token",
            "refresh_token",
            "secret",
            "authorization",
            "account_number",
            "routing_number",
            "client_secret",
            "signature",
            "webhook_signature",
        } or "token" in lowered or "secret" in lowered

    def _redact(value: Any) -> Any:
        if isinstance(value, dict):
            output: dict[str, Any] = {}
            for key, inner_value in value.items():
                if _is_sensitive_key(str(key)):
                    output[key] = "[REDACTED]"
                else:
                    output[key] = _redact(inner_value)
            return output
        if isinstance(value, list):
            return [_redact(item) for item in value]
        return value

    redacted = _redact(payload)
    if isinstance(redacted, dict):
        return redacted
    return {"value": redacted}


def parse_json_body(raw_body: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_body.decode("utf-8"))
    except Exception:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {"value": parsed}

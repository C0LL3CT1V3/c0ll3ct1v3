"""Deploy busy-gate: in-flight vault uploads + recent authenticated API traffic.

Used by ``scripts/prod-up.sh`` via ``python -m app.services.deploy_gate`` inside
the running backend container. Fail closed if Redis is configured but unreachable.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..models.media import MediaUpload

REDIS_KEY = "c0ll3ct1v3:deploy:last_auth_at"
INFLIGHT_STATUSES = ("uploading", "initiating")
SKIP_AUTH_PATHS = frozenset({"/health", "/", "/docs", "/openapi.json", "/redoc"})

_redis = None
_redis_failed = False


def _idle_seconds() -> int:
    return int(os.environ.get("DEPLOY_IDLE_SECONDS", "180"))


def _upload_max_age_hours() -> int:
    return int(os.environ.get("DEPLOY_UPLOAD_MAX_AGE_HOURS", "2"))


def _redis_client():
    global _redis, _redis_failed
    if _redis_failed:
        return None
    if not settings.redis_url:
        return None
    if _redis is None:
        try:
            from redis import Redis

            _redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        except Exception:
            _redis_failed = True
            return None
    return _redis


def record_auth_activity() -> None:
    client = _redis_client()
    if client is None:
        return
    try:
        client.set(REDIS_KEY, str(int(time.time())))
    except Exception:
        pass


def maybe_record_request_auth(request: Any) -> None:
    path = getattr(getattr(request, "url", None), "path", "") or ""
    if path in SKIP_AUTH_PATHS:
        return
    auth = ""
    headers = getattr(request, "headers", None)
    if headers is not None:
        auth = headers.get("authorization") or headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        record_auth_activity()


def last_auth_timestamp() -> tuple[int | None, str]:
    """Return (unix_ts or None, status). status is ok | unused | unreachable."""
    if not settings.redis_url:
        return None, "unused"
    client = _redis_client()
    if client is None:
        return None, "unreachable"
    try:
        raw = client.get(REDIS_KEY)
    except Exception:
        return None, "unreachable"
    if not raw:
        return None, "ok"
    try:
        return int(raw), "ok"
    except (TypeError, ValueError):
        return None, "ok"


def count_inflight_uploads(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=_upload_max_age_hours())
    q = db.query(MediaUpload).filter(MediaUpload.status.in_(INFLIGHT_STATUSES))
    # created_at can be naive on SQLite; compare as-aware when possible.
    rows = q.all()
    n = 0
    for row in rows:
        created = row.created_at
        if created is None:
            n += 1
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created >= cutoff:
            n += 1
    return n


def evaluate(db: Session) -> dict:
    uploads = count_inflight_uploads(db)
    ts, redis_status = last_auth_timestamp()
    idle = _idle_seconds()
    reasons: list[str] = []

    if redis_status == "unreachable":
        reasons.append("redis_unreachable")
        auth_idle = None
        auth_ok = False
    elif ts is None:
        auth_idle = None
        auth_ok = True
    else:
        auth_idle = max(0, int(time.time()) - ts)
        auth_ok = auth_idle >= idle
        if not auth_ok:
            reasons.append("recent_auth")

    if uploads > 0:
        reasons.append("inflight_uploads")

    ready = auth_ok and uploads == 0
    return {
        "ready": ready,
        "inflight_uploads": uploads,
        "auth_idle_seconds": auth_idle,
        "idle_threshold_seconds": idle,
        "redis": redis_status,
        "reasons": reasons,
    }


def main() -> int:
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        result = evaluate(db)
    finally:
        db.close()
    print(json.dumps(result))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())

"""Per-tenant rate limiting for manager chat."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

from ..config import settings

_buckets: dict[int, deque[float]] = defaultdict(deque)


def enforce_manager_chat_rate_limit(artist_id: int) -> None:
    limit = max(1, int(settings.manager_chat_rate_limit_per_min))
    now = time.time()
    window = 60.0
    bucket = _buckets[artist_id]
    while bucket and bucket[0] < now - window:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Manager chat rate limit exceeded ({limit} messages per minute). Try again shortly.",
        )
    bucket.append(now)

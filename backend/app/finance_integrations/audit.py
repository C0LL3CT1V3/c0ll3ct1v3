"""Minimal audit sink for security-relevant events."""

from __future__ import annotations

import json
import time


def audit_event(action: str, actor_id: str, metadata: dict[str, str] | None = None) -> None:
    record = {
        "timestamp": int(time.time()),
        "action": action,
        "actor_id": actor_id,
        "metadata": metadata or {},
    }
    # Replace with DB insert into audit_events in production.
    print(f"[AUDIT] {json.dumps(record, sort_keys=True)}")


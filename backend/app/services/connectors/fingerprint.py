"""Optional ACRCloud/AudD fingerprint — skipped unless an API key is configured."""

from __future__ import annotations

import logging
from typing import Any

from ...config import settings

log = logging.getLogger(__name__)


def fingerprint_drafts(*, title: str, asset_id: str) -> list[dict[str, Any]]:
    if not (settings.acrcloud_access_key or settings.audd_api_token):
        return []
    log.info("Fingerprint connector is configured but v1 does not call the vendor yet.")
    return [
        {
            "claim_type": "canonical_version",
            "value": {"asset_id": asset_id, "is_canonical": True, "title": title},
            "source_ref": {"note": "fingerprint_stub_pending_vendor_call"},
        }
    ]

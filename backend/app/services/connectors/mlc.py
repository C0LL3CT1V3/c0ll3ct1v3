"""MLC Public Work Search — drafts only. Never activates claims."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ...config import settings

log = logging.getLogger(__name__)


def _work_to_drafts(work: dict[str, Any], query: str) -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = []
    iswc = work.get("iswc") or work.get("ISWC") or work.get("iswcCode")
    if iswc:
        drafts.append(
            {
                "claim_type": "identifiers",
                "value": {"iswc": str(iswc)},
                "source_ref": {"mlc_work_id": work.get("id") or work.get("workId"), "query": query},
            }
        )
    writers = work.get("writers") or work.get("songwriters") or work.get("interestedParties") or []
    if isinstance(writers, list):
        for party in writers:
            if not isinstance(party, dict):
                continue
            name = party.get("name") or party.get("fullName") or party.get("writerName")
            role = (party.get("role") or party.get("partyRole") or "writer").lower()
            if name:
                drafts.append(
                    {
                        "claim_type": "credit",
                        "value": {
                            "role": "writer" if "perform" not in role else role,
                            "name": str(name),
                            "ipi_or_id": party.get("ipi") or party.get("ipiNameNumber"),
                        },
                        "source_ref": {"query": query},
                    }
                )
            share = party.get("share") or party.get("collectionShare") or party.get("percentage")
            if name and share is not None:
                try:
                    pct = float(str(share).replace("%", "").strip())
                except ValueError:
                    continue
                drafts.append(
                    {
                        "claim_type": "split",
                        "value": {
                            "payee_name_or_id": str(name),
                            "percentage": pct,
                            "right_type": "composition",
                        },
                        "source_ref": {"query": query, "disclaimer": "mlc_member_supplied"},
                    }
                )
    return drafts


def search_mlc_drafts(*, title: str, artist_name: str) -> list[dict[str, Any]]:
    """Return draft payloads. Empty if MLC is unconfigured or the lookup fails."""
    base = (settings.mlc_api_base_url or "").rstrip("/")
    token = (settings.mlc_api_token or "").strip()
    if not base or not token:
        return []
    query = f"{title} {artist_name}".strip()
    url = f"{base}/search"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(url, params={"title": title, "writer": artist_name}, headers=headers)
            if response.status_code >= 400:
                response = client.post(url, json={"title": title, "writer": artist_name}, headers=headers)
            response.raise_for_status()
            body = response.json()
    except Exception as exc:  # noqa: BLE001
        log.info("MLC lookup skipped: %s", exc)
        return []

    works = []
    if isinstance(body, list):
        works = body
    elif isinstance(body, dict):
        works = body.get("works") or body.get("results") or body.get("data") or []
        if isinstance(works, dict):
            works = [works]
    drafts: list[dict[str, Any]] = []
    for work in works[:5]:
        if isinstance(work, dict):
            drafts.extend(_work_to_drafts(work, query))
    return drafts

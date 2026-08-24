"""MusicBrainz recording lookup — identifier / release drafts only."""

from __future__ import annotations

import logging
from typing import Any
import httpx

log = logging.getLogger(__name__)

_UA = "c0ll3ct1v3/1.0 ( https://c0ll3ct1v3.xyz )"


def search_musicbrainz_drafts(*, title: str, artist_name: str) -> list[dict[str, Any]]:
    if not title:
        return []
    q_parts = [f'recording:"{title.replace(chr(34), "")}"']
    if artist_name:
        q_parts.append(f'artist:"{artist_name.replace(chr(34), "")}"')
    query = " AND ".join(q_parts)
    url = "https://musicbrainz.org/ws/2/recording"
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": _UA}) as client:
            response = client.get(url, params={"query": query, "fmt": "json", "limit": 3})
            response.raise_for_status()
            body = response.json()
    except Exception as exc:  # noqa: BLE001
        log.info("MusicBrainz lookup skipped: %s", exc)
        return []

    drafts: list[dict[str, Any]] = []
    for rec in body.get("recordings") or []:
        if not isinstance(rec, dict):
            continue
        isrcs = rec.get("isrcs") or []
        isrc = isrcs[0] if isrcs else None
        if isrc:
            drafts.append(
                {
                    "claim_type": "identifiers",
                    "value": {"isrc": str(isrc)},
                    "source_ref": {"mbid": rec.get("id"), "query": query},
                }
            )
        first_release = None
        for rel in rec.get("releases") or []:
            if isinstance(rel, dict) and rel.get("date"):
                first_release = rel.get("date")
                break
        drafts.append(
            {
                "claim_type": "canonical_version",
                "value": {
                    "asset_id": None,
                    "release_date": first_release,
                    "is_canonical": True,
                    "title": rec.get("title"),
                },
                "source_ref": {"mbid": rec.get("id"), "query": query},
            }
        )
        break
    return drafts

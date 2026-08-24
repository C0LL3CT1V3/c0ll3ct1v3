"""Orchestrate draft ingestion from MLC, MusicBrainz, CSV, fingerprint, consent flag."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models.artist import Artist
from ..models.attestation import AttestationClaim
from ..models.media import MediaAsset
from .attestation_service import assert_asset_owned, insert_draft, serialize_claim
from .connectors.distributor_csv import parse_distributor_csv
from .connectors.fingerprint import fingerprint_drafts
from .connectors.mlc import search_mlc_drafts
from .connectors.musicbrainz import search_musicbrainz_drafts

DEFAULT_SOURCES = ("mlc", "musicbrainz", "fingerprint", "consent_flag")


def _with_asset(value: dict[str, Any], asset_id: str, claim_type: str) -> dict[str, Any]:
    if claim_type == "canonical_version" and not value.get("asset_id"):
        return {**value, "asset_id": asset_id}
    return value


def _seed_consent_drafts(db: Session, artist: Artist, asset_id: str) -> list[AttestationClaim]:
    created: list[AttestationClaim] = []
    created.append(
        insert_draft(
            db,
            artist,
            claim_type="consent_cite",
            value={"allowed": True},
            source="consent_flag",
            subject_asset_id=asset_id,
            source_ref={"policy": "default_cite_allowed"},
        )
    )
    created.append(
        insert_draft(
            db,
            artist,
            claim_type="consent_train",
            value={"allowed": bool(artist.allow_training_contribution)},
            source="consent_flag",
            subject_asset_id=asset_id,
            source_ref={"from": "allow_training_contribution"},
        )
    )
    created.append(
        insert_draft(
            db,
            artist,
            claim_type="consent_sync",
            value={"allowed": False},
            source="consent_flag",
            subject_asset_id=asset_id,
            source_ref={"policy": "default_sync_off"},
        )
    )
    return created


def ingest_asset(
    db: Session,
    artist: Artist,
    asset_id: str,
    *,
    sources: list[str] | None = None,
    csv_bytes: bytes | None = None,
) -> list[AttestationClaim]:
    asset = assert_asset_owned(db, artist, asset_id)
    assert isinstance(asset, MediaAsset)
    wanted = set(sources or DEFAULT_SOURCES)
    title = (asset.title or "").strip() or "untitled"
    artist_name = artist.display_name or artist.tenant_slug
    created: list[AttestationClaim] = []

    payload_groups: list[tuple[str, list[dict[str, Any]]]] = []
    if "mlc" in wanted:
        payload_groups.append(("mlc", search_mlc_drafts(title=title, artist_name=artist_name)))
    if "musicbrainz" in wanted:
        payload_groups.append(
            ("musicbrainz", search_musicbrainz_drafts(title=title, artist_name=artist_name))
        )
    if "fingerprint" in wanted:
        payload_groups.append(
            ("fingerprint", fingerprint_drafts(title=title, asset_id=asset_id))
        )
    if csv_bytes is not None or "distributor_export" in wanted:
        rows = parse_distributor_csv(csv_bytes) if csv_bytes else []
        payload_groups.append(("distributor_export", rows))

    for source, payloads in payload_groups:
        for item in payloads:
            created.append(
                insert_draft(
                    db,
                    artist,
                    claim_type=item["claim_type"],
                    value=_with_asset(item.get("value") or {}, asset_id, item["claim_type"]),
                    source=source,
                    subject_asset_id=asset_id,
                    source_ref=item.get("source_ref") or {},
                )
            )

    if "consent_flag" in wanted:
        created.extend(_seed_consent_drafts(db, artist, asset_id))

    db.commit()
    for row in created:
        db.refresh(row)
    return created


def serialize_ingest(rows: list[AttestationClaim]) -> dict[str, Any]:
    return {"created": [serialize_claim(row) for row in rows], "count": len(rows)}

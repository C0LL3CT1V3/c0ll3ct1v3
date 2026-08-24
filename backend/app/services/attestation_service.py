"""Create, confirm, and read attestation claims."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.artist import Artist
from ..models.attestation import (
    CLAIM_SOURCES,
    CLAIM_TYPES,
    PUBLIC_HISTORY_STATUSES,
    AttestationClaim,
)
from ..models.media import MediaAsset
from ..models.user import User
from .artist_service import storage_namespace_for_artist
from .attestation_crypto import sign_payload, verify_signature
from .epk_media import collect_epk_asset_ids
from .epk_public import resolve_epk_public
from .epk_public_config import coerce_epk_public, get_epk_public_raw


def _now() -> datetime:
    return datetime.now(timezone.utc)


def assert_asset_owned(db: Session, artist: Artist, asset_id: str | None) -> MediaAsset | None:
    if asset_id is None:
        return None
    ns = storage_namespace_for_artist(artist)
    asset = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.id == asset_id,
            MediaAsset.tenant_slug == ns,
            MediaAsset.is_deleted.is_(False),
        )
        .first()
    )
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return asset


def _user_id_for_artist(db: Session, artist: Artist) -> int | None:
    if not artist.auth0_sub or artist.auth0_sub.startswith("seed:"):
        return None
    row = db.query(User).filter(User.auth0_sub == artist.auth0_sub).first()
    return int(row.id) if row else None


def _attested_stamp(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0).isoformat() + "Z"


def signing_payload(claim: AttestationClaim) -> dict[str, Any]:
    return {
        "artist_id": claim.artist_id,
        "subject_asset_id": claim.subject_asset_id,
        "claim_type": claim.claim_type,
        "value": claim.value or {},
        "attested_by_user_id": claim.attested_by_user_id,
        "attested_by_role": claim.attested_by_role,
        "attested_at": _attested_stamp(claim.attested_at),
        "prior_version_id": claim.prior_version_id,
    }


def serialize_claim(claim: AttestationClaim) -> dict[str, Any]:
    return {
        "id": claim.id,
        "artist_id": claim.artist_id,
        "subject_asset_id": claim.subject_asset_id,
        "claim_type": claim.claim_type,
        "value": claim.value or {},
        "source": claim.source,
        "source_ref": claim.source_ref or {},
        "attested_by_user_id": claim.attested_by_user_id,
        "attested_by_role": claim.attested_by_role,
        "attested_at": claim.attested_at.isoformat() if claim.attested_at else None,
        "stale_after": claim.stale_after.isoformat() if claim.stale_after else None,
        "prior_version_id": claim.prior_version_id,
        "status": claim.status,
        "signature": claim.signature,
        "key_fingerprint": claim.key_fingerprint,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
    }


def insert_draft(
    db: Session,
    artist: Artist,
    *,
    claim_type: str,
    value: dict[str, Any],
    source: str,
    subject_asset_id: str | None = None,
    source_ref: dict[str, Any] | None = None,
) -> AttestationClaim:
    if claim_type not in CLAIM_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Unknown claim_type: {claim_type}")
    if source not in CLAIM_SOURCES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Unknown source: {source}")
    assert_asset_owned(db, artist, subject_asset_id)
    row = AttestationClaim(
        artist_id=artist.id,
        subject_asset_id=subject_asset_id,
        claim_type=claim_type,
        value=value or {},
        source=source,
        source_ref=source_ref or {},
        status="draft",
        signature=None,
        key_fingerprint=None,
        attested_by_role=None,
        attested_at=None,
    )
    db.add(row)
    db.flush()
    return row


def _supersede_active(
    db: Session,
    artist: Artist,
    subject_asset_id: str | None,
    claim_type: str,
) -> str | None:
    q = db.query(AttestationClaim).filter(
        AttestationClaim.artist_id == artist.id,
        AttestationClaim.claim_type == claim_type,
        AttestationClaim.status == "active",
    )
    if subject_asset_id is None:
        q = q.filter(AttestationClaim.subject_asset_id.is_(None))
    else:
        q = q.filter(AttestationClaim.subject_asset_id == subject_asset_id)
    prior = q.order_by(AttestationClaim.created_at.desc()).first()
    if not prior:
        return None
    prior.status = "superseded"
    return prior.id


def confirm_claim(
    db: Session,
    artist: Artist,
    claim_id: str,
    *,
    value: dict[str, Any] | None = None,
    role: str = "artist",
) -> AttestationClaim:
    row = (
        db.query(AttestationClaim)
        .filter(AttestationClaim.id == claim_id, AttestationClaim.artist_id == artist.id)
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    if row.status != "draft":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Only draft claims can be confirmed.")
    if value is not None:
        row.value = value
    prior_id = _supersede_active(db, artist, row.subject_asset_id, row.claim_type)
    row.prior_version_id = prior_id
    row.attested_by_user_id = _user_id_for_artist(db, artist)
    row.attested_by_role = role if role in {"artist", "manager", "agent"} else "artist"
    row.attested_at = _now()
    sig, fingerprint = sign_payload(signing_payload(row))
    row.signature = sig
    row.key_fingerprint = fingerprint
    row.status = "active"
    db.flush()
    return row


def reject_claim(db: Session, artist: Artist, claim_id: str) -> AttestationClaim:
    row = (
        db.query(AttestationClaim)
        .filter(AttestationClaim.id == claim_id, AttestationClaim.artist_id == artist.id)
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    if row.status != "draft":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Only draft claims can be rejected.")
    row.status = "rejected"
    db.flush()
    return row


def dispute_claim(db: Session, artist: Artist, claim_id: str) -> AttestationClaim:
    row = (
        db.query(AttestationClaim)
        .filter(AttestationClaim.id == claim_id, AttestationClaim.artist_id == artist.id)
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    if row.status != "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Only active claims can be disputed.")
    row.status = "disputed"
    db.flush()
    return row


def list_claims_for_artist(
    db: Session,
    artist: Artist,
    *,
    asset_id: str | None = None,
    include_rejected: bool = True,
) -> list[AttestationClaim]:
    q = db.query(AttestationClaim).filter(AttestationClaim.artist_id == artist.id)
    if asset_id:
        q = q.filter(
            (AttestationClaim.subject_asset_id == asset_id) | (AttestationClaim.subject_asset_id.is_(None))
        )
    if not include_rejected:
        q = q.filter(AttestationClaim.status != "rejected")
    return q.order_by(AttestationClaim.created_at.asc()).all()


def _active_overlay(db: Session, artist_id: int, asset_id: str) -> dict[str, AttestationClaim]:
    rows = (
        db.query(AttestationClaim)
        .filter(
            AttestationClaim.artist_id == artist_id,
            AttestationClaim.status == "active",
            (AttestationClaim.subject_asset_id == asset_id) | (AttestationClaim.subject_asset_id.is_(None)),
        )
        .all()
    )
    overlay: dict[str, AttestationClaim] = {}
    for row in rows:
        if row.subject_asset_id is None:
            overlay.setdefault(row.claim_type, row)
    for row in rows:
        if row.subject_asset_id == asset_id:
            overlay[row.claim_type] = row
    return overlay


def published_epk_asset_ids(db: Session, artist: Artist) -> set[str]:
    raw = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    if not raw.get("epk_public_published"):
        return set()
    epk = coerce_epk_public(get_epk_public_raw(artist))
    data = resolve_epk_public(db, artist, epk)
    return collect_epk_asset_ids(data)


def get_public_rights(db: Session, asset_id: str) -> dict[str, Any]:
    asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id, MediaAsset.is_deleted.is_(False)).first()
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    artist = (
        db.query(Artist)
        .filter(
            (Artist.storage_namespace == asset.tenant_slug) | (Artist.tenant_slug == asset.tenant_slug)
        )
        .first()
    )
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artist not found.")
    allowed = published_epk_asset_ids(db, artist)
    if asset_id not in allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not in published EPK.")
    overlay = _active_overlay(db, artist.id, asset_id)
    claims = [serialize_claim(row) for row in overlay.values()]
    claims.sort(key=lambda c: c["claim_type"])
    return {
        "asset_id": asset_id,
        "artist_slug": artist.tenant_slug,
        "claims": claims,
    }


def get_public_history(db: Session, asset_id: str) -> dict[str, Any]:
    bundle = get_public_rights(db, asset_id)
    artist = db.query(Artist).filter(Artist.tenant_slug == bundle["artist_slug"]).first()
    rows = (
        db.query(AttestationClaim)
        .filter(
            AttestationClaim.artist_id == artist.id,
            AttestationClaim.status.in_(PUBLIC_HISTORY_STATUSES),
            (AttestationClaim.subject_asset_id == asset_id) | (AttestationClaim.subject_asset_id.is_(None)),
        )
        .order_by(AttestationClaim.created_at.asc())
        .all()
    )
    return {
        "asset_id": asset_id,
        "artist_slug": artist.tenant_slug,
        "claims": [serialize_claim(row) for row in rows],
    }


def verify_claim(db: Session, claim_id: str) -> dict[str, Any]:
    row = db.query(AttestationClaim).filter(AttestationClaim.id == claim_id).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    if row.status == "draft" or not row.signature:
        return {"claim_id": claim_id, "valid": False, "reason": "unsigned"}
    valid = verify_signature(signing_payload(row), row.signature, row.key_fingerprint or "")
    return {"claim_id": claim_id, "valid": valid}


def consent_menu(db: Session, artist: Artist, asset_id: str) -> dict[str, Any]:
    overlay = _active_overlay(db, artist.id, asset_id)
    menu = []
    listen = overlay.get("consent_cite") or overlay.get("consent_train")
    menu.append(
        {
            "tier": "listen",
            "note": "Human stream remains free. Machine fetch is offered here; no durable master URL.",
            "claim": serialize_claim(listen) if listen else None,
        }
    )
    for tier, key in (("cite", "consent_cite"), ("sync", "consent_sync"), ("train", "consent_train")):
        row = overlay.get(key)
        menu.append(
            {
                "tier": tier,
                "claim": serialize_claim(row) if row else None,
            }
        )
    return {"asset_id": asset_id, "payment_required": True, "menu": menu, "settlement": "stub"}

"""Append-only artist attestation claims (drafts unsigned; actives signed)."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy import JSON as SAJSON
from sqlalchemy.sql import func

from ..database import Base

CLAIM_TYPES = frozenset(
    {
        "credit",
        "split",
        "consent_train",
        "consent_sync",
        "consent_cite",
        "canonical_version",
        "identifiers",
    }
)
CLAIM_STATUSES = frozenset(
    {"draft", "active", "superseded", "disputed", "revoked", "rejected"}
)
ATTESTED_ROLES = frozenset({"artist", "manager", "agent"})
CLAIM_SOURCES = frozenset(
    {
        "manual",
        "mlc",
        "distributor_export",
        "musicbrainz",
        "fingerprint",
        "soundexchange",
        "usco",
        "consent_flag",
    }
)
PUBLIC_HISTORY_STATUSES = frozenset({"active", "superseded", "disputed", "revoked"})


def _uuid() -> str:
    return str(uuid.uuid4())


class AttestationClaim(Base):
    __tablename__ = "attestation_claims"

    id = Column(String(36), primary_key=True, default=_uuid)
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_asset_id = Column(
        String(36),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claim_type = Column(String(64), nullable=False, index=True)
    value = Column(SAJSON, nullable=False, default=dict)
    source = Column(String(64), nullable=False, default="manual")
    source_ref = Column(SAJSON, nullable=False, default=dict)
    attested_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    attested_by_role = Column(String(32), nullable=True)
    attested_at = Column(DateTime(timezone=True), nullable=True)
    stale_after = Column(DateTime(timezone=True), nullable=True)
    prior_version_id = Column(
        String(36),
        ForeignKey("attestation_claims.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(32), nullable=False, default="draft", index=True)
    signature = Column(String(256), nullable=True)
    key_fingerprint = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

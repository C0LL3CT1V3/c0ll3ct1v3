"""Artist profile linked to Auth0 identity and public EPK tenant slug."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.sql import func

from ..database import Base


def default_epk_config() -> dict:
    return {
        "tagline": "",
        "bio": "",
        "booking_email": "",
        "social": {},
        "sections": {"music": True, "photos": True, "bio": True},
    }


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    auth0_sub = Column(String, unique=True, nullable=False, index=True)
    tenant_slug = Column(String, unique=True, nullable=False, index=True)
    # Immutable S3/workbench prefix — never changes when display_name or tenant_slug updates.
    storage_namespace = Column(String(64), nullable=True, index=True)
    display_name = Column(String, nullable=False)
    epk_config = Column(SAJSON, nullable=False, default=default_epk_config)
    epk_draft = Column(SAJSON, nullable=True)
    manager_system_prompt = Column(Text, nullable=True)
    allow_training_contribution = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ArtistSlugAlias(Base):
    """Maps former public subdomains to an artist (redirect / lookup)."""

    __tablename__ = "artist_slug_aliases"

    id = Column(Integer, primary_key=True, index=True)
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

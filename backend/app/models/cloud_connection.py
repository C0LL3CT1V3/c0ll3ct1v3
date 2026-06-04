"""Per-artist OAuth tokens for cloud import (Google Drive, Dropbox)."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from ..database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CloudConnection(Base):
    __tablename__ = "cloud_connections"
    __table_args__ = (UniqueConstraint("artist_id", "provider", name="uq_cloud_connections_artist_provider"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(16), nullable=False, index=True)  # google | dropbox
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    account_label = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

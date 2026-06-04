"""Creative media (DAM) — metadata in Postgres, blobs in object storage.

Workbench:
- One ``MediaAsset`` per upload; masters live under ``workbench/``.
- Optional ``vision_id`` groups assets in the portal UI.
- ``status`` tracks ingest: inbox → processing → ready.
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base

# Workbench ingest lifecycle
WORKBENCH_STATUSES = frozenset({"inbox", "processing", "ready", "archived"})
# Gallery rows use ready; archived applies to soft-deleted workflow
GALLERY_STATUSES = frozenset({"ready", "archived"})
STORAGE_REGIONS = frozenset({"workbench", "gallery"})
GALLERY_STAGE_RELEASED = "released"


def _uuid() -> str:
    return str(uuid.uuid4())


class MediaAsset(Base):
    """Logical asset scoped to a tenant workspace."""

    __tablename__ = "media_assets"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_slug = Column(String(64), nullable=False, index=True)
    title = Column(String(512), nullable=True)
    asset_type = Column(String(32), nullable=False, index=True)  # audio | image | video | document | archive
    status = Column(String(32), nullable=False, default="inbox", index=True)
    visibility = Column(String(32), nullable=False, default="private")  # legacy; prefer gallery_stage
    tags = Column(SAJSON, nullable=False, default=dict)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_by = Column(String(256), nullable=True)

    storage_region = Column(String(32), nullable=False, default="workbench", index=True)
    gallery_rev = Column(Integer, nullable=True)
    parent_asset_id = Column(String(36), ForeignKey("media_assets.id"), nullable=True, index=True)
    gallery_stage = Column(String(32), nullable=True)  # released (gallery only)
    content_id = Column(String(36), nullable=True, index=True)
    vision_id = Column(String(36), ForeignKey("visions.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    versions = relationship(
        "MediaVersion",
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="MediaVersion.version_number.desc()",
    )
    uploads = relationship("MediaUpload", back_populates="asset", cascade="all, delete-orphan")
    vision = relationship("Vision", back_populates="assets")


class MediaVersion(Base):
    """Stored master rendition (re-upload increments version_number)."""

    __tablename__ = "media_versions"

    id = Column(String(36), primary_key=True, default=_uuid)
    asset_id = Column(String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    is_current = Column(Boolean, nullable=False, default=True)
    storage_key = Column(String(1024), nullable=False)
    original_filename = Column(String(512), nullable=False)
    mime_type = Column(String(256), nullable=False)
    byte_size = Column(BigInteger, nullable=False)
    checksum_sha256 = Column(String(64), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("MediaAsset", back_populates="versions")
    variants = relationship(
        "MediaVariant",
        back_populates="version",
        cascade="all, delete-orphan",
    )
    jobs = relationship(
        "MediaJob",
        back_populates="version",
        cascade="all, delete-orphan",
    )


class MediaVariant(Base):
    """Derivative for delivery (web MP3, display WebP, gallery master copy)."""

    __tablename__ = "media_variants"

    id = Column(String(36), primary_key=True, default=_uuid)
    version_id = Column(String(36), ForeignKey("media_versions.id", ondelete="CASCADE"), nullable=False)
    variant_kind = Column(String(64), nullable=False, index=True)
    storage_key = Column(String(1024), nullable=False)
    mime_type = Column(String(256), nullable=False)
    byte_size = Column(BigInteger, nullable=True)
    ready = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    version = relationship("MediaVersion", back_populates="variants")


class MediaUpload(Base):
    """In-flight multipart upload."""

    __tablename__ = "media_uploads"

    id = Column(String(36), primary_key=True, default=_uuid)
    asset_id = Column(String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False)
    s3_upload_id = Column(String(1024), nullable=False)
    inbox_storage_key = Column(String(1024), nullable=False)
    status = Column(String(32), nullable=False, default="uploading")
    expected_byte_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(256), nullable=True)
    part_count = Column(Integer, nullable=False)
    completed_parts = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("MediaAsset", back_populates="uploads")


class MediaJob(Base):
    """Async ingest or promote job (RQ worker)."""

    __tablename__ = "media_jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    version_id = Column(String(36), ForeignKey("media_versions.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String(64), nullable=False, index=True)  # ingest | promote
    status = Column(String(32), nullable=False, default="pending", index=True)
    promote_meta = Column(SAJSON, nullable=True)  # {workbench_asset_id, stage}
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    version = relationship("MediaVersion", back_populates="jobs")

"""Pydantic models for creative media APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UploadInitBody(BaseModel):
    filename: str = Field(..., min_length=1, max_length=512)
    mime_type: str = Field(..., min_length=3, max_length=256)
    byte_size: int = Field(..., gt=0)
    asset_type: str = Field(..., pattern="^(audio|image|video|document|archive)$")
    title: str | None = Field(None, max_length=512)
    tenant_slug: str | None = Field(None, max_length=64)


class PresignedPart(BaseModel):
    part_number: int
    url: str


class UploadInitResponse(BaseModel):
    asset_id: str
    upload_row_id: str
    multipart_storage_key: str
    s3_upload_id: str
    parts: list[PresignedPart]
    chunk_size_bytes: int


class UploadedPart(BaseModel):
    part_number: int = Field(..., ge=1)
    etag: str = Field(..., min_length=1)


class UploadCompleteBody(BaseModel):
    upload_row_id: str
    parts: list[UploadedPart]


class UploadCompleteResponse(BaseModel):
    asset_id: str
    version_id: str
    storage_key: str


class AssetUpdateBody(BaseModel):
    title: str | None = None
    tags: dict[str, Any] | None = None
    status: str | None = None


class VariantOut(BaseModel):
    id: str
    variant_kind: str
    storage_key: str
    mime_type: str
    byte_size: int | None = None
    ready: bool
    stream_url: str | None = None

    model_config = {"from_attributes": True}


class VersionOut(BaseModel):
    id: str
    version_number: int
    is_current: bool
    storage_key: str
    original_filename: str
    mime_type: str
    byte_size: int
    checksum_sha256: str | None
    duration_ms: int | None
    width: int | None
    height: int | None
    variants: list[VariantOut] = []

    model_config = {"from_attributes": True}


class AssetListItem(BaseModel):
    id: str
    tenant_slug: str
    title: str | None
    asset_type: str
    status: str
    visibility: str
    created_at: Any
    tags: dict[str, Any]

    model_config = {"from_attributes": True}


class AssetDetail(BaseModel):
    id: str
    tenant_slug: str
    title: str | None
    asset_type: str
    status: str
    visibility: str
    tags: dict[str, Any]
    created_at: Any
    versions: list[VersionOut] = []

    model_config = {"from_attributes": True}


class PublishedTrackOut(BaseModel):
    asset_id: str
    title: str | None
    duration_ms: int | None
    stream_url: str
    mime_type: str


class PublishedPhotoOut(BaseModel):
    asset_id: str
    title: str | None
    url: str
    mime_type: str


class PublishResponse(BaseModel):
    asset_id: str
    public_variants: list[VariantOut]

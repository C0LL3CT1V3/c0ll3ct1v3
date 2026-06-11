"""URL-based vision references (no file upload)."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.media import MediaAsset
from ..models.vision import Vision
_MAX_URL_LEN = 2048


def normalize_reference_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw or len(raw) > _MAX_URL_LEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid URL.")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="URL must use http or https.")
    return raw


def external_url_from_asset(asset: MediaAsset) -> str | None:
    tags = asset.tags or {}
    if tags.get("source") != "url":
        return None
    url = (tags.get("external_url") or "").strip()
    return url or None


def reference_title_for_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "link").removeprefix("www.")
    path = (parsed.path or "").strip("/")
    if path:
        segment = path.split("/")[-1]
        if segment:
            return f"{host}/{segment}"[:120]
    return host[:120]


def create_url_reference_asset(
    db: Session,
    *,
    tenant_slug: str,
    vision_id: str,
    url: str,
    created_by: str | None = None,
) -> MediaAsset:
    safe_url = normalize_reference_url(url)
    vision = (
        db.query(Vision)
        .filter(Vision.id == vision_id, Vision.tenant_slug == tenant_slug)
        .first()
    )
    if not vision:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vision not found.")

    asset = MediaAsset(
        tenant_slug=tenant_slug,
        title=reference_title_for_url(safe_url),
        asset_type="image",
        status="ready",
        storage_region="workbench",
        tags={"source": "url", "external_url": safe_url},
        created_by=created_by,
    )
    db.add(asset)
    db.flush()
    from .vision_pack import apply_vision_assignment

    apply_vision_assignment(db, asset, vision_id=vision_id, vision_role="reference")
    db.commit()
    db.refresh(asset)
    return asset

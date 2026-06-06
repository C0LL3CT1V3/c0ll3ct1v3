"""Vision group partitions: wireframe, references, and media for EPK builds."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models.media import MediaAsset, MediaVersion
from ..models.vision import Vision
from ..services.media_variants import best_image_variant, url_for_variant
from ..services.spaces_storage import get_s3_client, presigned_get_object

VISION_ROLES = frozenset({"wireframe", "reference", "media"})
ROLE_LIMITS: dict[str, int] = {"wireframe": 1, "reference": 3}
IMAGE_ONLY_ROLES = frozenset({"wireframe", "reference"})


def vision_role_from_tags(tags: dict | None) -> str:
    role = (tags or {}).get("vision_role")
    if role in VISION_ROLES:
        return role
    return "media"


def _preview_url_for_asset(db: Session, asset: MediaAsset) -> str | None:
    ver = (
        db.query(MediaVersion)
        .options(joinedload(MediaVersion.variants))
        .filter(MediaVersion.asset_id == asset.id, MediaVersion.is_current.is_(True))
        .first()
    )
    if not ver:
        return None
    if asset.asset_type == "image":
        best = best_image_variant(ver)
        if best:
            try:
                return url_for_variant(best)
            except Exception:
                pass
    if not settings.spaces_enabled:
        return None
    try:
        client = get_s3_client()
        return presigned_get_object(client, ver.storage_key)
    except Exception:
        return None


def _asset_to_pack_item(db: Session, asset: MediaAsset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "title": asset.title,
        "asset_type": asset.asset_type,
        "vision_role": vision_role_from_tags(asset.tags),
        "preview_url": _preview_url_for_asset(db, asset),
    }


def validate_vision_role_assignment(
    db: Session,
    *,
    asset: MediaAsset,
    vision_id: str | None,
    vision_role: str | None,
) -> str:
    """Return resolved role; raise HTTPException on slot violations."""
    role = vision_role or vision_role_from_tags(asset.tags)
    if role not in VISION_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid vision_role.")
    if vision_id is None:
        return role
    if role in IMAGE_ONLY_ROLES and asset.asset_type != "image":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Only images can be assigned as {role}.",
        )
    limit = ROLE_LIMITS.get(role)
    if limit is None:
        return role
    query = db.query(MediaAsset).filter(
        MediaAsset.vision_id == vision_id,
        MediaAsset.is_deleted.is_(False),
        MediaAsset.id != asset.id,
    )
    count = 0
    for row in query.all():
        if vision_role_from_tags(row.tags) == role:
            count += 1
    if count >= limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Vision already has the maximum number of {role} assets ({limit}).",
        )
    return role


def apply_vision_assignment(
    db: Session,
    asset: MediaAsset,
    *,
    vision_id: str | None,
    vision_role: str | None,
) -> None:
    """Set vision_id and tags.vision_role with slot validation."""
    if vision_id is None:
        asset.vision_id = None
        tags = dict(asset.tags or {})
        tags.pop("vision_role", None)
        asset.tags = tags
        return

    role = validate_vision_role_assignment(
        db,
        asset=asset,
        vision_id=vision_id,
        vision_role=vision_role or "media",
    )
    tags = dict(asset.tags or {})
    tags["vision_role"] = role
    asset.tags = tags
    asset.vision_id = vision_id


def get_vision_pack(db: Session, vision_id: str, tenant_slug: str) -> dict[str, Any]:
    vision = (
        db.query(Vision)
        .filter(Vision.id == vision_id, Vision.tenant_slug == tenant_slug)
        .first()
    )
    if not vision:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vision not found.")

    assets = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.vision_id == vision_id,
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.is_deleted.is_(False),
            MediaAsset.storage_region == "workbench",
        )
        .order_by(MediaAsset.created_at.asc())
        .all()
    )

    wireframe: dict[str, Any] | None = None
    references: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []

    for asset in assets:
        item = _asset_to_pack_item(db, asset)
        role = item["vision_role"]
        if role == "wireframe":
            wireframe = item
        elif role == "reference":
            references.append(item)
        else:
            media.append(item)

    return {
        "vision_id": vision.id,
        "vision_title": vision.title,
        "wireframe": wireframe,
        "references": references[:3],
        "media": media,
        "counts": {
            "wireframe": 1 if wireframe else 0,
            "references": len(references),
            "media": len(media),
        },
    }

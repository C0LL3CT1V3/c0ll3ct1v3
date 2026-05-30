"""Public EPK read endpoints (no auth)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from ...config import settings
from ...database import get_db
from ...models.media import MediaAsset, MediaVersion
from ...schemas.artist_schemas import coerce_epk_config
from ...schemas.epk_design_schemas import EpkDesignSpec, EpkSiteDesignOut
from ...schemas.media_schemas import PublishedPhotoOut, PublishedTrackOut
from ...services.artist_service import get_artist_by_slug
from ...services.epk_media_resolve import (
    best_image_variant,
    published_photos_for_tenant,
    published_tracks_for_tenant,
    url_for_variant,
)
from ...services.spaces_storage import presigned_get_object, get_s3_client

router = APIRouter(prefix="/epk", tags=["epk"])


def _design_from_config(cfg: dict, key: str) -> EpkDesignSpec | None:
    raw = cfg.get(key)
    if not raw or not isinstance(raw, dict):
        return None
    try:
        return EpkDesignSpec.model_validate(raw)
    except Exception:
        return None


@router.get("/site", response_model=EpkSiteDesignOut)
def epk_site(
    tenant_slug: str | None = None,
    db: Session = Depends(get_db),
) -> EpkSiteDesignOut:
    slug = (tenant_slug or settings.default_media_tenant_slug).strip().lower()
    artist = get_artist_by_slug(db, slug)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found.")
    cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    epk = coerce_epk_config(cfg)
    published_design = _design_from_config(cfg, "design_published") or _design_from_config(cfg, "design")
    return EpkSiteDesignOut(
        tenant_slug=artist.tenant_slug,
        display_name=artist.display_name,
        tagline=epk.tagline,
        bio=epk.bio,
        booking_email=epk.booking_email,
        social=epk.social,
        sections=epk.sections,
        design=published_design,
        design_published_at=cfg.get("design_published_at"),
        tracks=published_tracks_for_tenant(db, slug),
        photos=published_photos_for_tenant(db, slug),
    )


@router.get("/tracks", response_model=list[PublishedTrackOut])
def epk_tracks(
    tenant_slug: str | None = None,
    db: Session = Depends(get_db),
) -> list[PublishedTrackOut]:
    slug = (tenant_slug or settings.default_media_tenant_slug).strip().lower()
    rows = published_tracks_for_tenant(db, slug)
    return [PublishedTrackOut(**r) for r in rows]


@router.get("/photos", response_model=list[PublishedPhotoOut])
def epk_photos(
    tenant_slug: str | None = None,
    db: Session = Depends(get_db),
) -> list[PublishedPhotoOut]:
    slug = (tenant_slug or settings.default_media_tenant_slug).strip().lower()
    rows = published_photos_for_tenant(db, slug)
    return [PublishedPhotoOut(**r) for r in rows]


@router.get("/assets/{asset_id}/file")
def epk_asset_file(
    asset_id: str,
    tenant_slug: str | None = None,
    db: Session = Depends(get_db),
):
    """Redirect to a viewable URL for a published asset (dev-friendly when MinIO ACL is tight)."""
    slug = (tenant_slug or settings.default_media_tenant_slug).strip().lower()
    asset = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.id == asset_id,
            MediaAsset.tenant_slug == slug,
            MediaAsset.is_deleted.is_(False),
            MediaAsset.status == "published",
            MediaAsset.visibility == "public",
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    ver = (
        db.query(MediaVersion)
        .options(joinedload(MediaVersion.variants))
        .filter(MediaVersion.asset_id == asset.id, MediaVersion.is_current.is_(True))
        .first()
    )
    if not ver:
        raise HTTPException(status_code=404, detail="No version.")
    best = None
    if asset.asset_type == "image":
        from ...services.epk_media_resolve import best_image_variant

        best = best_image_variant(ver)
    elif asset.asset_type == "audio":
        from ...services.epk_media_resolve import best_audio_variant

        best = best_audio_variant(ver)
    if not best:
        raise HTTPException(status_code=404, detail="No public variant.")
    return RedirectResponse(url=url_for_variant(best), status_code=302)


@router.get("/press-kit")
def epk_press_kit(
    tenant_slug: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Return a presigned URL for a published press-kit archive, if configured."""
    from sqlalchemy.orm import joinedload

    slug = (tenant_slug or settings.default_media_tenant_slug).strip().lower()
    row = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions))
        .filter(
            MediaAsset.is_deleted.is_(False),
            MediaAsset.tenant_slug == slug,
            MediaAsset.asset_type == "archive",
            MediaAsset.status == "published",
            MediaAsset.visibility == "public",
        )
        .order_by(MediaAsset.created_at.desc())
        .first()
    )
    if not row:
        return {"download_url": None, "title": None}
    ver = next((v for v in row.versions if v.is_current), None)
    if not ver:
        return {"download_url": None, "title": row.title}
    if not settings.spaces_enabled:
        raise HTTPException(
            status_code=503,
            detail="Press kit download is unavailable (storage not configured).",
        )
    client = get_s3_client()
    url = presigned_get_object(client, ver.storage_key)
    return {"download_url": url, "title": row.title, "filename": ver.original_filename}

"""Resolve best public URLs for EPK media variants."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from ..models.media import MediaAsset, MediaVariant, MediaVersion
from .spaces_storage import public_url_for_key, presigned_get_object, get_s3_client
from ..config import settings


def _image_variant_rank(kind: str) -> int:
    return {"display_webp": 0, "published_delivery": 1}.get(kind, 5)


def _audio_variant_rank(kind: str) -> int:
    return {"web_mp3": 0, "web_aac": 1, "published_delivery": 2}.get(kind, 5)


def best_image_variant(version: MediaVersion) -> MediaVariant | None:
    cands = [v for v in version.variants if v.ready and v.mime_type.startswith("image/")]
    if not cands:
        return None
    public = [v for v in cands if "/public/" in v.storage_key]
    pool = public if public else cands
    pool.sort(key=lambda v: (_image_variant_rank(v.variant_kind), v.variant_kind))
    return pool[0]


def best_audio_variant(version: MediaVersion) -> MediaVariant | None:
    cands = [v for v in version.variants if v.ready and v.mime_type.startswith("audio/")]
    if not cands:
        return None
    public = [v for v in cands if "/public/" in v.storage_key]
    pool = public if public else cands
    pool.sort(key=lambda v: (_audio_variant_rank(v.variant_kind), v.variant_kind))
    return pool[0]


def _url_for_version_master(ver: MediaVersion) -> str | None:
    if not settings.spaces_enabled:
        return None
    try:
        client = get_s3_client()
        return presigned_get_object(client, ver.storage_key)
    except Exception:
        return None


def url_for_variant(variant: MediaVariant) -> str:
    if "/public/" in variant.storage_key:
        return public_url_for_key(variant.storage_key)
    if settings.spaces_enabled:
        try:
            client = get_s3_client()
            return presigned_get_object(client, variant.storage_key)
        except Exception:
            pass
    return public_url_for_key(variant.storage_key)


def published_tracks_for_tenant(db: Session, tenant_slug: str) -> list[dict]:
    rows = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions).joinedload(MediaVersion.variants))
        .filter(
            MediaAsset.is_deleted.is_(False),
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.asset_type == "audio",
            MediaAsset.status == "published",
            MediaAsset.visibility == "public",
        )
        .order_by(MediaAsset.created_at.asc())
        .limit(50)
        .all()
    )
    out: list[dict] = []
    for a in rows:
        ver = next((v for v in a.versions if v.is_current), None)
        if not ver:
            continue
        best = best_audio_variant(ver)
        if not best:
            continue
        out.append(
            {
                "asset_id": a.id,
                "title": a.title,
                "duration_ms": ver.duration_ms,
                "stream_url": url_for_variant(best),
                "mime_type": best.mime_type,
            }
        )
    return out


def published_photos_for_tenant(db: Session, tenant_slug: str) -> list[dict]:
    rows = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions).joinedload(MediaVersion.variants))
        .filter(
            MediaAsset.is_deleted.is_(False),
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.asset_type == "image",
            MediaAsset.status == "published",
            MediaAsset.visibility == "public",
        )
        .order_by(MediaAsset.created_at.asc())
        .limit(50)
        .all()
    )
    out: list[dict] = []
    for a in rows:
        ver = next((v for v in a.versions if v.is_current), None)
        if not ver:
            continue
        best = best_image_variant(ver)
        if not best:
            continue
        out.append(
            {
                "asset_id": a.id,
                "title": a.title,
                "url": url_for_variant(best),
                "mime_type": best.mime_type,
            }
        )
    return out


def studio_tracks_for_tenant(db: Session, tenant_slug: str) -> list[dict]:
    """Ready or published audio for portal design preview (not only live EPK)."""
    rows = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions).joinedload(MediaVersion.variants))
        .filter(
            MediaAsset.is_deleted.is_(False),
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.asset_type == "audio",
            MediaAsset.status.in_(("ready", "published")),
        )
        .order_by(MediaAsset.created_at.asc())
        .limit(50)
        .all()
    )
    out: list[dict] = []
    for a in rows:
        ver = next((v for v in a.versions if v.is_current), None)
        if not ver:
            continue
        best = best_audio_variant(ver)
        stream_url = url_for_variant(best) if best else _url_for_version_master(ver)
        if not stream_url:
            continue
        mime = best.mime_type if best else ver.mime_type
        out.append(
            {
                "asset_id": a.id,
                "title": a.title,
                "duration_ms": ver.duration_ms,
                "stream_url": stream_url,
                "mime_type": mime,
                "status": a.status,
            }
        )
    return out


def studio_photos_for_tenant(db: Session, tenant_slug: str) -> list[dict]:
    """Ready or published images for portal design preview."""
    rows = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions).joinedload(MediaVersion.variants))
        .filter(
            MediaAsset.is_deleted.is_(False),
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.asset_type == "image",
            MediaAsset.status.in_(("ready", "published")),
        )
        .order_by(MediaAsset.created_at.asc())
        .limit(50)
        .all()
    )
    out: list[dict] = []
    for a in rows:
        ver = next((v for v in a.versions if v.is_current), None)
        if not ver:
            continue
        best = best_image_variant(ver)
        url = url_for_variant(best) if best else _url_for_version_master(ver)
        if not url:
            continue
        mime = best.mime_type if best else ver.mime_type
        out.append(
            {
                "asset_id": a.id,
                "title": a.title,
                "url": url,
                "mime_type": mime,
                "status": a.status,
            }
        )
    return out

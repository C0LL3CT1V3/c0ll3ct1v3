"""Pick delivery variants and build stream/preview URLs for gallery assets."""

from __future__ import annotations

from ..config import settings
from ..models.media import MediaVariant, MediaVersion
from .spaces_storage import get_s3_client, presigned_get_object, public_url_for_key
from .storage_paths import is_public_delivery_key


def _image_variant_rank(kind: str) -> int:
    return {"display_webp": 0, "published_delivery": 1}.get(kind, 5)


def _audio_variant_rank(kind: str) -> int:
    return {"web_mp3": 0, "web_aac": 1, "published_delivery": 2}.get(kind, 5)


def best_image_variant(version: MediaVersion) -> MediaVariant | None:
    cands = [v for v in version.variants if v.ready and v.mime_type.startswith("image/")]
    if not cands:
        return None
    public = [v for v in cands if is_public_delivery_key(v.storage_key)]
    pool = public if public else cands
    pool.sort(key=lambda v: (_image_variant_rank(v.variant_kind), v.variant_kind))
    return pool[0]


def best_audio_variant(version: MediaVersion) -> MediaVariant | None:
    cands = [v for v in version.variants if v.ready and v.mime_type.startswith("audio/")]
    if not cands:
        return None
    public = [v for v in cands if is_public_delivery_key(v.storage_key)]
    pool = public if public else cands
    pool.sort(key=lambda v: (_audio_variant_rank(v.variant_kind), v.variant_kind))
    return pool[0]


def url_for_variant(variant: MediaVariant) -> str:
    if is_public_delivery_key(variant.storage_key):
        return public_url_for_key(variant.storage_key)
    if settings.spaces_enabled:
        try:
            client = get_s3_client()
            return presigned_get_object(client, variant.storage_key)
        except Exception:
            pass
    return public_url_for_key(variant.storage_key)

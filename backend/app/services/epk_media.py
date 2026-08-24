"""Media proxy helpers for booker EPK pages."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models.artist import Artist
from ..models.media import MediaAsset, MediaVersion
from .artist_service import storage_namespace_for_artist
from .epk_public_config import get_epk_public_raw
from .spaces_storage import get_s3_client, presigned_get_object

STREAMING_KEYS = frozenset({"spotify", "soundcloud", "bandcamp", "youtube"})
SOCIAL_KEYS = frozenset({"instagram", "tiktok", "twitter", "x"})
_BOT_UA = (
    "gptbot",
    "chatgpt-user",
    "claudebot",
    "anthropic-ai",
    "google-extended",
    "bytespider",
    "ccbot",
    "amazonbot",
    "perplexitybot",
    "applebot-extended",
    "facebookbot",
    "meta-externalagent",
    "cohere-ai",
    "youbot",
)


def is_machine_request(request: Request) -> bool:
    ua = (request.headers.get("user-agent") or "").lower()
    if any(token in ua for token in _BOT_UA):
        return True
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept:
        return False
    return "application/json" in accept


def epk_content_hash(artist: Artist) -> str:
    raw = get_epk_public_raw(artist)
    payload = json.dumps(raw, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def collect_epk_asset_ids(data: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    hero = data.get("hero_video") or {}
    if hero.get("asset_id"):
        ids.add(str(hero["asset_id"]))
    for photo in data.get("photos") or []:
        if photo.get("asset_id"):
            ids.add(str(photo["asset_id"]))
    for track in data.get("audio_samples") or []:
        if track.get("asset_id"):
            ids.add(str(track["asset_id"]))
    rider = data.get("tech_rider") or {}
    if rider.get("asset_id"):
        ids.add(str(rider["asset_id"]))
    return ids


def media_proxy_url(
    tenant_slug: str,
    asset_id: str,
    *,
    preview_token: str | None = None,
) -> str:
    base = settings.epk_sim_base_url.rstrip("/")
    if preview_token:
        return f"{base}/artists/epk-preview/media/{asset_id}?token={preview_token}"
    return f"{base}/artists/public/{tenant_slug}/epk/media/{asset_id}"


def _presigned_asset_url(db: Session, asset: MediaAsset) -> str | None:
    ver = (
        db.query(MediaVersion)
        .options(joinedload(MediaVersion.variants))
        .filter(MediaVersion.asset_id == asset.id, MediaVersion.is_current.is_(True))
        .first()
    )
    if not ver:
        return None
    if not settings.spaces_enabled:
        return None
    try:
        client = get_s3_client()
        return presigned_get_object(client, ver.storage_key)
    except Exception:
        return None


def redirect_epk_asset(
    db: Session,
    *,
    artist: Artist,
    asset_id: str,
    allowed_ids: set[str],
) -> RedirectResponse:
    if asset_id not in allowed_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not in EPK.")
    asset = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.id == asset_id,
            MediaAsset.tenant_slug == storage_namespace_for_artist(artist),
            MediaAsset.is_deleted.is_(False),
        )
        .first()
    )
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    url = _presigned_asset_url(db, asset)
    if not url:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Media URL unavailable.")
    return RedirectResponse(url, status_code=302)

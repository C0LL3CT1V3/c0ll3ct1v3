"""Booker-facing EPK public config — slot CRUD, resolve, and HTML render."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models.artist import Artist
from ..models.media import MediaAsset, MediaVersion
from ..schemas.artist_schemas import coerce_epk_config
from ..schemas.epk_public_schemas import EpkPublicConfig, EpkPublicPatch
from .epk_media import STREAMING_KEYS, SOCIAL_KEYS, epk_content_hash, media_proxy_url
from .epk_streaming_logos import streaming_logo_link
from .epk_preview_token import epk_preview_page_url, mint_epk_preview_token
from .public_urls import public_epk_url, public_site_origin
from .artist_service import resolve_artist_by_public_slug, storage_namespace_for_artist
from .epk_public_config import coerce_epk_public, get_epk_public_raw
from .media_variants import best_image_variant, url_for_variant
from .spaces_storage import get_s3_client, presigned_get_object

_YOUTUBE_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{6,})"
)


def _save_epk_public(db: Session, artist: Artist, epk: EpkPublicConfig) -> None:
    cfg = dict(artist.epk_config or {})
    cfg["epk_public"] = epk.model_dump()
    artist.epk_config = cfg
    db.commit()
    db.refresh(artist)


def _assert_workbench_asset(db: Session, artist: Artist, asset_id: str) -> MediaAsset:
    row = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.id == asset_id,
            MediaAsset.tenant_slug == storage_namespace_for_artist(artist),
            MediaAsset.is_deleted.is_(False),
            MediaAsset.storage_region == "workbench",
        )
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Asset {asset_id} not found in Vault.")
    return row


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


def _same_origin_media_proxy(artist: Artist, asset_id: str) -> str:
    """API proxy on the artist subdomain (avoids apex cross-origin + srcdoc ORB issues)."""
    origin = public_site_origin(artist.tenant_slug)
    return f"{origin}/api/artists/public/{artist.tenant_slug}/epk/media/{asset_id}"


def _delivery_url_for_asset(
    db: Session,
    artist: Artist,
    asset: MediaAsset,
    *,
    preview_token: str | None = None,
) -> str:
    """Prefer direct HTTPS object URLs; fall back to same-origin API proxy."""
    if preview_token:
        return media_proxy_url(artist.tenant_slug, asset.id, preview_token=preview_token)
    direct = _preview_url_for_asset(db, asset)
    if direct and direct.startswith("https://"):
        return direct
    return _same_origin_media_proxy(artist, asset.id)


def _youtube_embed_id(url: str) -> str | None:
    if not url:
        return None
    m = _YOUTUBE_RE.search(url)
    return m.group(1) if m else None


def patch_epk_public(db: Session, artist: Artist, body: EpkPublicPatch) -> EpkPublicConfig:
    epk = coerce_epk_public(get_epk_public_raw(artist))
    patch = body.model_dump(exclude_unset=True)

    if "hero_video" in patch and patch["hero_video"] is not None:
        hv = patch["hero_video"]
        if hv.get("asset_id"):
            asset = _assert_workbench_asset(db, artist, hv["asset_id"])
            if asset.asset_type not in ("video", "audio"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Hero must be a video or audio asset.")
        epk.hero_video = epk.hero_video.model_copy(update=hv)

    if "photos" in patch and patch["photos"] is not None:
        for slot in patch["photos"]:
            _assert_workbench_asset(db, artist, slot["asset_id"])
        epk.photos = [p for p in patch["photos"]]

    if "audio_samples" in patch and patch["audio_samples"] is not None:
        for slot in patch["audio_samples"]:
            asset = _assert_workbench_asset(db, artist, slot["asset_id"])
            if asset.asset_type != "audio":
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Audio samples must be audio assets.")
        epk.audio_samples = [a for a in patch["audio_samples"]]

    if "tech_rider" in patch:
        tr = patch["tech_rider"]
        if tr and tr.get("asset_id"):
            _assert_workbench_asset(db, artist, tr["asset_id"])
        epk.tech_rider = tr

    if "bio" in patch and patch["bio"] is not None:
        epk.bio = patch["bio"]
    if "booking_email" in patch and patch["booking_email"] is not None:
        epk.booking_email = patch["booking_email"]
    if "social" in patch and patch["social"] is not None:
        epk.social = patch["social"]

    _save_epk_public(db, artist, epk)
    return epk


def publish_epk_public(db: Session, artist: Artist) -> EpkPublicConfig:
    epk = coerce_epk_public(get_epk_public_raw(artist))
    from .epk_booker_completeness import evaluate_booker_completeness

    completeness = evaluate_booker_completeness(db, artist)
    if completeness["required_score"] < 0.6:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="EPK is not ready to publish — fill required slots first.",
        )
    epk.published = True
    epk.published_at = datetime.now(timezone.utc).isoformat()
    cfg = dict(artist.epk_config or {})
    cfg["epk_public"] = epk.model_dump()
    cfg["epk_public_snapshot"] = resolve_epk_public(db, artist, epk)
    cfg["epk_public_published"] = True
    cfg["epk_public_published_at"] = epk.published_at
    artist.epk_config = cfg
    db.commit()
    db.refresh(artist)
    return epk


def resolve_epk_public(
    db: Session,
    artist: Artist,
    epk: EpkPublicConfig | None = None,
    *,
    preview_token: str | None = None,
) -> dict[str, Any]:
    epk = epk or coerce_epk_public(get_epk_public_raw(artist))
    cfg = coerce_epk_config(artist.epk_config)

    hero: dict[str, Any] | None = None
    if epk.hero_video.type == "youtube" and epk.hero_video.url.strip():
        yt_id = _youtube_embed_id(epk.hero_video.url)
        hero = {
            "type": "youtube",
            "url": epk.hero_video.url,
            "embed_id": yt_id,
            "embed_url": f"https://www.youtube.com/embed/{yt_id}" if yt_id else None,
        }
    elif epk.hero_video.asset_id:
        asset = (
            db.query(MediaAsset)
            .filter(MediaAsset.id == epk.hero_video.asset_id, MediaAsset.is_deleted.is_(False))
            .first()
        )
        if asset:
            hero = {
                "type": "asset",
                "asset_id": asset.id,
                "title": asset.title,
                "asset_type": asset.asset_type,
                "url": _delivery_url_for_asset(
                    db, artist, asset, preview_token=preview_token
                ),
            }

    photos = []
    for slot in epk.photos:
        asset = (
            db.query(MediaAsset)
            .filter(MediaAsset.id == slot.asset_id, MediaAsset.is_deleted.is_(False))
            .first()
        )
        if asset:
            photos.append(
                {
                    "asset_id": asset.id,
                    "title": asset.title,
                    "caption": slot.caption,
                    "url": _delivery_url_for_asset(
                        db, artist, asset, preview_token=preview_token
                    ),
                }
            )

    audio_samples = []
    for slot in epk.audio_samples:
        asset = (
            db.query(MediaAsset)
            .filter(MediaAsset.id == slot.asset_id, MediaAsset.is_deleted.is_(False))
            .first()
        )
        if asset:
            audio_samples.append(
                {
                    "asset_id": asset.id,
                    "title": slot.title or asset.title,
                    "url": _delivery_url_for_asset(
                        db, artist, asset, preview_token=preview_token
                    ),
                }
            )

    tech_rider = None
    if epk.tech_rider and epk.tech_rider.asset_id:
        asset = (
            db.query(MediaAsset)
            .filter(MediaAsset.id == epk.tech_rider.asset_id, MediaAsset.is_deleted.is_(False))
            .first()
        )
        if asset:
            tech_rider = {
                "asset_id": asset.id,
                "title": asset.title,
                "url": _delivery_url_for_asset(
                    db, artist, asset, preview_token=preview_token
                ),
            }

    return {
        "template": epk.template,
        "published": epk.published,
        "published_at": epk.published_at,
        "display_name": artist.display_name,
        "tenant_slug": artist.tenant_slug,
        "bio": epk.bio or cfg.bio,
        "booking_email": epk.booking_email or cfg.booking_email,
        "social": {**(cfg.social or {}), **(epk.social or {})},
        "hero_video": hero,
        "photos": photos,
        "audio_samples": audio_samples,
        "tech_rider": tech_rider,
    }


def get_my_epk_public(db: Session, artist: Artist) -> dict[str, Any]:
    epk = coerce_epk_public(get_epk_public_raw(artist))
    resolved = resolve_epk_public(db, artist, epk)
    from .epk_booker_completeness import evaluate_booker_completeness

    completeness = evaluate_booker_completeness(db, artist)
    return {
        "config": epk.model_dump(),
        "resolved": resolved,
        "completeness": completeness,
        "preview_url": f"/artists/public/{artist.tenant_slug}/epk/page",
        "public_epk_url": public_epk_url(artist.tenant_slug),
    }


def get_public_booker_epk(db: Session, tenant_slug: str) -> dict[str, Any]:
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="EPK not found.")

    cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    snapshot = cfg.get("epk_public_snapshot")
    epk = coerce_epk_public(get_epk_public_raw(artist))

    if not epk.published and not cfg.get("epk_public_published"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="EPK not published.")

    if isinstance(snapshot, dict) and snapshot.get("display_name"):
        data = snapshot
    else:
        data = resolve_epk_public(db, artist, epk)

    return {
        "tenant_slug": artist.tenant_slug,
        "display_name": data.get("display_name") or artist.display_name,
        "template": data.get("template") or "booker_v1",
        "published": True,
        "bio": data.get("bio") or "",
        "booking_email": data.get("booking_email") or "",
        "social": data.get("social") or {},
        "hero_video": data.get("hero_video"),
        "photos": data.get("photos") or [],
        "audio_samples": data.get("audio_samples") or [],
        "tech_rider": data.get("tech_rider"),
        "page_url": f"/artists/public/{tenant_slug}/epk/page",
    }


def _build_booker_epk_html(data: dict[str, Any], *, draft: bool = False) -> str:
    name = html.escape(data.get("display_name") or "Artist")
    bio = html.escape(data.get("bio") or "").replace("\n", "<br>")
    booking = html.escape(data.get("booking_email") or "")
    social = data.get("social") or {}

    hero_html = ""
    hero = data.get("hero_video")
    if hero:
        if hero.get("type") == "youtube":
            embed = hero.get("embed_url")
            if not embed and hero.get("url"):
                yt_id = _youtube_embed_id(hero["url"])
                if yt_id:
                    embed = f"https://www.youtube.com/embed/{yt_id}"
            if embed:
                embed_safe = html.escape(embed)
                hero_html = f"""
            <div class="booker-epk-hero">
              <div class="booker-epk-video-wrap">
                <iframe src="{embed_safe}" title="Hero video" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen loading="lazy"></iframe>
              </div>
            </div>"""
        elif hero.get("url"):
            url = html.escape(hero["url"])
            if hero.get("asset_type") == "video":
                hero_html = f"""
                <div class="booker-epk-hero">
                  <video class="booker-epk-video-native" controls playsinline preload="metadata" src="{url}"></video>
                </div>"""
            else:
                hero_html = f"""
                <div class="booker-epk-hero">
                  <audio controls preload="metadata" src="{url}"></audio>
                </div>"""

    photos_html = ""
    for photo in data.get("photos") or []:
        url = photo.get("url")
        if not url:
            continue
        caption = (photo.get("caption") or "").strip()
        cap_html = html.escape(caption) if caption else ""
        photos_html += f"""
        <figure class="booker-epk-gallery-item">
          <img src="{html.escape(url)}" alt="" loading="lazy" />
          {f'<figcaption>{cap_html}</figcaption>' if cap_html else ''}
        </figure>"""

    audio_html = ""
    for track in data.get("audio_samples") or []:
        url = track.get("url")
        if not url:
            continue
        title = html.escape(track.get("title") or "Track")
        audio_html += f"""
        <div class="booker-epk-track">
          <div class="booker-epk-track-icon" aria-hidden="true">♫</div>
          <div class="booker-epk-track-body">
            <span class="booker-epk-track-title">{title}</span>
            <audio controls src="{html.escape(url)}"></audio>
          </div>
        </div>"""

    streaming_html = ""
    social_html = ""
    for key, val in sorted(social.items()):
        if not val or val == "in_page":
            continue
        label = html.escape(key.replace("_", " ").title())
        text_link = (
            f'<a class="booker-epk-link" href="{html.escape(val)}" '
            f'target="_blank" rel="noreferrer">{label}</a>'
        )
        if key.lower() in STREAMING_KEYS:
            streaming_html += streaming_logo_link(key, val)
        elif key.lower() in SOCIAL_KEYS:
            social_html += text_link
        else:
            streaming_html += streaming_logo_link(key, val)

    rider_html = ""
    rider = data.get("tech_rider")
    if rider and rider.get("url"):
        rider_html = (
            f'<p class="booker-epk-rider">'
            f'<a href="{html.escape(rider["url"])}" target="_blank" rel="noreferrer">Tech rider</a></p>'
        )

    draft_banner = (
        '<div class="booker-epk-draft-banner">Draft preview — not published yet</div>'
        if draft
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{name} — Press Kit</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      height: auto;
      min-height: 0;
    }}
    body {{
      font-family: Georgia, "Times New Roman", serif;
      background: #0a0a0c;
      color: #eceae6;
      margin: 0;
      padding: 2rem 1.25rem 1.5rem;
    }}
    .booker-epk-wrap {{ max-width: 920px; margin: 0 auto; }}
    .booker-epk-draft-banner {{
      background: #3d3528;
      color: #f5e6c8;
      text-align: center;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      margin-bottom: 1.5rem;
      font-family: system-ui, sans-serif;
      font-size: 0.85rem;
    }}
    .booker-epk-header h1 {{
      margin: 0 0 0.35rem;
      font-size: 2.4rem;
      font-weight: 400;
      letter-spacing: 0.02em;
    }}
    .booker-epk-sub {{
      margin: 0;
      font-family: system-ui, sans-serif;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #9a958c;
    }}
    .booker-epk-hero {{ margin: 1.75rem 0; }}
    .booker-epk-video-wrap {{
      position: relative;
      padding-bottom: 56.25%;
      height: 0;
      overflow: hidden;
      border-radius: 8px;
      background: #111;
    }}
    .booker-epk-video-wrap iframe {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      border: 0;
    }}
    .booker-epk-video-native {{
      width: 100%;
      border-radius: 8px;
      background: #111;
    }}
    .booker-epk-bio {{
      line-height: 1.75;
      margin: 1.75rem 0;
      font-size: 1.05rem;
      color: #d8d4cc;
    }}
    .booker-epk-gallery {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.65rem;
      margin: 2rem 0;
    }}
    @media (max-width: 720px) {{
      .booker-epk-gallery {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .booker-epk-gallery-item {{
      margin: 0;
      overflow: hidden;
      border-radius: 6px;
      aspect-ratio: 4 / 5;
      background: #141418;
    }}
    .booker-epk-gallery-item img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      transition: transform 0.3s ease;
    }}
    .booker-epk-gallery-item:hover img {{ transform: scale(1.03); }}
    .booker-epk-gallery-item figcaption {{
      display: none;
    }}
    .booker-epk-tracks {{ margin: 2rem 0; }}
    .booker-epk-track {{
      display: flex;
      gap: 0.85rem;
      align-items: flex-start;
      padding: 0.85rem 0;
      border-bottom: 1px solid #222;
    }}
    .booker-epk-track-icon {{
      width: 44px;
      height: 44px;
      border-radius: 8px;
      background: linear-gradient(135deg, #2a2438, #1a1820);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.35rem;
      color: #c4a574;
      flex-shrink: 0;
    }}
    .booker-epk-track-body {{ flex: 1; min-width: 0; }}
    .booker-epk-track-title {{
      display: block;
      font-family: system-ui, sans-serif;
      font-size: 0.9rem;
      color: #b8b4ac;
      margin-bottom: 0.4rem;
    }}
    .booker-epk-track audio {{ width: 100%; }}
    .booker-epk-email {{
      font-family: system-ui, sans-serif;
      font-size: 1rem;
      margin: 1.5rem 0 1rem;
    }}
    .booker-epk-email a {{ color: #c4a574; }}
    .booker-epk-streaming-section {{
      margin: 1.25rem 0 1.75rem;
    }}
    .booker-epk-streaming-label {{
      margin: 0 0 0.75rem;
      font-family: system-ui, sans-serif;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: #9a958c;
    }}
    .booker-epk-streaming, .booker-epk-socials {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.65rem 1.25rem;
      margin: 0;
      font-family: system-ui, sans-serif;
      align-items: center;
    }}
    .booker-epk-socials {{
      margin: 1.25rem 0;
    }}
    .booker-epk-streaming-logo {{
      display: inline-flex;
      line-height: 0;
      opacity: 0.92;
      transition: opacity 0.15s ease, transform 0.15s ease;
    }}
    .booker-epk-streaming-logo:hover {{
      opacity: 1;
      transform: scale(1.06);
    }}
    .booker-epk-streaming-logo img {{
      display: block;
      width: 2.25rem;
      height: 2.25rem;
      border-radius: 0.25rem;
    }}
    .booker-epk-link {{
      color: #c4a574;
      text-decoration: none;
      font-size: 0.9rem;
      text-transform: capitalize;
    }}
    .booker-epk-link:hover {{ text-decoration: underline; }}
    .booker-epk-rider {{
      font-family: system-ui, sans-serif;
      margin-top: 1.5rem;
    }}
    .booker-epk-rider a {{ color: #c4a574; }}
  </style>
</head>
<body>
  <div class="booker-epk-wrap">
    {draft_banner}
    <header class="booker-epk-header">
      <h1>{name}</h1>
      <p class="booker-epk-sub">Electronic Press Kit</p>
    </header>
    {hero_html}
    {f'<section class="booker-epk-streaming-section"><h2 class="booker-epk-streaming-label">Streaming links</h2><div class="booker-epk-streaming">{streaming_html}</div></section>' if streaming_html else ''}
    <section class="booker-epk-bio">{bio or '<em>Bio coming soon.</em>'}</section>
    {f'<section class="booker-epk-gallery">{photos_html}</section>' if photos_html else ''}
    {f'<section class="booker-epk-tracks">{audio_html}</section>' if audio_html else ''}
    {f'<p class="booker-epk-email">Booking: <a href="mailto:{booking}">{booking}</a></p>' if booking else ''}
    {f'<div class="booker-epk-socials">{social_html}</div>' if social_html else ''}
    {rider_html}
  </div>
</body>
</html>"""


def render_draft_booker_epk_html(db: Session, artist: Artist, *, preview_token: str) -> str:
    epk = coerce_epk_public(get_epk_public_raw(artist))
    data = resolve_epk_public(db, artist, epk, preview_token=preview_token)
    return _build_booker_epk_html(data, draft=True)


def create_epk_preview_link(db: Session, artist: Artist) -> str:
    token = mint_epk_preview_token(artist_id=artist.id, content_hash=epk_content_hash(artist))
    return epk_preview_page_url(token)


def render_booker_epk_html(db: Session, tenant_slug: str) -> str:
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="EPK not found.")
    cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    if not cfg.get("epk_public_published"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="EPK not published.")
    epk = coerce_epk_public(get_epk_public_raw(artist))
    data = resolve_epk_public(db, artist, epk, preview_token=None)
    snap = cfg.get("epk_public_snapshot")
    if isinstance(snap, dict):
        for key in ("display_name", "bio", "booking_email", "social"):
            if snap.get(key) is not None:
                data[key] = snap[key]
    data["published"] = True
    return _build_booker_epk_html(data, draft=False)

"""Artist Homebase — events calendar and Square pay nested in epk_config."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.artist import Artist
from ..models.media import MediaAsset
from ..schemas.homebase_schemas import (
    HomebaseConfig,
    HomebaseEvent,
    HomebasePatch,
    HomebasePay,
)
from ..config import settings
from .artist_service import resolve_artist_by_public_slug, storage_namespace_for_artist
from .epk_public import _assert_workbench_asset
from .public_urls import public_homebase_url
from .square_checkout import checkout_configured

HEADLINE_MAX = 280
NOTES_MAX = 500
TITLE_MAX = 160
VENUE_MAX = 160
CITY_MAX = 120
LABEL_MAX = 40
AMOUNT_MIN = 1
AMOUNT_MAX = 10_000
AMOUNTS_CAP = 8
DEFAULT_AMOUNTS = [5, 10, 20]


def get_homebase_raw(artist: Artist) -> dict[str, Any]:
    cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    raw = cfg.get("homebase")
    return raw if isinstance(raw, dict) else {}


def collect_homebase_asset_ids(raw: dict[str, Any] | None) -> set[str]:
    ids: set[str] = set()
    events = raw.get("events") if isinstance(raw, dict) else None
    if not isinstance(events, list):
        return ids
    for item in events:
        if not isinstance(item, dict):
            continue
        asset_id = str(item.get("image_asset_id") or "").strip()
        if asset_id:
            ids.add(asset_id)
    return ids


def coerce_homebase(raw: dict[str, Any] | None) -> HomebaseConfig:
    if not raw:
        return HomebaseConfig()
    data = dict(raw)
    data["headline"] = _clip(data.get("headline"), HEADLINE_MAX)
    data["published"] = bool(data.get("published"))
    events = data.get("events")
    data["events"] = [_coerce_event(item) for item in events] if isinstance(events, list) else []
    data["events"] = [e for e in data["events"] if e is not None]
    pay_raw = data.get("pay") if isinstance(data.get("pay"), dict) else {}
    tips_raw = data.get("tips") if isinstance(data.get("tips"), dict) else {}
    data["pay"] = _coerce_pay(pay_raw, tips_raw)
    data.pop("tips", None)
    return HomebaseConfig.model_validate(data)


def _clip(value: Any, limit: int) -> str:
    text = "" if value is None else str(value).strip()
    return text[:limit]


def _coerce_event(raw: Any) -> HomebaseEvent | None:
    if not isinstance(raw, dict):
        return None
    event_id = str(raw.get("id") or "").strip() or str(uuid.uuid4())
    end = raw.get("end")
    end_s = None if end is None or str(end).strip() == "" else str(end).strip()
    image_asset_id = str(raw.get("image_asset_id") or "").strip() or None
    return HomebaseEvent(
        id=event_id,
        title=_clip(raw.get("title"), TITLE_MAX),
        start=_clip(raw.get("start"), 64),
        end=end_s[:64] if end_s else None,
        venue=_clip(raw.get("venue"), VENUE_MAX),
        city=_clip(raw.get("city"), CITY_MAX),
        ticket_url=_sanitize_https_url(str(raw.get("ticket_url") or "")),
        notes=_clip(raw.get("notes"), NOTES_MAX),
        image_asset_id=image_asset_id,
    )


def _coerce_amounts(raw: Any) -> list[int]:
    if not isinstance(raw, list) or not raw:
        return list(DEFAULT_AMOUNTS)
    out: list[int] = []
    for item in raw:
        try:
            n = int(item)
        except (TypeError, ValueError):
            continue
        if AMOUNT_MIN <= n <= AMOUNT_MAX and n not in out:
            out.append(n)
        if len(out) >= AMOUNTS_CAP:
            break
    return out or list(DEFAULT_AMOUNTS)


def _coerce_pay(pay_raw: dict[str, Any], tips_raw: dict[str, Any]) -> HomebasePay:
    src = pay_raw if pay_raw else tips_raw
    enabled = src.get("enabled")
    if enabled is None:
        enabled = True
    label = _clip(src.get("button_label") or "Pay", LABEL_MAX) or "Pay"
    return HomebasePay(
        enabled=bool(enabled),
        blurb=_clip(src.get("blurb"), HEADLINE_MAX),
        amounts=_coerce_amounts(src.get("amounts")),
        button_label=label,
    )


def _sanitize_https_url(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered.startswith(("javascript:", "data:", "vbscript:", "file:")):
        return ""
    if not lowered.startswith("https://"):
        return ""
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc or not parsed.hostname:
        return ""
    return text


def _save_homebase(db: Session, artist: Artist, homebase: HomebaseConfig) -> None:
    cfg = dict(artist.epk_config or {})
    cfg["homebase"] = homebase.model_dump()
    artist.epk_config = cfg
    db.commit()
    db.refresh(artist)


def get_my_homebase(artist: Artist) -> dict[str, Any]:
    homebase = coerce_homebase(get_homebase_raw(artist))
    return {
        "config": homebase.model_dump(),
        "public_homebase_url": public_homebase_url(artist.tenant_slug),
        "checkout_available": checkout_configured(),
    }


def _validate_event_image(db: Session, artist: Artist, event: HomebaseEvent) -> None:
    if not event.image_asset_id:
        return
    asset = _assert_workbench_asset(db, artist, event.image_asset_id)
    if asset.asset_type != "image":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Event graphic must be an image.")


def patch_homebase(db: Session, artist: Artist, body: HomebasePatch) -> HomebaseConfig:
    homebase = coerce_homebase(get_homebase_raw(artist))
    patch = body.model_dump(exclude_unset=True)

    if "headline" in patch and patch["headline"] is not None:
        homebase.headline = _clip(patch["headline"], HEADLINE_MAX)

    if "events" in patch and patch["events"] is not None:
        coerced = [_coerce_event(e if isinstance(e, dict) else e.model_dump()) for e in patch["events"]]
        events = [e for e in coerced if e is not None]
        for event in events:
            _validate_event_image(db, artist, event)
        homebase.events = events

    if "pay" in patch and patch["pay"] is not None:
        current = homebase.pay.model_dump()
        current.update({k: v for k, v in patch["pay"].items() if v is not None})
        homebase.pay = _coerce_pay(current, {})

    _save_homebase(db, artist, homebase)
    return homebase


def publish_homebase(db: Session, artist: Artist) -> HomebaseConfig:
    homebase = coerce_homebase(get_homebase_raw(artist))
    homebase.published = True
    _save_homebase(db, artist, homebase)
    return homebase


def _event_sort_key(event: dict[str, Any]) -> tuple[int, str]:
    start = str(event.get("start") or "")
    try:
        parsed = datetime.fromisoformat(start.replace("Z", "+00:00"))
        return (0, parsed.isoformat())
    except ValueError:
        return (1, start)


def _public_pay(pay: HomebasePay) -> dict[str, Any]:
    if not pay.enabled:
        return {"enabled": False, "blurb": "", "amounts": [], "button_label": pay.button_label or "Pay"}
    return {
        "enabled": True,
        "blurb": pay.blurb,
        "amounts": list(pay.amounts),
        "button_label": pay.button_label or "Pay",
    }


def _lookup_image(db: Session, artist: Artist, asset_id: str) -> MediaAsset | None:
    return (
        db.query(MediaAsset)
        .filter(
            MediaAsset.id == asset_id,
            MediaAsset.tenant_slug == storage_namespace_for_artist(artist),
            MediaAsset.is_deleted.is_(False),
        )
        .first()
    )


def _homebase_proxy_url(artist: Artist, asset_id: str) -> str:
    """API proxy the public React page can load (same host pattern as EPK media_proxy_url)."""
    base = settings.epk_sim_base_url.rstrip("/")
    return f"{base}/artists/public/{artist.tenant_slug}/homebase/media/{asset_id}"


def _event_image_url(db: Session, artist: Artist, asset_id: str) -> str | None:
    asset = _lookup_image(db, artist, asset_id)
    if not asset:
        return None
    # Always proxy so local Compose and tenant hosts resolve through the API, not production origin.
    return _homebase_proxy_url(artist, asset_id)


def get_public_homebase(db: Session, tenant_slug: str) -> dict[str, Any]:
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Homebase not found or not published.")

    homebase = coerce_homebase(get_homebase_raw(artist))
    if not homebase.published:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Homebase not found or not published.")

    events = [e.model_dump() for e in homebase.events]
    for item in events:
        asset_id = item.get("image_asset_id")
        item["image_url"] = _event_image_url(db, artist, asset_id) if asset_id else None
    events.sort(key=_event_sort_key)
    pay = _public_pay(homebase.pay)
    available = checkout_configured()
    return {
        "tenant_slug": artist.tenant_slug,
        "display_name": artist.display_name,
        "published": True,
        "headline": homebase.headline,
        "events": events,
        "pay": pay,
        "checkout_available": bool(available and pay.get("enabled")),
        "page_url": public_homebase_url(artist.tenant_slug),
    }

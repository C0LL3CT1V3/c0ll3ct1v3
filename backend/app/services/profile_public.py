"""Public musician profile (MySpace-style) — read published artist pages."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.artist import Artist
from .artist_service import resolve_artist_by_public_slug
from ..schemas.artist_schemas import coerce_epk_config
from .epk_draft import get_or_init_draft
from .epk_html_draft import is_html_draft, render_draft_html
from .manager_epk_service import build_preview_payload


def _published_design(artist: Artist) -> dict[str, Any]:
    cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    page = cfg.get("profile_page")
    if isinstance(page, dict) and page.get("format"):
        return page
    design = cfg.get("epk_design")
    if isinstance(design, dict) and design.get("layout"):
        return design
    draft = artist.epk_draft if isinstance(artist.epk_draft, dict) else {}
    if draft:
        return draft
    return get_or_init_draft(artist)


def is_profile_published(artist: Artist) -> bool:
    cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    return bool(cfg.get("profile_published"))


def get_public_profile(db: Session, tenant_slug: str) -> dict[str, Any]:
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    cfg = coerce_epk_config(artist.epk_config)
    raw = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    published = is_profile_published(artist)
    design = _published_design(artist)

    base = {
        "tenant_slug": artist.tenant_slug,
        "display_name": artist.display_name,
        "tagline": cfg.tagline,
        "bio": cfg.bio,
        "booking_email": cfg.booking_email,
        "social": cfg.social,
        "sections": cfg.sections,
        "profile_published": published,
        "profile_published_at": raw.get("profile_published_at"),
        "mood": raw.get("profile_mood") or "",
    }

    if is_html_draft(design):
        return {
            **base,
            "format": "html_v1",
            "html": design.get("html"),
            "css": design.get("css"),
            "asset_bindings": design.get("asset_bindings") or {},
            "font_palette": design.get("font_palette"),
            "google_fonts_href": design.get("google_fonts_href"),
            "page_url": f"/artists/public/{tenant_slug}/page",
            "design": {},
            "site": {},
            "tracks": [],
            "photos": [],
        }

    preview = build_preview_payload(db, artist, design)
    return {
        **base,
        "format": "layout",
        "design": preview["design"],
        "site": preview["site"],
        "tracks": preview["tracks"],
        "photos": preview["photos"],
        "page_url": None,
    }


def render_public_profile_html(db: Session, tenant_slug: str) -> str:
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    if not is_profile_published(artist):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profile is not live yet.")

    design = _published_design(artist)
    if not is_html_draft(design):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Profile uses layout format.")
    return render_draft_html(db, artist, design)

"""EPK draft design document — separate from published epk_config."""

from __future__ import annotations

import copy
from typing import Any


def default_epk_design(display_name: str = "", tagline: str = "", bio: str = "") -> dict[str, Any]:
    """Structured layout JSON with stable block ids for annotation + LLM patches."""
    return {
        "template_id": "editorial",
        "theme": {"accent": "#c4a574", "background": "#faf9f6"},
        "layout": [
            {
                "id": "hero",
                "type": "hero",
                "headline": display_name or "Artist Name",
                "subhead": tagline or "",
            },
            {
                "id": "bio-main",
                "type": "bio",
                "body": bio or "",
            },
            {
                "id": "photos-1",
                "type": "photo_grid",
                "asset_ids": [],
            },
            {
                "id": "music-1",
                "type": "music",
                "asset_ids": [],
            },
            {
                "id": "contact-1",
                "type": "contact",
                "email": "",
            },
        ],
    }


def ensure_block_ids(design: dict[str, Any]) -> dict[str, Any]:
    """Guarantee every layout block has an id."""
    out = copy.deepcopy(design)
    layout = out.get("layout") or []
    for i, block in enumerate(layout):
        if not isinstance(block, dict):
            continue
        if not block.get("id"):
            block["id"] = f"{block.get('type', 'block')}-{i + 1}"
    out["layout"] = layout
    return out


def init_epk_draft_from_artist(epk_config: dict | None, display_name: str) -> dict[str, Any]:
    cfg = epk_config if isinstance(epk_config, dict) else {}
    design = default_epk_design(
        display_name=display_name,
        tagline=str(cfg.get("tagline") or ""),
        bio=str(cfg.get("bio") or ""),
    )
    contact = next((b for b in design["layout"] if b.get("id") == "contact-1"), None)
    if contact is not None:
        contact["email"] = str(cfg.get("booking_email") or "")
    return design


def get_or_init_draft(artist) -> dict[str, Any]:
    raw = getattr(artist, "epk_draft", None)
    if isinstance(raw, dict) and raw.get("layout"):
        return ensure_block_ids(raw)
    return init_epk_draft_from_artist(artist.epk_config, artist.display_name)


def design_to_site_context(epk_config: dict | None, display_name: str) -> dict[str, Any]:
    cfg = epk_config if isinstance(epk_config, dict) else {}
    return {
        "display_name": display_name,
        "tagline": str(cfg.get("tagline") or ""),
        "bio": str(cfg.get("bio") or ""),
        "booking_email": str(cfg.get("booking_email") or ""),
        "sections": cfg.get("sections") or {"music": True, "photos": True, "bio": True},
    }

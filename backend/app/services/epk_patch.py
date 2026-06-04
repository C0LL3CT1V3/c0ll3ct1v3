"""Apply LLM design patches to epk_draft documents."""

from __future__ import annotations

import copy
from typing import Any


def _merge_block(existing: dict, patch: dict) -> dict:
    out = copy.deepcopy(existing)
    for key, val in patch.items():
        if key == "id":
            continue
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **val}
        else:
            out[key] = val
    return out


def apply_design_patch(draft: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Merge patch into draft: theme, template_id, layout blocks by id, site fields."""
    out = copy.deepcopy(draft)
    if not patch:
        return out

    if patch.get("template_id"):
        out["template_id"] = patch["template_id"]

    if isinstance(patch.get("theme"), dict):
        out["theme"] = {**(out.get("theme") or {}), **patch["theme"]}

    layout_patches = patch.get("layout") or []
    if layout_patches:
        layout = list(out.get("layout") or [])
        by_id = {b.get("id"): i for i, b in enumerate(layout) if b.get("id")}
        for bp in layout_patches:
            if not isinstance(bp, dict):
                continue
            bid = bp.get("id")
            if bid and bid in by_id:
                layout[by_id[bid]] = _merge_block(layout[by_id[bid]], bp)
            elif bid:
                layout.append(bp)
        out["layout"] = layout

    site_patch = patch.get("site")
    if isinstance(site_patch, dict):
        out.setdefault("_site_patch", {})
        out["_site_patch"] = {**(out.get("_site_patch") or {}), **site_patch}

    return out


def site_from_draft_and_config(draft: dict, epk_config: dict, display_name: str) -> dict[str, Any]:
    """Build site props for EpkRenderer from draft site patch + epk_config."""
    cfg = epk_config if isinstance(epk_config, dict) else {}
    site_patch = draft.get("_site_patch") or {}
    return {
        "display_name": site_patch.get("display_name") or display_name,
        "tagline": site_patch.get("tagline") if "tagline" in site_patch else str(cfg.get("tagline") or ""),
        "bio": site_patch.get("bio") if "bio" in site_patch else str(cfg.get("bio") or ""),
        "booking_email": site_patch.get("booking_email")
        if "booking_email" in site_patch
        else str(cfg.get("booking_email") or ""),
        "sections": cfg.get("sections") or {"music": True, "photos": True, "bio": True},
    }

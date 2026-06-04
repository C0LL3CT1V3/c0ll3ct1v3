"""Map EPK layout blocks to editable props for annotation → LLM refinement."""

from __future__ import annotations

from typing import Any

COMPONENT_PROP_PATHS: dict[str, list[str]] = {
    "hero": ["headline", "subhead"],
    "bio": ["body"],
    "photo_grid": ["asset_ids"],
    "music": ["asset_ids"],
    "contact": ["email"],
}

THEME_PROP_PATHS = ["accent", "background"]


def get_component_map(design: dict[str, Any]) -> list[dict[str, Any]]:
    """Registry metadata for overlay UI."""
    items: list[dict[str, Any]] = []
    for block in design.get("layout") or []:
        if not isinstance(block, dict):
            continue
        btype = block.get("type") or "unknown"
        bid = block.get("id")
        if not bid:
            continue
        items.append(
            {
                "component_id": bid,
                "type": btype,
                "prop_paths": list(COMPONENT_PROP_PATHS.get(btype, [])),
                "label": f"{btype.replace('_', ' ').title()} ({bid})",
            }
        )
    items.append(
        {
            "component_id": "_theme",
            "type": "theme",
            "prop_paths": THEME_PROP_PATHS,
            "label": "Theme colors",
        }
    )
    return items


def _valid_ids(design: dict[str, Any]) -> set[str]:
    ids = {b.get("id") for b in (design.get("layout") or []) if isinstance(b, dict) and b.get("id")}
    ids.add("_theme")
    return ids


def resolve_annotations(
    design: dict[str, Any],
    raw_annotations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate client hits + attach prop_paths for LLM."""
    valid = _valid_ids(design)
    resolved: list[dict[str, Any]] = []
    for ann in raw_annotations or []:
        if not isinstance(ann, dict):
            continue
        note = str(ann.get("note") or "").strip()
        bbox = ann.get("bbox_norm") or ann.get("bbox")
        hits = ann.get("component_ids") or ann.get("component_hits") or []
        if not hits and ann.get("component_id"):
            hits = [ann["component_id"]]

        for cid in hits:
            cid = str(cid)
            if cid not in valid:
                continue
            if cid == "_theme":
                btype = "theme"
                paths = THEME_PROP_PATHS
            else:
                block = next((b for b in design.get("layout") or [] if b.get("id") == cid), {})
                btype = block.get("type") or "unknown"
                paths = COMPONENT_PROP_PATHS.get(btype, [])
            resolved.append(
                {
                    "component_id": cid,
                    "type": btype,
                    "prop_paths": paths,
                    "note": note,
                    "bbox_norm": bbox,
                }
            )
        if not hits and note:
            resolved.append(
                {
                    "component_id": None,
                    "type": "general",
                    "prop_paths": [],
                    "note": note,
                    "bbox_norm": bbox,
                }
            )
    return resolved

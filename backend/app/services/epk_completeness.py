"""Musician profile readiness — MySpace-style page completeness."""

from __future__ import annotations

import re
from typing import Any, Literal

from sqlalchemy.orm import Session

from ..models.artist import Artist
from ..models.media import MediaAsset
from ..schemas.artist_schemas import coerce_epk_config
from .epk_draft import get_or_init_draft
from .epk_html_draft import is_html_draft

Status = Literal["missing", "partial", "ready"]
Priority = Literal["required", "recommended", "optional"]

_ITEM = dict[str, Any]


def _status_rank(status: Status) -> float:
    return {"missing": 0.0, "partial": 0.5, "ready": 1.0}[status]


def _workbench_inventory(db: Session, tenant_slug: str) -> dict[str, Any]:
    rows = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.is_deleted.is_(False),
            MediaAsset.storage_region == "workbench",
        )
        .all()
    )
    by_type: dict[str, int] = {}
    by_id: dict[str, MediaAsset] = {}
    for row in rows:
        by_type[row.asset_type] = by_type.get(row.asset_type, 0) + 1
        by_id[row.id] = row
    return {
        "total": len(rows),
        "by_type": by_type,
        "audio": by_type.get("audio", 0),
        "image": by_type.get("image", 0),
        "video": by_type.get("video", 0),
        "by_id": by_id,
    }


def _bound_asset_types(draft: dict, inventory: dict[str, Any]) -> dict[str, int]:
    counts = {"audio": 0, "image": 0, "video": 0}
    by_id: dict[str, MediaAsset] = inventory.get("by_id") or {}
    for asset_id in (draft.get("asset_bindings") or {}).values():
        asset = by_id.get(str(asset_id))
        if asset and asset.asset_type in counts:
            counts[asset.asset_type] += 1
    for block in draft.get("layout") or []:
        if not isinstance(block, dict):
            continue
        for asset_id in block.get("asset_ids") or []:
            asset = by_id.get(str(asset_id))
            if asset and asset.asset_type in counts:
                counts[asset.asset_type] += 1
    return counts


def _html_blob(draft: dict) -> str:
    return f"{draft.get('html') or ''}\n{draft.get('css') or ''}".lower()


def _bio_text(draft: dict, cfg) -> str:
    if is_html_draft(draft):
        return _html_blob(draft)
    bio_block = next(
        (b for b in draft.get("layout") or [] if isinstance(b, dict) and b.get("id") == "bio-main"),
        None,
    )
    parts = [cfg.bio or ""]
    if bio_block and bio_block.get("body"):
        parts.append(str(bio_block["body"]))
    return "\n".join(parts).strip()


def _social_links(cfg, draft: dict) -> dict[str, str]:
    links = dict(cfg.social or {})
    if is_html_draft(draft):
        html = _html_blob(draft)
        for key, pat in (
            ("spotify", r"open\.spotify\.com"),
            ("instagram", r"instagram\.com"),
            ("tiktok", r"tiktok\.com"),
            ("soundcloud", r"soundcloud\.com"),
            ("youtube", r"youtube\.com|youtu\.be"),
        ):
            if re.search(pat, html, re.I):
                links.setdefault(key, "in_page")
    return {k: v for k, v in links.items() if v}


def _item(
    *,
    id: str,
    category: str,
    label: str,
    status: Status,
    priority: Priority,
    detail: str,
    suggestion: str,
) -> _ITEM:
    return {
        "id": id,
        "category": category,
        "label": label,
        "status": status,
        "priority": priority,
        "detail": detail,
        "suggestion": suggestion,
    }


def evaluate_epk_completeness(db: Session, artist: Artist) -> dict[str, Any]:
    """Profile readiness for a fan-facing musician page."""
    cfg = coerce_epk_config(artist.epk_config)
    draft = artist.epk_draft if isinstance(artist.epk_draft, dict) else get_or_init_draft(artist)
    inventory = _workbench_inventory(db, artist.tenant_slug)
    bound = _bound_asset_types(draft, inventory)
    audio_count = max(inventory["audio"], bound["audio"])
    image_count = max(inventory["image"], bound["image"])
    video_count = max(inventory["video"], bound["video"])
    bio_len = len(_bio_text(draft, cfg))
    social = _social_links(cfg, draft)
    raw_cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    published = bool(raw_cfg.get("profile_published"))
    custom_page = is_html_draft(draft) or bool((draft.get("theme") or {}).get("accent"))

    items: list[_ITEM] = []

    if custom_page and (is_html_draft(draft) or draft.get("layout")):
        page_status: Status = "ready"
    elif draft.get("layout"):
        page_status = "partial"
    else:
        page_status = "missing"
    items.append(
        _item(
            id="custom_page",
            category="vibe",
            label="Custom page — your look, your HTML/CSS",
            status=page_status,
            priority="required",
            detail="html_v1 custom page" if is_html_draft(draft) else "Template layout draft.",
            suggestion=(
                "Pick a vision, write a vibe spec, and hit Build profile — MySpace was all about "
                "making the page yours."
            ),
        )
    )

    if audio_count >= 2:
        music_status: Status = "ready"
    elif audio_count >= 1:
        music_status = "partial"
    else:
        music_status = "missing"
    items.append(
        _item(
            id="music_tracks",
            category="sound",
            label="Music — tracks fans can play right on your page",
            status=music_status,
            priority="required",
            detail=f"{audio_count} track(s) ready.",
            suggestion="Upload your best 2–3 tracks to the workbench and bind them on your profile page.",
        )
    )

    if bio_len >= 120:
        bio_status: Status = "ready"
    elif bio_len >= 40:
        bio_status = "partial"
    else:
        bio_status = "missing"
    items.append(
        _item(
            id="bio",
            category="about",
            label="About you — who you are in a few lines",
            status=bio_status,
            priority="required",
            detail=f"~{bio_len} characters of about/copy.",
            suggestion="Write a short about blurb — first person is fine on MySpace. Tell fans your vibe.",
        )
    )

    if image_count >= 4:
        photo_status: Status = "ready"
    elif image_count >= 1:
        photo_status = "partial"
    else:
        photo_status = "missing"
    items.append(
        _item(
            id="photos",
            category="look",
            label="Photo wall — live shots, press, friends",
            status=photo_status,
            priority="required",
            detail=f"{image_count} image(s) in library.",
            suggestion="Add photos to your vision media zone — the wall is half the personality.",
        )
    )

    video_status: Status = "ready" if video_count >= 1 else "missing"
    items.append(
        _item(
            id="video",
            category="look",
            label="Video — live clip or visualizer",
            status=video_status,
            priority="recommended",
            detail=f"{video_count} video(s)." if video_count else "No video yet.",
            suggestion="Drop a live clip or music video into workbench — motion grabs scrollers.",
        )
    )

    streaming = {"spotify", "soundcloud", "bandcamp", "youtube"} & {k.lower() for k in social}
    social_keys = {k.lower() for k in social}
    has_social = bool({"instagram", "tiktok", "twitter"} & social_keys)
    if streaming and has_social:
        link_status: Status = "ready"
    elif streaming or has_social:
        link_status = "partial"
    else:
        link_status = "missing"
    items.append(
        _item(
            id="social_streaming",
            category="connect",
            label="Social + streaming links",
            status=link_status,
            priority="required",
            detail=f"Links: {', '.join(sorted(social_keys)) or 'none'}.",
            suggestion="Add Spotify/SoundCloud and Instagram/TikTok in profile settings or on your page.",
        )
    )

    items.append(
        _item(
            id="go_live",
            category="connect",
            label="Go live — publish your page to your subdomain",
            status="ready" if published else "missing",
            priority="required",
            detail=f"{artist.tenant_slug}.your-domain" if published else "Draft only — not public yet.",
            suggestion="When you're happy with the preview, hit Go live so fans can visit your URL.",
        )
    )

    required = [i for i in items if i["priority"] == "required"]
    required_score = sum(_status_rank(i["status"]) for i in required) / max(len(required), 1)
    overall_score = sum(_status_rank(i["status"]) for i in items) / max(len(items), 1)
    gaps = [i for i in items if i["status"] != "ready"]

    return {
        "score": round(overall_score, 2),
        "required_score": round(required_score, 2),
        "items": items,
        "gaps": gaps,
        "gap_ids": [i["id"] for i in gaps],
        "summary": _build_summary(required, gaps, published),
        "agent_brief": _build_agent_brief(gaps),
        "inventory": {
            "audio": audio_count,
            "images": image_count,
            "video": video_count,
            "workbench_total": inventory["total"],
        },
    }


def _build_summary(required: list[_ITEM], gaps: list[_ITEM], published: bool) -> str:
    ready_req = sum(1 for i in required if i["status"] == "ready")
    if not gaps and published:
        return "Your musician page is live and looking complete."
    if not published:
        return "Build your page, then Go live on your subdomain when you're ready."
    missing_req = [i for i in required if i["status"] == "missing"]
    if missing_req:
        labels = ", ".join(i["label"].split(" — ")[0] for i in missing_req[:3])
        return f"Page is live — still missing: {labels}."
    return f"Good momentum ({ready_req}/{len(required)} essentials). Keep customizing."


def _build_agent_brief(gaps: list[_ITEM]) -> str:
    if not gaps:
        return "Profile readiness: page looks solid. Help with customization, vibe, or going live."
    lines = ["Profile gaps — suggest fun, concrete next steps (MySpace vibe, not corporate EPK):"]
    for item in gaps[:8]:
        lines.append(f"- [{item['status']}] {item['label']}: {item['suggestion']}")
    return "\n".join(lines)


def completeness_context_block(db: Session, artist: Artist) -> str:
    report = evaluate_epk_completeness(db, artist)
    lines = [
        "## Musician profile readiness",
        f"Score: {int(report['required_score'] * 100)}% essentials · {report['summary']}",
        f"Media library: {report['inventory']['audio']} tracks, "
        f"{report['inventory']['images']} photos, {report['inventory']['video']} videos",
    ]
    for item in report["gaps"][:6]:
        lines.append(f"- {item['label']} ({item['status']}): {item['suggestion']}")
    return "\n".join(lines)

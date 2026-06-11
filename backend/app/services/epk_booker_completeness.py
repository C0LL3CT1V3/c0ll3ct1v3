"""Booker EPK readiness checklist — separate from fan profile completeness."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from ..models.artist import Artist
from ..schemas.artist_schemas import coerce_epk_config
from .epk_public_config import coerce_epk_public, get_epk_public_raw

Status = Literal["missing", "partial", "ready"]
Priority = Literal["required", "recommended", "optional"]
_ITEM = dict[str, Any]


def _status_rank(status: Status) -> float:
    return {"missing": 0.0, "partial": 0.5, "ready": 1.0}[status]


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


def evaluate_booker_completeness(db: Session, artist: Artist) -> dict[str, Any]:
    """Press-kit readiness for bookers — structured EPK slots."""
    cfg = coerce_epk_config(artist.epk_config)
    epk = coerce_epk_public(get_epk_public_raw(artist))
    raw = artist.epk_config if isinstance(artist.epk_config, dict) else {}

    items: list[_ITEM] = []

    has_hero = bool(
        (epk.hero_video.type == "youtube" and epk.hero_video.url.strip())
        or (epk.hero_video.type == "asset" and epk.hero_video.asset_id)
    )
    items.append(
        _item(
            id="hero_video",
            category="media",
            label="Hero video — live clip or official visual",
            status="ready" if has_hero else "missing",
            priority="required",
            detail="YouTube embed or workbench video asset.",
            suggestion="Drag a live clip video from Vault or paste a YouTube URL.",
        )
    )

    photo_count = len(epk.photos)
    if photo_count >= 3:
        photo_status: Status = "ready"
    elif photo_count >= 1:
        photo_status = "partial"
    else:
        photo_status = "missing"
    items.append(
        _item(
            id="press_photos",
            category="media",
            label="Press photos — 3–6 high-res shots",
            status=photo_status,
            priority="required",
            detail=f"{photo_count} photo(s) in EPK slots.",
            suggestion="Drag 3–6 press photos from Vault into the EPK photo grid.",
        )
    )

    bio_len = len((epk.bio or cfg.bio or "").strip())
    if bio_len >= 200:
        bio_status: Status = "ready"
    elif bio_len >= 80:
        bio_status = "partial"
    else:
        bio_status = "missing"
    items.append(
        _item(
            id="bio",
            category="copy",
            label="Bio — short and booker-ready",
            status=bio_status,
            priority="required",
            detail=f"~{bio_len} characters.",
            suggestion="Write 2–3 paragraphs: sound, scene, notable shows, and what makes you bookable.",
        )
    )

    booking = (epk.booking_email or cfg.booking_email or "").strip()
    items.append(
        _item(
            id="booking_email",
            category="contact",
            label="Booking email",
            status="ready" if booking else "missing",
            priority="required",
            detail=booking or "No booking contact set.",
            suggestion="Add the email bookers should use — manager or direct.",
        )
    )

    audio_count = len(epk.audio_samples)
    items.append(
        _item(
            id="audio_samples",
            category="sound",
            label="Audio samples — 2–3 best tracks",
            status="ready" if audio_count >= 2 else ("partial" if audio_count == 1 else "missing"),
            priority="required",
            detail=f"{audio_count} track(s) linked.",
            suggestion="Drag your best 2–3 tracks from Vault into audio sample slots.",
        )
    )

    social = epk.social or cfg.social or {}
    has_streaming = bool({"spotify", "soundcloud", "bandcamp", "youtube"} & {k.lower() for k in social})
    has_social = bool({"instagram", "tiktok", "twitter"} & {k.lower() for k in social})
    if has_streaming and has_social:
        social_status: Status = "ready"
    elif has_streaming or has_social:
        social_status = "partial"
    else:
        social_status = "missing"
    items.append(
        _item(
            id="social_links",
            category="connect",
            label="Social + streaming links",
            status=social_status,
            priority="required",
            detail=f"Links: {', '.join(sorted(social.keys())) or 'none'}.",
            suggestion="Add Spotify and Instagram at minimum so bookers can dig deeper.",
        )
    )

    has_rider = bool(epk.tech_rider and epk.tech_rider.asset_id)
    items.append(
        _item(
            id="tech_rider",
            category="logistics",
            label="Tech rider (optional)",
            status="ready" if has_rider else "missing",
            priority="optional",
            detail="PDF or doc in Vault." if has_rider else "No rider attached.",
            suggestion="Upload a one-page tech rider PDF to Vault and slot it here.",
        )
    )

    published = bool(epk.published or raw.get("epk_public_published"))
    items.append(
        _item(
            id="publish_epk",
            category="deliver",
            label="Publish EPK — one-click booker page",
            status="ready" if published else "missing",
            priority="required",
            detail="Live at /epk on your subdomain." if published else "Draft only.",
            suggestion="When slots look good, publish so bookers get a stable URL.",
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
    }


def _build_summary(required: list[_ITEM], gaps: list[_ITEM], published: bool) -> str:
    if not gaps and published:
        return "EPK is published and booker-ready."
    if not published:
        return "Fill the EPK slots, then publish for a one-click booker URL."
    missing_req = [i for i in required if i["status"] == "missing"]
    if missing_req:
        labels = ", ".join(i["label"].split(" — ")[0] for i in missing_req[:3])
        return f"EPK draft — still missing: {labels}."
    return "Almost there — polish remaining slots and publish."


def _build_agent_brief(gaps: list[_ITEM]) -> str:
    if not gaps:
        return "Booker EPK looks complete."
    lines = ["Booker EPK gaps:"]
    for item in gaps[:8]:
        lines.append(f"- [{item['status']}] {item['label']}: {item['suggestion']}")
    return "\n".join(lines)

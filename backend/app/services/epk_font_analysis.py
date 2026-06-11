"""Detect typography from vision reference images and build Google Fonts links."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote_plus

from ..config import settings

_GOOGLE_FONTS_CSS_PREFIX = "https://fonts.googleapis.com/css2?"
_MAX_HREF_LEN = 2048
_FAMILY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+ _-]{0,80}$")


def _prompt_path(name: str):
    from pathlib import Path

    return Path(__file__).resolve().parent.parent / "prompts" / name


def load_font_detect_template() -> str:
    path = _prompt_path("manager_epk_font_detect.md")
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "Return JSON with heading, body, optional accent Google Font matches."


def stub_font_palette(*, notes: str = "Default typography (stub mode).") -> dict[str, Any]:
    return {
        "heading": {
            "family": "Playfair Display",
            "google_fonts_family": "Playfair+Display",
            "weights": ["700"],
            "category": "serif",
            "confidence": 0.4,
        },
        "body": {
            "family": "Inter",
            "google_fonts_family": "Inter",
            "weights": ["400", "600"],
            "category": "sans-serif",
            "confidence": 0.4,
        },
        "accent": None,
        "notes": notes,
        "source": "stub",
    }


def _slug_for_family(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        return ""
    if "+" in cleaned and " " not in cleaned:
        return cleaned
    return quote_plus(cleaned)


def _normalize_font_slot(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    family = (raw.get("family") or "").strip()
    slug = (raw.get("google_fonts_family") or "").strip() or _slug_for_family(family)
    if not family or not slug or not _FAMILY_RE.match(slug.replace("+", " ")):
        return None
    weights_raw = raw.get("weights") or ["400"]
    weights = [str(w).strip() for w in weights_raw if str(w).strip() in {"100", "200", "300", "400", "500", "600", "700", "800", "900"}]
    if not weights:
        weights = ["400"]
    try:
        confidence = float(raw.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))
    return {
        "family": family[:80],
        "google_fonts_family": slug[:96],
        "weights": weights[:4],
        "category": (raw.get("category") or "sans-serif")[:32],
        "confidence": confidence,
    }


def normalize_font_palette(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return stub_font_palette(notes="Invalid font palette; using defaults.")
    heading = _normalize_font_slot(raw.get("heading"))
    body = _normalize_font_slot(raw.get("body"))
    accent = _normalize_font_slot(raw.get("accent"))
    if not heading and not body:
        return stub_font_palette(notes="Could not parse detected fonts; using defaults.")
    palette: dict[str, Any] = {
        "heading": heading or body,
        "body": body or heading,
        "accent": accent,
        "notes": (raw.get("notes") or "")[:500],
        "source": raw.get("source") or "detected",
    }
    return palette


def build_google_fonts_href(font_palette: dict[str, Any] | None) -> str | None:
    if not isinstance(font_palette, dict):
        return None
    params: list[str] = []
    seen: set[str] = set()
    for role in ("heading", "body", "accent"):
        slot = font_palette.get(role)
        if not isinstance(slot, dict):
            continue
        slug = slot.get("google_fonts_family")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        weights = slot.get("weights") or ["400"]
        weight_str = ";".join(weights)
        params.append(f"family={slug}:wght@{weight_str}")
    if not params:
        return None
    href = _GOOGLE_FONTS_CSS_PREFIX + "&".join(params) + "&display=swap"
    if len(href) > _MAX_HREF_LEN:
        return None
    return href


def sanitize_google_fonts_href(href: str | None) -> str | None:
    if not href:
        return None
    text = href.strip()
    if not text.startswith(_GOOGLE_FONTS_CSS_PREFIX):
        return None
    if len(text) > _MAX_HREF_LEN:
        return None
    if any(bad in text.lower() for bad in ("javascript:", "data:", "@import")):
        return None
    return text


def css_font_stack(font_palette: dict[str, Any] | None) -> dict[str, str]:
    """Suggested font-family values for generator prompt."""
    palette = font_palette if isinstance(font_palette, dict) else {}
    stacks: dict[str, str] = {}
    for role, fallback in (("heading", "Georgia, serif"), ("body", "system-ui, sans-serif"), ("accent", "inherit")):
        slot = palette.get(role)
        if isinstance(slot, dict) and slot.get("family"):
            category = slot.get("category") or "sans-serif"
            stacks[role] = f"'{slot['family']}', {category}"
        elif role != "accent":
            stacks[role] = fallback
    return stacks


def _vision_pack_image_urls(pack: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    wf = pack.get("wireframe")
    if isinstance(wf, dict) and wf.get("preview_url"):
        urls.append(wf["preview_url"])
    for ref in pack.get("references") or []:
        if isinstance(ref, dict) and ref.get("preview_url"):
            urls.append(ref["preview_url"])
    return urls[:4]


def detect_fonts_from_vision_pack(vision_pack: dict[str, Any]) -> dict[str, Any]:
    """Vision-model pass over reference images → Google Fonts palette."""
    image_urls = _vision_pack_image_urls(vision_pack)
    if not image_urls:
        return stub_font_palette(notes="Add reference images to detect typography.")

    from .manager_llm import _call_llm_json_any, manager_llm_configured

    if not manager_llm_configured() or not (settings.openrouter_api_key or "").strip():
        return stub_font_palette(notes="Stub fonts — set OPENROUTER_API_KEY for vision detection.")

    template = load_font_detect_template()
    text = (
        "Infer typography from the attached reference images.\n\n"
        f"Vision pack metadata:\n{json.dumps(vision_pack, indent=2)}"
    )
    user_content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for url in image_urls:
        user_content.append({"type": "image_url", "image_url": {"url": url}})

    parsed = _call_llm_json_any(
        template,
        user_content,
        json_mode=True,
        model=settings.manager_vision_model,
        max_tokens=900,
    )
    if parsed.get("heading") or parsed.get("body"):
        parsed["source"] = "detected"
        return normalize_font_palette(parsed)
    return stub_font_palette(notes="Font detection unavailable; using defaults.")

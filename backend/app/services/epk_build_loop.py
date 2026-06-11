"""Orchestrate html_v1 EPK build: generate → Playwright screenshot → vision critique → optional revise."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..models.artist import Artist
from ..models.manager import EpkIteration, ManagerThread
from ..services.epk_html_draft import (
    HTML_FORMAT,
    draft_content_hash,
    normalize_html_draft,
)
from ..services.epk_completeness import evaluate_epk_completeness
from ..services.epk_font_analysis import detect_fonts_from_vision_pack
from ..services.epk_playwright import capture_sim_screenshot
from ..services.epk_sim_token import sim_render_url
from ..services.manager_epk_service import (
    _screenshot_presign,
    append_message,
    save_draft,
)
from ..services.manager_llm import build_system_prompt, critique_epk_screenshot, generate_epk_html
from ..services.spaces_storage import get_s3_client
from ..services.vision_pack import get_vision_pack


def _upload_screenshot(tenant_slug: str, iteration_id: str, png: bytes) -> str | None:
    if not settings.spaces_enabled or not png:
        return None
    key = f"tenants/{tenant_slug}/manager/iterations/{iteration_id}.png"
    try:
        client = get_s3_client()
        client.put_object(
            Bucket=settings.spaces_bucket,
            Key=key,
            Body=png,
            ContentType="image/png",
        )
        return key
    except Exception:
        return None


def build_epk_from_vision(
    db: Session,
    artist: Artist,
    thread: ManagerThread,
    *,
    vision_id: str,
    spec: str,
) -> dict[str, Any]:
    pack = get_vision_pack(db, vision_id, artist.tenant_slug)
    font_palette = detect_fonts_from_vision_pack(pack)
    epk_readiness = evaluate_epk_completeness(db, artist)
    pack["font_palette"] = font_palette
    pack["epk_readiness"] = {
        "required_score": epk_readiness.get("required_score"),
        "summary": epk_readiness.get("summary"),
        "gaps": epk_readiness.get("gaps"),
        "inventory": epk_readiness.get("inventory"),
    }
    thread.vision_id = vision_id
    db.commit()

    epk = artist.epk_config or {}
    system = build_system_prompt(
        artist.display_name,
        epk,
        artist.manager_system_prompt,
        prompt_role="patch",
    )

    max_cycles = max(1, min(settings.epk_build_max_revisions, 2))
    critique_notes: str | None = None
    last_critique: dict[str, Any] = {}
    screenshot_key: str | None = None
    screenshot_png: bytes | None = None
    reasoning_summary = ""
    draft: dict[str, Any] = {}
    cycles_run = 0

    for cycle in range(max_cycles):
        cycles_run = cycle + 1
        generated = generate_epk_html(
            system,
            spec=spec,
            vision_pack=pack,
            artist_name=artist.display_name,
            critique_notes=critique_notes,
            font_palette=font_palette,
        )
        draft = normalize_html_draft(
            html=generated.get("html") or "",
            css=generated.get("css") or "",
            asset_bindings=generated.get("asset_bindings") or {},
            vision_id=vision_id,
            spec_snapshot=spec,
            font_palette=font_palette,
        )
        save_draft(db, artist, draft)
        reasoning_summary = generated.get("reasoning_summary") or "Built EPK preview."

        sim_url = sim_render_url(artist_id=artist.id, draft_hash=draft_content_hash(draft))
        screenshot_png = capture_sim_screenshot(sim_url)
        last_critique = critique_epk_screenshot(
            spec=spec,
            vision_pack=pack,
            screenshot_png=screenshot_png,
        )

        should_revise = bool(last_critique.get("should_revise")) and bool(last_critique.get("major_gaps"))
        if should_revise and cycle + 1 < max_cycles:
            critique_notes = json.dumps(
                {
                    "major_gaps": last_critique.get("major_gaps") or [],
                    "minor_gaps": last_critique.get("minor_gaps") or [],
                    "critique_summary": last_critique.get("critique_summary"),
                },
                indent=2,
            )
            continue
        break

    iteration = EpkIteration(
        artist_id=artist.id,
        thread_id=thread.id,
        step="generate",
        user_prompt=spec,
        context_snapshot={
            "vision_pack": pack,
            "font_palette": font_palette,
            "spec": spec,
            "critique": last_critique,
            "revision_cycles": cycles_run,
            "format": HTML_FORMAT,
        },
        model_reasoning=critique_notes,
        reasoning_summary=reasoning_summary,
        design_patch={"format": HTML_FORMAT},
        design_after=draft,
        consent_for_training=bool(artist.allow_training_contribution),
    )
    db.add(iteration)
    db.commit()
    db.refresh(iteration)

    if screenshot_png:
        screenshot_key = _upload_screenshot(artist.tenant_slug, iteration.id, screenshot_png)
        if screenshot_key:
            iteration.screenshot_storage_key = screenshot_key
            db.commit()

    render_url = sim_render_url(
        artist_id=artist.id,
        draft_hash=draft_content_hash(draft),
        iteration_id=iteration.id,
    )
    append_message(db, thread, "user", spec, metadata={"type": "epk_build", "vision_id": vision_id})
    assistant_text = reasoning_summary
    if last_critique.get("critique_summary"):
        assistant_text = f"{reasoning_summary}\n\n{last_critique.get('critique_summary')}"
    append_message(
        db,
        thread,
        "assistant",
        assistant_text,
        metadata={
            "type": "epk_build",
            "iteration_id": iteration.id,
            "match_score": last_critique.get("match_score"),
            "revision_cycles": cycles_run,
        },
    )

    return {
        "iteration_id": iteration.id,
        "thread_id": thread.id,
        "reasoning_summary": reasoning_summary,
        "critique_summary": last_critique.get("critique_summary"),
        "match_score": last_critique.get("match_score"),
        "revision_cycles": cycles_run,
        "format": HTML_FORMAT,
        "html": draft.get("html"),
        "css": draft.get("css"),
        "asset_bindings": draft.get("asset_bindings") or {},
        "vision_id": vision_id,
        "spec_snapshot": spec,
        "font_palette": font_palette,
        "google_fonts_href": draft.get("google_fonts_href"),
        "sim_render_url": render_url,
        "screenshot_storage_key": screenshot_key,
        "design": {},
        "site": {},
        "tracks": [],
        "photos": [],
    }

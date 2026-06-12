"""Manager EPK builder and thread business logic."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models.artist import Artist
from ..models.manager import EpkIteration, ManagerMessage, ManagerThread
from ..models.media import MediaAsset, MediaVersion
from ..services.artist_service import storage_namespace_for_artist
from ..services.epk_completeness import completeness_context_block, evaluate_epk_completeness
from ..services.epk_component_registry import get_component_map, resolve_annotations
from ..services.epk_draft import get_or_init_draft
from ..services.epk_html_draft import (
    draft_content_hash,
    is_html_draft,
    normalize_html_draft,
    resolve_binding_urls,
)
from ..services.epk_sim_token import sim_render_url
from ..services.epk_patch import apply_design_patch, site_from_draft_and_config as build_site
from ..services.manager_agent import ManagerTurnResult, run_manager_turn
from ..services.manager_llm import (
    build_system_prompt,
    generate_epk_patch,
    refine_epk_from_annotations,
    refine_epk_html_from_annotations,
)
from ..services.media_variants import best_image_variant, url_for_variant
from ..services.spaces_storage import get_s3_client, presigned_get_object, presigned_put_object


def _iteration_storage_key(tenant_slug: str, iteration_id: str) -> str:
    return f"tenants/{tenant_slug}/manager/iterations/{iteration_id}.png"


def _screenshot_presign(tenant_slug: str, iteration_id: str) -> tuple[str | None, str | None]:
    if not settings.spaces_enabled:
        return None, None
    key = _iteration_storage_key(tenant_slug, iteration_id)
    try:
        client = get_s3_client()
        url = presigned_put_object(client, key, "image/png")
        return url, key
    except RuntimeError:
        return None, None


def _screenshot_get_url(storage_key: str | None) -> str | None:
    if not settings.spaces_enabled or not storage_key:
        return None
    try:
        client = get_s3_client()
        return presigned_get_object(client, storage_key)
    except RuntimeError:
        return None


def _iteration_format(row: EpkIteration) -> str:
    ctx = row.context_snapshot if isinstance(row.context_snapshot, dict) else {}
    design = row.design_after if isinstance(row.design_after, dict) else {}
    if ctx.get("format") == "html_v1" or design.get("format") == "html_v1":
        return "html_v1"
    return "layout"


def _get_iteration_row(db: Session, artist: Artist, iteration_id: str) -> EpkIteration:
    row = (
        db.query(EpkIteration)
        .filter(EpkIteration.id == iteration_id, EpkIteration.artist_id == artist.id)
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Iteration not found.")
    return row


def _iteration_summary(row: EpkIteration, artist: Artist) -> dict[str, Any]:
    ctx = row.context_snapshot if isinstance(row.context_snapshot, dict) else {}
    design = row.design_after if isinstance(row.design_after, dict) else {}
    fmt = _iteration_format(row)
    is_seed = row.step == "generate" and not row.parent_iteration_id
    return {
        "id": row.id,
        "step": row.step,
        "format": fmt,
        "is_seed": is_seed,
        "user_prompt": row.user_prompt,
        "reasoning_summary": row.reasoning_summary,
        "vision_id": design.get("vision_id") or ctx.get("vision_pack", {}).get("vision_id"),
        "spec_snapshot": design.get("spec_snapshot") or ctx.get("spec"),
        "match_score": ctx.get("critique", {}).get("match_score"),
        "revision_cycles": ctx.get("revision_cycles"),
        "artist_accepted": row.artist_accepted,
        "parent_iteration_id": row.parent_iteration_id,
        "screenshot_url": _screenshot_get_url(row.screenshot_storage_key),
        "created_at": row.created_at,
    }


def build_iteration_preview(db: Session, artist: Artist, row: EpkIteration) -> dict[str, Any]:
    design = row.design_after if isinstance(row.design_after, dict) else {}
    fmt = _iteration_format(row)
    summary = _iteration_summary(row, artist)
    if fmt == "html_v1" and design:
        draft_hash = draft_content_hash(design)
        return {
            **summary,
            "format": "html_v1",
            "html": design.get("html"),
            "css": design.get("css"),
            "asset_bindings": design.get("asset_bindings") or {},
            "vision_id": design.get("vision_id"),
            "spec_snapshot": design.get("spec_snapshot"),
            "font_palette": design.get("font_palette"),
            "google_fonts_href": design.get("google_fonts_href"),
            "sim_render_url": sim_render_url(
                artist_id=artist.id,
                draft_hash=draft_hash,
                iteration_id=row.id,
            ),
            "design": {},
            "site": {},
            "tracks": [],
            "photos": [],
        }
    preview = build_preview_payload(db, artist, design or get_or_init_draft(artist))
    return {
        **summary,
        "format": "layout",
        **preview,
        "sim_render_url": None,
    }


def list_epk_iterations(db: Session, artist: Artist, *, limit: int = 40) -> list[dict[str, Any]]:
    rows = (
        db.query(EpkIteration)
        .filter(EpkIteration.artist_id == artist.id)
        .order_by(EpkIteration.created_at.desc(), EpkIteration.id.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [_iteration_summary(row, artist) for row in rows]


def get_epk_iteration_preview(db: Session, artist: Artist, iteration_id: str) -> dict[str, Any]:
    row = _get_iteration_row(db, artist, iteration_id)
    return build_iteration_preview(db, artist, row)


def restore_epk_iteration(db: Session, artist: Artist, iteration_id: str) -> dict[str, Any]:
    row = _get_iteration_row(db, artist, iteration_id)
    design = row.design_after
    if not isinstance(design, dict) or not design:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Iteration has no saved design.")
    save_draft(db, artist, design)
    return build_iteration_preview(db, artist, row)


def get_or_create_thread(
    db: Session,
    artist: Artist,
    mode: str,
    thread_id: str | None,
    vision_id: str | None = None,
) -> ManagerThread:
    if thread_id:
        row = (
            db.query(ManagerThread)
            .filter(ManagerThread.id == thread_id, ManagerThread.artist_id == artist.id)
            .first()
        )
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Thread not found.")
        if vision_id and row.vision_id != vision_id:
            row.vision_id = vision_id
            db.commit()
            db.refresh(row)
        return row
    row = ManagerThread(artist_id=artist.id, mode=mode, vision_id=vision_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_thread_messages(db: Session, thread_id: str, artist_id: int) -> list[ManagerMessage]:
    thread = (
        db.query(ManagerThread)
        .filter(ManagerThread.id == thread_id, ManagerThread.artist_id == artist_id)
        .first()
    )
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Thread not found.")
    return (
        db.query(ManagerMessage)
        .filter(ManagerMessage.thread_id == thread_id)
        .order_by(ManagerMessage.created_at.asc())
        .all()
    )


def append_message(
    db: Session,
    thread: ManagerThread,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> ManagerMessage:
    msg = ManagerMessage(
        thread_id=thread.id,
        role=role,
        content=content,
        metadata_json=metadata or {},
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def workbench_summary(db: Session, tenant_slug: str) -> dict[str, Any]:
    assets = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.is_deleted.is_(False),
            MediaAsset.storage_region == "workbench",
        )
        .order_by(MediaAsset.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "count": len(assets),
        "assets": [
            {
                "id": a.id,
                "title": a.title,
                "asset_type": a.asset_type,
            }
            for a in assets
        ],
    }


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


def build_preview_payload(db: Session, artist: Artist, design: dict) -> dict[str, Any]:
    site = build_site(design, artist.epk_config or {}, artist.display_name)
    tracks: list[dict] = []
    photos: list[dict] = []

    assets = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.tenant_slug == storage_namespace_for_artist(artist),
            MediaAsset.is_deleted.is_(False),
            MediaAsset.storage_region == "workbench",
        )
        .order_by(MediaAsset.created_at.desc())
        .limit(50)
        .all()
    )
    by_id = {a.id: a for a in assets}

    for block in design.get("layout") or []:
        if not isinstance(block, dict):
            continue
        ids = block.get("asset_ids") or []
        if block.get("type") == "music":
            for aid in ids:
                a = by_id.get(aid)
                if a and a.asset_type in ("audio", "video"):
                    tracks.append({"asset_id": a.id, "title": a.title, "mime_type": None, "url": None})
        if block.get("type") == "photo_grid":
            for aid in ids:
                a = by_id.get(aid)
                if a and a.asset_type == "image":
                    photos.append({"asset_id": a.id, "title": a.title, "mime_type": None, "url": None})

    if not tracks:
        tracks = [
            {
                "asset_id": a.id,
                "title": a.title,
                "mime_type": None,
                "url": _preview_url_for_asset(db, a) if a.asset_type in ("audio", "video") else None,
                "stream_url": _preview_url_for_asset(db, a) if a.asset_type in ("audio", "video") else None,
            }
            for a in assets
            if a.asset_type in ("audio", "video")
        ][:6]
    else:
        tracks = [
            {
                **t,
                "url": _preview_url_for_asset(db, by_id[t["asset_id"]])
                if t.get("asset_id") in by_id
                else t.get("url"),
                "stream_url": _preview_url_for_asset(db, by_id[t["asset_id"]])
                if t.get("asset_id") in by_id
                else t.get("stream_url") or t.get("url"),
            }
            for t in tracks
        ]
    if not photos:
        photos = [
            {
                "asset_id": a.id,
                "title": a.title,
                "mime_type": "image/jpeg",
                "url": _preview_url_for_asset(db, a),
            }
            for a in assets
            if a.asset_type == "image"
        ][:12]
    else:
        photos = [
            {
                **p,
                "url": _preview_url_for_asset(db, by_id[p["asset_id"]])
                if p.get("asset_id") in by_id
                else p.get("url"),
            }
            for p in photos
        ]

    return {
        "design": design,
        "site": site,
        "tracks": tracks,
        "photos": photos,
    }


def save_draft(db: Session, artist: Artist, design: dict) -> None:
    artist.epk_draft = design
    db.commit()


def build_agent_context_block(db: Session, artist: Artist) -> str:
    """Compact context for the chat agent (no new tools)."""
    draft = get_or_init_draft(artist)
    wb = workbench_summary(db, storage_namespace_for_artist(artist))
    components = get_component_map(draft)
    section_keys = [c.get("component_id") for c in components if c.get("component_id")]
    hero = next((b for b in draft.get("layout") or [] if b.get("id") == "hero"), {})
    lines = [
        "## Current context",
        f"Workbench assets: {wb.get('count', 0)}",
    ]
    titles = [a.get("title") for a in wb.get("assets") or [] if a.get("title")][:8]
    if titles:
        lines.append("Asset titles: " + ", ".join(titles))
    if section_keys:
        lines.append("Patchable EPK sections: " + ", ".join(section_keys))
    if hero.get("headline"):
        lines.append(f"Draft hero headline: {hero.get('headline')}")
    if hero.get("subhead"):
        lines.append(f"Draft hero subhead: {hero.get('subhead')}")
    tagline = (artist.epk_config or {}).get("tagline")
    if tagline:
        lines.append(f"Published tagline: {tagline}")
    lines.append("")
    lines.append(completeness_context_block(db, artist))
    return "\n".join(lines)


def apply_epk_update_from_chat(
    db: Session,
    artist: Artist,
    thread: ManagerThread,
    prompt: str,
) -> tuple[str, EpkIteration]:
    """Apply an EPK patch from manager chat (user message already recorded on thread)."""
    draft_before = get_or_init_draft(artist)
    if not artist.epk_draft:
        artist.epk_draft = draft_before
        db.commit()

    summary = workbench_summary(db, storage_namespace_for_artist(artist))
    epk = artist.epk_config or {}
    system = build_system_prompt(
        artist.display_name,
        epk,
        artist.manager_system_prompt,
        prompt_role="patch",
    )
    result = generate_epk_patch(system, prompt, draft_before, workbench_summary=summary)

    patch = result.get("patch") or {}
    design_after = apply_design_patch(draft_before, patch)
    save_draft(db, artist, design_after)

    iteration = EpkIteration(
        artist_id=artist.id,
        thread_id=thread.id,
        step="generate",
        user_prompt=prompt,
        context_snapshot={"draft_before": draft_before, "workbench": summary, "source": "manager_chat"},
        model_reasoning=result.get("reasoning"),
        reasoning_summary=result.get("reasoning_summary"),
        design_patch=patch,
        design_after=design_after,
        consent_for_training=bool(artist.allow_training_contribution),
    )
    db.add(iteration)
    db.commit()
    db.refresh(iteration)

    upload_url, storage_key = _screenshot_presign(storage_namespace_for_artist(artist), iteration.id)
    if storage_key:
        iteration.screenshot_storage_key = storage_key
        db.commit()

    summary_text = result.get("reasoning_summary") or "Updated your EPK draft preview."
    return summary_text, iteration


def chat_with_history(
    db: Session,
    artist: Artist,
    thread: ManagerThread,
    user_message: str,
    *,
    channel: str = "portal",
) -> ManagerTurnResult:
    history = list_thread_messages(db, thread.id, artist.id)
    history_msgs = [{"role": m.role, "content": m.content} for m in history[-12:]]
    append_message(db, thread, "user", user_message, metadata={"channel": channel})

    context_block = build_agent_context_block(db, artist)
    turn = run_manager_turn(
        db,
        artist,
        thread,
        user_message,
        history_msgs,
        context_block=context_block,
    )
    metadata = turn.metadata
    if turn.draft_updated:
        metadata = dict(metadata or {})
        metadata.setdefault("type", "epk_generate")
        metadata.setdefault("source", "manager_chat")
        if turn.iteration_id:
            metadata["iteration_id"] = turn.iteration_id
    append_message(db, thread, "assistant", turn.reply, metadata=metadata or None)
    return turn


def iterate_epk(
    db: Session,
    artist: Artist,
    prompt: str,
    thread: ManagerThread,
) -> tuple[EpkIteration, dict, str | None, str | None]:
    draft_before = get_or_init_draft(artist)
    if not artist.epk_draft:
        artist.epk_draft = draft_before
        db.commit()

    summary = workbench_summary(db, storage_namespace_for_artist(artist))
    epk = artist.epk_config or {}
    system = build_system_prompt(
        artist.display_name,
        epk,
        artist.manager_system_prompt,
        prompt_role="patch",
    )
    result = generate_epk_patch(system, prompt, draft_before, workbench_summary=summary)

    patch = result.get("patch") or {}
    design_after = apply_design_patch(draft_before, patch)
    save_draft(db, artist, design_after)

    iteration = EpkIteration(
        artist_id=artist.id,
        thread_id=thread.id,
        step="generate",
        user_prompt=prompt,
        context_snapshot={"draft_before": draft_before, "workbench": summary},
        model_reasoning=result.get("reasoning"),
        reasoning_summary=result.get("reasoning_summary"),
        design_patch=patch,
        design_after=design_after,
        consent_for_training=bool(artist.allow_training_contribution),
    )
    db.add(iteration)
    db.commit()
    db.refresh(iteration)

    upload_url, storage_key = _screenshot_presign(storage_namespace_for_artist(artist), iteration.id)
    if storage_key:
        iteration.screenshot_storage_key = storage_key
        db.commit()

    append_message(db, thread, "user", prompt)
    summary_text = result.get("reasoning_summary") or "Updated your EPK draft preview."
    append_message(
        db,
        thread,
        "assistant",
        summary_text,
        metadata={"iteration_id": iteration.id, "type": "epk_generate"},
    )

    preview = build_preview_payload(db, artist, design_after)
    return iteration, preview, upload_url, storage_key


def annotate_iteration(
    db: Session,
    artist: Artist,
    iteration_id: str,
    annotations: list[dict],
    screenshot_storage_key: str | None,
) -> EpkIteration:
    iteration = (
        db.query(EpkIteration)
        .filter(EpkIteration.id == iteration_id, EpkIteration.artist_id == artist.id)
        .first()
    )
    if not iteration:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Iteration not found.")

    design = iteration.design_after or get_or_init_draft(artist)
    raw = [a if isinstance(a, dict) else a.model_dump() for a in annotations]
    if is_html_draft(design):
        resolved = [
            {
                "note": str(a.get("note") or "").strip(),
                "bbox_norm": a.get("bbox_norm"),
                "component_ids": a.get("component_ids") or [],
            }
            for a in raw
            if str(a.get("note") or "").strip()
        ]
    else:
        resolved = resolve_annotations(design, raw)

    iteration.annotations_raw = raw
    iteration.annotations_resolved = resolved
    if screenshot_storage_key:
        iteration.screenshot_storage_key = screenshot_storage_key
    db.commit()
    db.refresh(iteration)
    return iteration


def refine_iteration(db: Session, artist: Artist, parent: EpkIteration) -> tuple[EpkIteration, dict, str | None, str | None]:
    if not parent.annotations_resolved:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Annotate the iteration before refining.")

    draft_before = parent.design_after or get_or_init_draft(artist)
    epk = artist.epk_config or {}
    system = build_system_prompt(
        artist.display_name,
        epk,
        artist.manager_system_prompt,
        prompt_role="patch",
    )

    if is_html_draft(draft_before):
        bindings = draft_before.get("asset_bindings") or {}
        asset_urls = resolve_binding_urls(db, storage_namespace_for_artist(artist), bindings)
        result = refine_epk_html_from_annotations(
            system,
            html=draft_before.get("html") or "",
            css=draft_before.get("css") or "",
            asset_bindings=bindings,
            asset_urls=asset_urls,
            original_prompt=parent.user_prompt
            or (parent.context_snapshot if isinstance(parent.context_snapshot, dict) else {}).get("spec", ""),
            resolved_annotations=parent.annotations_resolved or [],
        )
        design_after = normalize_html_draft(
            html=result.get("html") or draft_before.get("html") or "",
            css=result.get("css") or draft_before.get("css") or "",
            asset_bindings=result.get("asset_bindings") or bindings,
            vision_id=draft_before.get("vision_id"),
            spec_snapshot=draft_before.get("spec_snapshot"),
            font_palette=draft_before.get("font_palette"),
            google_fonts_href=draft_before.get("google_fonts_href"),
        )
        patch = {"format": "html_v1"}
    else:
        result = refine_epk_from_annotations(
            system,
            draft_before,
            parent.user_prompt,
            parent.annotations_resolved,
        )
        patch = result.get("patch") or {}
        design_after = apply_design_patch(draft_before, patch)

    save_draft(db, artist, design_after)

    child = EpkIteration(
        artist_id=artist.id,
        thread_id=parent.thread_id,
        step="refine",
        user_prompt=parent.user_prompt,
        context_snapshot={"parent_id": parent.id, "annotations": parent.annotations_resolved},
        model_reasoning=result.get("reasoning"),
        reasoning_summary=result.get("reasoning_summary"),
        design_patch=patch,
        design_after=design_after,
        annotations_raw=parent.annotations_raw,
        annotations_resolved=parent.annotations_resolved,
        parent_iteration_id=parent.id,
        consent_for_training=bool(artist.allow_training_contribution),
    )
    db.add(child)
    db.commit()
    db.refresh(child)

    upload_url, storage_key = _screenshot_presign(storage_namespace_for_artist(artist), child.id)
    if storage_key:
        child.screenshot_storage_key = storage_key
        db.commit()

    if parent.thread_id:
        thread = db.query(ManagerThread).filter(ManagerThread.id == parent.thread_id).first()
        if thread:
            append_message(
                db,
                thread,
                "assistant",
                result.get("reasoning_summary") or "Refined your EPK from annotations.",
                metadata={"iteration_id": child.id, "type": "epk_refine"},
            )

    preview = build_iteration_preview(db, artist, child)
    return child, preview, upload_url, storage_key


def accept_iteration(db: Session, artist: Artist, iteration_id: str, consent: bool) -> EpkIteration:
    iteration = (
        db.query(EpkIteration)
        .filter(EpkIteration.id == iteration_id, EpkIteration.artist_id == artist.id)
        .first()
    )
    if not iteration:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Iteration not found.")
    iteration.artist_accepted = True
    if consent:
        iteration.consent_for_training = True
        artist.allow_training_contribution = True
    db.commit()
    db.refresh(iteration)
    return iteration


def publish_draft(db: Session, artist: Artist) -> dict:
    design = get_or_init_draft(artist)
    if artist.epk_draft:
        design = artist.epk_draft

    site_patch = design.get("_site_patch") or {}
    cfg = dict(artist.epk_config or {})
    if site_patch.get("tagline") is not None:
        cfg["tagline"] = site_patch["tagline"]
    if site_patch.get("bio") is not None:
        cfg["bio"] = site_patch["bio"]
    if site_patch.get("booking_email") is not None:
        cfg["booking_email"] = site_patch["booking_email"]

    hero = next((b for b in design.get("layout") or [] if b.get("id") == "hero"), {})
    if hero.get("subhead"):
        cfg["tagline"] = hero["subhead"]
    bio_block = next((b for b in design.get("layout") or [] if b.get("id") == "bio-main"), {})
    if bio_block.get("body"):
        cfg["bio"] = bio_block["body"]
    contact = next((b for b in design.get("layout") or [] if b.get("id") == "contact-1"), {})
    if contact.get("email"):
        cfg["booking_email"] = contact["email"]

    cfg["epk_design"] = {k: v for k, v in design.items() if k != "_site_patch"}
    if is_html_draft(design):
        cfg["profile_page"] = {
            k: design[k]
            for k in (
                "format",
                "html",
                "css",
                "asset_bindings",
                "font_palette",
                "google_fonts_href",
                "vision_id",
                "spec_snapshot",
            )
            if k in design
        }
    cfg["profile_published"] = True
    from datetime import datetime, timezone

    cfg["profile_published_at"] = datetime.now(timezone.utc).isoformat()
    artist.epk_config = cfg
    db.commit()
    return cfg


def export_training_jsonl(db: Session, artist: Artist, consent_only: bool = True) -> str:
    q = db.query(EpkIteration).filter(EpkIteration.artist_id == artist.id)
    if consent_only:
        q = q.filter(EpkIteration.consent_for_training.is_(True))
    rows = q.order_by(EpkIteration.created_at.asc()).all()
    lines = []
    for row in rows:
        lines.append(
            json.dumps(
                {
                    "tenant_slug": artist.tenant_slug,
                    "iteration_id": row.id,
                    "step": row.step,
                    "user_prompt": row.user_prompt,
                    "model_reasoning": row.model_reasoning,
                    "design_patch": row.design_patch,
                    "design_after": row.design_after,
                    "annotations_resolved": row.annotations_resolved,
                    "artist_accepted": row.artist_accepted,
                    "screenshot_storage_key": row.screenshot_storage_key,
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")

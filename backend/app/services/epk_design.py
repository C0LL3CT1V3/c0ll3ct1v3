"""EPK design generation — hybrid templates + optional LLM."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..models.artist import Artist
from ..models.media import MediaAsset
from ..schemas.epk_design_schemas import EpkDesignGenerateBody, EpkDesignSpec, EpkTheme
from .epk_media_resolve import (
    published_photos_for_tenant,
    published_tracks_for_tenant,
    studio_photos_for_tenant,
    studio_tracks_for_tenant,
)
from .spaces_storage import get_s3_client, presigned_get_object


def default_design_for_artist(
    artist: Artist,
    *,
    brief: str = "",
    photo_ids: list[str] | None = None,
    track_ids: list[str] | None = None,
) -> EpkDesignSpec:
    cfg = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    epk = cfg
    photos = photo_ids or []
    tracks = track_ids or []

    layout: list[dict[str, Any]] = [
        {
            "type": "hero",
            "headline": artist.display_name,
            "subhead": epk.get("tagline") or brief[:120] if brief else "",
        },
    ]
    if photos:
        layout.append({"type": "photo_grid", "columns": 2, "asset_ids": photos[:12]})
    if tracks:
        layout.append({"type": "music", "asset_ids": tracks[:20]})
    if epk.get("bio"):
        layout.append({"type": "bio", "body": epk.get("bio")})
    if epk.get("booking_email"):
        layout.append({"type": "contact", "email": epk.get("booking_email")})

    return EpkDesignSpec(
        template_id="editorial",
        theme=EpkTheme(),
        layout=layout,
        inputs_snapshot={
            "brief": brief,
            "wireframe_asset_id": None,
            "style_asset_id": None,
            "audio_asset_id": None,
        },
    )


def default_design_for_artist_db(
    db: Session,
    artist: Artist,
    body: EpkDesignGenerateBody,
) -> EpkDesignSpec:
    slug = artist.tenant_slug
    photos = studio_photos_for_tenant(db, slug)
    tracks = studio_tracks_for_tenant(db, slug)
    photo_id_set = {p["asset_id"] for p in photos if p.get("asset_id")}
    track_id_set = {t["asset_id"] for t in tracks if t.get("asset_id")}
    if body.published_media_ids is not None:
        photo_ids = [i for i in body.published_media_ids if i in photo_id_set]
        track_ids = [i for i in body.published_media_ids if i in track_id_set]
    else:
        photo_ids = list(photo_id_set)
        track_ids = list(track_id_set)
    return default_design_for_artist(
        artist,
        brief=body.brief,
        photo_ids=photo_ids,
        track_ids=track_ids,
    )


def _asset_image_url(db: Session, asset_id: str | None, tenant_slug: str) -> str | None:
    if not asset_id or not settings.spaces_enabled:
        return None
    row = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.id == asset_id,
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.is_deleted.is_(False),
        )
        .first()
    )
    if not row:
        return None
    from ..models.media import MediaVersion
    from .epk_media_resolve import best_image_variant

    ver = (
        db.query(MediaVersion)
        .filter(MediaVersion.asset_id == row.id, MediaVersion.is_current.is_(True))
        .first()
    )
    if not ver:
        return None
    best = best_image_variant(ver)
    if not best:
        return None
    try:
        client = get_s3_client()
        return presigned_get_object(client, best.storage_key)
    except Exception:
        return None


def transcribe_audio_asset(db: Session, asset_id: str | None, tenant_slug: str) -> str:
    if not asset_id:
        return ""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return ""
    row = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.id == asset_id,
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.asset_type == "audio",
            MediaAsset.is_deleted.is_(False),
        )
        .first()
    )
    if not row:
        return ""
    from ..models.media import MediaVersion

    ver = (
        db.query(MediaVersion)
        .filter(MediaVersion.asset_id == row.id, MediaVersion.is_current.is_(True))
        .first()
    )
    if not ver or not settings.spaces_enabled:
        return ""
    try:
        import tempfile
        from openai import OpenAI

        client_s3 = get_s3_client()
        with tempfile.NamedTemporaryFile(suffix=".audio") as tmp:
            client_s3.download_file(settings.spaces_bucket, ver.storage_key, tmp.name)
            oai = OpenAI(api_key=api_key)
            with open(tmp.name, "rb") as f:
                tr = oai.audio.transcriptions.create(model="whisper-1", file=f)
            return getattr(tr, "text", "") or ""
    except Exception:
        return ""


def _parse_json_from_llm(text: str) -> dict[str, Any] | None:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def generate_design_with_llm(
    db: Session,
    artist: Artist,
    body: EpkDesignGenerateBody,
    base: EpkDesignSpec,
) -> EpkDesignSpec:
    provider = (
        os.environ.get("EPK_DESIGN_LLM_PROVIDER")
        or os.environ.get("MANAGER_LLM_PROVIDER")
        or "openai"
    ).strip().lower()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if provider != "openai" or not api_key:
        return base

    slug = artist.tenant_slug
    wire_url = _asset_image_url(db, body.wireframe_asset_id, slug)
    style_url = _asset_image_url(db, body.style_asset_id, slug)
    audio_text = transcribe_audio_asset(db, body.audio_asset_id, slug)
    brief = body.brief
    if audio_text:
        brief = f"{brief}\n\nAudio notes:\n{audio_text}".strip()

    system = (
        "You are an EPK layout designer. Output ONLY valid JSON matching this schema:\n"
        '{"template_id":"editorial|gallery|minimal","theme":{"accent":"#hex","background":"#hex",'
        '"font_pair":"serif-sans|sans|mono"},"layout":[{"type":"hero","headline":"...","subhead":"..."},'
        '{"type":"photo_grid","columns":2,"asset_ids":["uuid"]},{"type":"music","asset_ids":[]},'
        '{"type":"bio","body":"..."},{"type":"contact","email":"..."}],"inputs_snapshot":{"brief":"..."}}\n'
        "Use only asset_ids from the provided lists. Keep layout 3-6 blocks."
    )
    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Artist: {artist.display_name}\nBrief:\n{brief}\n"
                f"Photo asset_ids: {[p['asset_id'] for p in studio_photos_for_tenant(db, slug)]}\n"
                f"Track asset_ids: {[t['asset_id'] for t in studio_tracks_for_tenant(db, slug)]}\n"
                f"Current draft JSON:\n{base.model_dump_json()}"
            ),
        },
    ]
    if wire_url:
        user_content.append({"type": "image_url", "image_url": {"url": wire_url}})
    if style_url:
        user_content.append({"type": "image_url", "image_url": {"url": style_url}})

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.environ.get("EPK_DESIGN_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=2000,
            temperature=0.4,
        )
        raw = (resp.choices[0].message.content or "").strip()
        parsed = _parse_json_from_llm(raw)
        if not parsed:
            return base
        merged = base.model_dump()
        for key in ("template_id", "theme", "layout"):
            if key in parsed:
                merged[key] = parsed[key]
        merged["inputs_snapshot"] = {
            **base.inputs_snapshot.model_dump(),
            "brief": brief,
            "wireframe_asset_id": body.wireframe_asset_id,
            "style_asset_id": body.style_asset_id,
            "audio_asset_id": body.audio_asset_id,
        }
        spec = EpkDesignSpec.model_validate(merged)
        if body.polish_copy:
            spec = _polish_copy_only(client, model, spec, brief)
        return spec
    except Exception:
        return base


def _polish_copy_only(client, model: str, spec: EpkDesignSpec, brief: str) -> EpkDesignSpec:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Polish headline/subhead/bio text only. Return same JSON structure, do not change asset_ids or template_id.",
                },
                {"role": "user", "content": f"Brief: {brief}\n\n{spec.model_dump_json()}"},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        parsed = _parse_json_from_llm((resp.choices[0].message.content or "").strip())
        if parsed and "layout" in parsed:
            spec = EpkDesignSpec.model_validate({**spec.model_dump(), "layout": parsed["layout"]})
    except Exception:
        pass
    return spec


def generate_design(db: Session, artist: Artist, body: EpkDesignGenerateBody) -> EpkDesignSpec:
    base = default_design_for_artist_db(db, artist, body)
    if body.template_id:
        base.template_id = body.template_id
    return generate_design_with_llm(db, artist, body, base)

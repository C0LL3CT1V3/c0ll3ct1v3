"""Authenticated EPK design studio endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ...database import get_db
from ...models.user import User
from ...schemas.epk_design_schemas import EpkDesignGenerateBody, EpkDesignOut, EpkDesignSpec
from ...services.artist_service import get_or_create_artist
from ...services.epk_design import default_design_for_artist_db, generate_design
from ...services.epk_media_resolve import (
    published_photos_for_tenant,
    published_tracks_for_tenant,
    studio_photos_for_tenant,
    studio_tracks_for_tenant,
)

router = APIRouter(prefix="/epk/design", tags=["epk-design"])


def _cfg_dict(artist) -> dict:
    return dict(artist.epk_config) if isinstance(artist.epk_config, dict) else {}


def _design_out(artist) -> EpkDesignOut:
    cfg = _cfg_dict(artist)
    draft = cfg.get("design")
    published = cfg.get("design_published")
    return EpkDesignOut(
        draft=EpkDesignSpec.model_validate(draft) if isinstance(draft, dict) else None,
        published=EpkDesignSpec.model_validate(published) if isinstance(published, dict) else None,
        design_published_at=cfg.get("design_published_at"),
    )


@router.get("/draft", response_model=EpkDesignOut)
def get_design_draft(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EpkDesignOut:
    artist = get_or_create_artist(db, current_user)
    return _design_out(artist)


@router.get("/preview")
def preview_site(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Aggregate draft design + resolved media for portal preview."""
    artist = get_or_create_artist(db, current_user)
    cfg = _cfg_dict(artist)
    draft_raw = cfg.get("design")
    if not isinstance(draft_raw, dict):
        draft = default_design_for_artist_db(db, artist, EpkDesignGenerateBody())
    else:
        draft = EpkDesignSpec.model_validate(draft_raw)
    slug = artist.tenant_slug
    epk = cfg
    return {
        "tenant_slug": slug,
        "display_name": artist.display_name,
        "tagline": epk.get("tagline") or "",
        "bio": epk.get("bio") or "",
        "booking_email": epk.get("booking_email") or "",
        "social": epk.get("social") or {},
        "sections": epk.get("sections") or {},
        "design": draft.model_dump(),
        "tracks": studio_tracks_for_tenant(db, slug),
        "photos": studio_photos_for_tenant(db, slug),
        "published_tracks": published_tracks_for_tenant(db, slug),
        "published_photos": published_photos_for_tenant(db, slug),
    }


@router.post("/generate", response_model=EpkDesignOut)
def post_generate_design(
    body: EpkDesignGenerateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EpkDesignOut:
    artist = get_or_create_artist(db, current_user)
    spec = generate_design(db, artist, body)
    cfg = _cfg_dict(artist)
    cfg["design"] = spec.model_dump()
    artist.epk_config = cfg
    db.commit()
    db.refresh(artist)
    return _design_out(artist)


@router.post("/publish", response_model=EpkDesignOut)
def post_publish_design(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EpkDesignOut:
    artist = get_or_create_artist(db, current_user)
    cfg = _cfg_dict(artist)
    draft = cfg.get("design")
    if not isinstance(draft, dict):
        raise HTTPException(status_code=400, detail="No design draft to publish. Generate a preview first.")
    cfg["design_published"] = draft
    cfg["design_published_at"] = datetime.now(timezone.utc).isoformat()
    artist.epk_config = cfg
    db.commit()
    db.refresh(artist)
    return _design_out(artist)


@router.post("/init-default", response_model=EpkDesignOut)
def post_init_default_design(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EpkDesignOut:
    """Create a template-only draft without LLM (Phase 1 path)."""
    artist = get_or_create_artist(db, current_user)
    spec = default_design_for_artist_db(db, artist, EpkDesignGenerateBody())
    cfg = _cfg_dict(artist)
    cfg["design"] = spec.model_dump()
    artist.epk_config = cfg
    db.commit()
    db.refresh(artist)
    return _design_out(artist)

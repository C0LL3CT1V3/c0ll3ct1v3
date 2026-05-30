"""Authenticated artist profile API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ...database import get_db
from ...models.artist import Artist
from ...models.user import User
from ...schemas.artist_schemas import (
    ArtistProfileOut,
    ArtistProfilePatch,
    coerce_epk_config,
)
from ...schemas.audience_schemas import AudienceMapReport
from ...services.artist_service import get_or_create_artist, validate_tenant_slug

router = APIRouter(prefix="/artists", tags=["artists"])


def _to_out(artist) -> ArtistProfileOut:
    return ArtistProfileOut(
        id=artist.id,
        tenant_slug=artist.tenant_slug,
        display_name=artist.display_name,
        epk_config=coerce_epk_config(
            artist.epk_config if isinstance(artist.epk_config, dict) else None,
        ),
    )


@router.get("/me", response_model=ArtistProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArtistProfileOut:
    try:
        artist = get_or_create_artist(db, current_user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_out(artist)


@router.patch("/me", response_model=ArtistProfileOut)
def patch_my_profile(
    body: ArtistProfilePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArtistProfileOut:
    try:
        artist = get_or_create_artist(db, current_user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if body.display_name is not None:
        artist.display_name = body.display_name.strip() or artist.display_name

    if body.tenant_slug is not None:
        try:
            new_slug = validate_tenant_slug(body.tenant_slug)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        conflict = (
            db.query(Artist)
            .filter(Artist.tenant_slug == new_slug, Artist.id != artist.id)
            .first()
        )
        if conflict:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="tenant_slug already in use.")
        artist.tenant_slug = new_slug

    if body.epk_config is not None:
        merged = {**(artist.epk_config or {}), **body.epk_config.model_dump()}
        artist.epk_config = merged

    db.commit()
    db.refresh(artist)
    return _to_out(artist)


@router.get("/me/audience-profile")
def get_my_audience_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    artist = get_or_create_artist(db, current_user)
    epk = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    return {"audience_profile": epk.get("audience_profile")}


@router.post("/me/audience-profile/refresh", response_model=AudienceMapReport)
def refresh_my_audience_profile(
    asset_id: str = Query(..., description="Media asset UUID to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AudienceMapReport:
    from ..music.router import analyze_media_asset

    return analyze_media_asset(asset_id, persist=True, db=db, current_user=current_user)

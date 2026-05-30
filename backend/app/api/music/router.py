"""Audience mapper API — analyze tracks and cache audience profile."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user
from ...config import settings
from ...database import get_db
from ...models.media import MediaAsset, MediaVersion
from ...models.user import User
from ...schemas.audience_schemas import AudienceMapReport
from ...services.artist_service import get_or_create_artist, tenant_slug_for_user
from ...services.audience_map import (
    audience_profile_from_cache,
    build_audience_map,
    cache_audience_profile,
    report_to_markdown,
)
from ...services.spaces_storage import get_s3_client

router = APIRouter(prefix="/music", tags=["music"])


def _assert_asset_workspace(asset: MediaAsset, db: Session, user: User) -> None:
    allowed = tenant_slug_for_user(db, user)
    if asset.tenant_slug != allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found.")


@router.post("/analyze", response_model=AudienceMapReport)
async def analyze_upload(
    file: UploadFile = File(...),
    track_title: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AudienceMapReport:
    if not settings.audience_analysis_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Audience analysis is disabled.")

    suffix = os.path.splitext(file.filename or "upload.bin")[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        return build_audience_map(
            tmp_path,
            track_title=track_title or (file.filename or "").rsplit(".", 1)[0],
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Analysis failed: {exc}") from exc
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/media/assets/{asset_id}/audience-map", response_model=AudienceMapReport)
def analyze_media_asset(
    asset_id: str,
    persist: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AudienceMapReport:
    if not settings.audience_analysis_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Audience analysis is disabled.")
    if not settings.spaces_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Object storage required for asset analysis.")

    asset = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions))
        .filter(MediaAsset.id == asset_id, MediaAsset.is_deleted.is_(False))
        .first()
    )
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    _assert_asset_workspace(asset, db, current_user)

    ver = next((v for v in asset.versions if v.is_current), None)
    if not ver:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No current version.")

    if asset.status not in ("ready", "published", "processing"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Asset must finish uploading before analysis (status inbox not supported).",
        )

    suffix = os.path.splitext(ver.original_filename or ver.storage_key)[1] or ".mp3"
    client = get_s3_client()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
    try:
        client.download_file(settings.spaces_bucket, ver.storage_key, tmp_path)
        report = build_audience_map(
            tmp_path,
            track_title=asset.title,
            reference_asset_id=asset.id,
        )
        if persist:
            artist = get_or_create_artist(db, current_user)
            artist.epk_config = cache_audience_profile(artist.epk_config or {}, report)
            tags = dict(asset.tags or {})
            tags["audience_map"] = {
                "primary_genre": report.primary_genre,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            asset.tags = tags
            db.commit()
        return report
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Analysis failed: {exc}") from exc
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/audience-profile")
def get_audience_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    artist = get_or_create_artist(db, current_user)
    epk = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    profile = epk.get("audience_profile")
    if not profile:
        return {"audience_profile": None}
    return {"audience_profile": profile}


@router.post("/audience-profile/refresh", response_model=AudienceMapReport)
def refresh_audience_profile(
    asset_id: str = Query(..., description="Media asset UUID to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AudienceMapReport:
    return analyze_media_asset(asset_id, persist=True, db=db, current_user=current_user)


@router.get("/audience-profile/markdown")
def get_audience_profile_markdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    artist = get_or_create_artist(db, current_user)
    epk = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    raw = epk.get("audience_profile")
    if not raw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No cached audience profile.")
    try:
        report = audience_profile_from_cache(raw)
        if not report:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cached profile incomplete.")
        return {"markdown": report_to_markdown(report)}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

"""OAuth connect + cloud file import (Google Drive, Dropbox)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ...database import get_db
from ...models.cloud_connection import CloudConnection
from ...models.user import User
from ...schemas.cloud_schemas import (
    CloudDropboxImportBody,
    CloudFileListOut,
    CloudFileOut,
    CloudImportBody,
    CloudImportOut,
    CloudStatusOut,
    CloudProviderStatus,
    OAuthAuthorizeOut,
)
from ...services.artist_service import get_or_create_artist, tenant_slug_for_user
from ...services.cloud_dropbox import download_dropbox_file, list_dropbox_files
from ...services.cloud_google import download_google_file, list_google_files
from ...services.cloud_import_media import import_bytes_to_workbench
from ...services.cloud_oauth import (
    build_dropbox_authorize_url,
    build_google_authorize_url,
    connection_status,
    dropbox_oauth_configured,
    exchange_dropbox_code,
    exchange_google_code,
    frontend_redirect,
    verify_oauth_state,
)

router = APIRouter(prefix="/cloud", tags=["media-cloud"])


def _artist(db: Session, user: User):
    return get_or_create_artist(db, user)


@router.get("/status", response_model=CloudStatusOut)
def cloud_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CloudStatusOut:
    artist = _artist(db, current_user)
    raw = connection_status(db, artist.id)
    return CloudStatusOut(
        google=CloudProviderStatus(**raw["google"]),
        dropbox=CloudProviderStatus(**raw["dropbox"]),
    )


@router.get("/google/authorize", response_model=OAuthAuthorizeOut)
def google_authorize(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OAuthAuthorizeOut:
    artist = _artist(db, current_user)
    return OAuthAuthorizeOut(url=build_google_authorize_url(artist.id))


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(frontend_redirect("google", ok=False, error=error))
    if not code or not state:
        return RedirectResponse(frontend_redirect("google", ok=False, error="missing_code"))
    artist_id, provider = verify_oauth_state(state)
    if provider != "google":
        raise HTTPException(status_code=400, detail="Invalid provider in state.")
    await exchange_google_code(db, artist_id, code)
    return RedirectResponse(frontend_redirect("google", ok=True))


@router.delete("/google/disconnect", status_code=204, response_class=Response)
def google_disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    artist = _artist(db, current_user)
    db.query(CloudConnection).filter(
        CloudConnection.artist_id == artist.id,
        CloudConnection.provider == "google",
    ).delete()
    db.commit()
    return Response(status_code=204)


@router.get("/google/files", response_model=CloudFileListOut)
async def google_files(
    page_token: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CloudFileListOut:
    artist = _artist(db, current_user)
    data = await list_google_files(db, artist.id, page_token=page_token)
    return CloudFileListOut(
        files=[CloudFileOut(**f) for f in data["files"] if not f.get("is_folder")],
        next_page_token=data.get("next_page_token"),
    )


@router.post("/google/import", response_model=CloudImportOut)
async def google_import(
    body: CloudImportBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CloudImportOut:
    artist = _artist(db, current_user)
    tenant = tenant_slug_for_user(db, current_user)
    name, mime, data = await download_google_file(db, artist.id, body.file_id)
    asset = import_bytes_to_workbench(
        db,
        tenant_slug=tenant,
        created_by=current_user.auth0_sub or str(current_user.id),
        filename=name,
        mime_type=mime,
        data=data,
    )
    return CloudImportOut(asset_id=asset.id, title=asset.title)


@router.get("/dropbox/authorize", response_model=OAuthAuthorizeOut)
def dropbox_authorize(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OAuthAuthorizeOut:
    artist = _artist(db, current_user)
    return OAuthAuthorizeOut(url=build_dropbox_authorize_url(artist.id))


@router.get("/dropbox/callback")
async def dropbox_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(frontend_redirect("dropbox", ok=False, error=error))
    if not code or not state:
        return RedirectResponse(frontend_redirect("dropbox", ok=False, error="missing_code"))
    artist_id, provider = verify_oauth_state(state)
    if provider != "dropbox":
        raise HTTPException(status_code=400, detail="Invalid provider in state.")
    await exchange_dropbox_code(db, artist_id, code)
    return RedirectResponse(frontend_redirect("dropbox", ok=True))


@router.delete("/dropbox/disconnect", status_code=204, response_class=Response)
def dropbox_disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    artist = _artist(db, current_user)
    db.query(CloudConnection).filter(
        CloudConnection.artist_id == artist.id,
        CloudConnection.provider == "dropbox",
    ).delete()
    db.commit()
    return Response(status_code=204)


@router.get("/dropbox/files", response_model=CloudFileListOut)
async def dropbox_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CloudFileListOut:
    artist = _artist(db, current_user)
    data = await list_dropbox_files(db, artist.id)
    return CloudFileListOut(
        files=[CloudFileOut(**f) for f in data["files"] if not f.get("is_folder")],
        next_page_token=data.get("next_page_token"),
    )


@router.post("/dropbox/import", response_model=CloudImportOut)
async def dropbox_import(
    body: CloudDropboxImportBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CloudImportOut:
    artist = _artist(db, current_user)
    tenant = tenant_slug_for_user(db, current_user)
    name, mime, data = await download_dropbox_file(db, artist.id, body.path)
    asset = import_bytes_to_workbench(
        db,
        tenant_slug=tenant,
        created_by=current_user.auth0_sub or str(current_user.id),
        filename=name,
        mime_type=mime,
        data=data,
    )
    return CloudImportOut(asset_id=asset.id, title=asset.title)

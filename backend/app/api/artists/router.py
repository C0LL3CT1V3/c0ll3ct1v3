"""Authenticated artist profile API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ...database import get_db
from ...models.artist import Artist
from ...models.user import User
from ...schemas.artist_schemas import (
    ArtistProfileOut,
    ArtistProfilePatch,
    PublicProfileOut,
    coerce_epk_config,
)
from ...schemas.audience_schemas import AudienceMapReport
from ...schemas.epk_public_schemas import EpkPublicOut, EpkPublicPatch, PublicBookerEpkOut
from ...schemas.homebase_schemas import HomebaseOut, HomebasePatch, PublicHomebaseOut
from ...schemas.payments_schemas import CatalogOut, CheckoutOut, CheckoutRequest
from ...services.artist_service import (
    claim_tenant_slug,
    get_or_create_artist,
    rebind_media_to_storage_namespace,
    resolve_artist_by_public_slug,
)
from ...services.epk_pdf import generate_booker_epk_pdf
from ...services.epk_media import collect_epk_asset_ids, epk_content_hash, is_machine_request, redirect_epk_asset
from ...services.epk_preview_token import verify_epk_preview_token
from ...services.epk_public import (
    create_epk_preview_link,
    get_my_epk_public,
    get_public_booker_epk,
    patch_epk_public,
    publish_epk_public,
    render_booker_epk_html,
    render_draft_booker_epk_html,
    resolve_epk_public,
)
from ...services.epk_public_config import coerce_epk_public, get_epk_public_raw
from ...services.homebase import (
    collect_homebase_asset_ids,
    get_homebase_raw,
    get_my_homebase,
    get_public_homebase,
    patch_homebase,
    publish_homebase,
)
from ...services.payments import (
    create_public_checkout,
    get_my_catalog,
    get_public_catalog,
)
from ...services.attestation_service import consent_menu
from ...services.profile_public import get_public_profile, render_public_profile_html

router = APIRouter(prefix="/artists", tags=["artists"])


@router.get("/public/{tenant_slug}", response_model=PublicProfileOut)
def get_public_artist_profile(
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> PublicProfileOut:
    return PublicProfileOut(**get_public_profile(db, tenant_slug))


@router.get("/public/{tenant_slug}/page", response_class=HTMLResponse)
def get_public_artist_page(
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    html = render_public_profile_html(db, tenant_slug)
    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=60"})


@router.get("/public/{tenant_slug}/epk", response_model=PublicBookerEpkOut)
def get_public_booker_epk_route(
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> PublicBookerEpkOut:
    return PublicBookerEpkOut(**get_public_booker_epk(db, tenant_slug))


@router.get("/public/{tenant_slug}/epk/page", response_class=HTMLResponse)
def get_public_booker_epk_page(
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    html = render_booker_epk_html(db, tenant_slug)
    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=60"})


@router.get("/public/{tenant_slug}/homebase", response_model=PublicHomebaseOut)
def get_public_homebase_route(
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> PublicHomebaseOut:
    return PublicHomebaseOut(**get_public_homebase(db, tenant_slug))


@router.get("/public/{tenant_slug}/homebase/media/{asset_id}")
def public_homebase_media(
    tenant_slug: str,
    asset_id: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Homebase not found.")
    raw = get_homebase_raw(artist)
    if not (isinstance(raw, dict) and raw.get("published")):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Homebase not published.")
    return redirect_epk_asset(
        db,
        artist=artist,
        asset_id=asset_id,
        allowed_ids=collect_homebase_asset_ids(raw),
    )


@router.get("/public/{tenant_slug}/catalog", response_model=CatalogOut)
def get_public_catalog_route(
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> CatalogOut:
    return CatalogOut(**get_public_catalog(db, tenant_slug))


@router.post("/public/{tenant_slug}/checkout", response_model=CheckoutOut)
def post_public_checkout(
    tenant_slug: str,
    body: CheckoutRequest,
    db: Session = Depends(get_db),
) -> CheckoutOut:
    return CheckoutOut(**create_public_checkout(db, tenant_slug, body))


def _to_out(artist) -> ArtistProfileOut:
    raw = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    epk_public = raw.get("epk_public") if isinstance(raw.get("epk_public"), dict) else {}
    homebase = raw.get("homebase") if isinstance(raw.get("homebase"), dict) else {}
    return ArtistProfileOut(
        id=artist.id,
        tenant_slug=artist.tenant_slug,
        display_name=artist.display_name,
        epk_config=coerce_epk_config(raw),
        profile_published=bool(raw.get("profile_published")),
        epk_public_published=bool(raw.get("epk_public_published") or epk_public.get("published")),
        homebase_published=bool(homebase.get("published")),
        epk_public=epk_public,
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
            artist = claim_tenant_slug(db, artist=artist, user=current_user, new_slug=body.tenant_slug)
        except ValueError as exc:
            msg = str(exc)
            if msg == "tenant_slug already in use.":
                raise HTTPException(status.HTTP_409_CONFLICT, detail=msg) from exc
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    else:
        rebind_media_to_storage_namespace(db, artist)

    if body.epk_config is not None:
        merged = {**(artist.epk_config or {}), **body.epk_config.model_dump()}
        artist.epk_config = merged

    db.commit()
    db.refresh(artist)
    return _to_out(artist)


@router.get("/me/epk-public", response_model=EpkPublicOut)
def get_my_epk_public_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EpkPublicOut:
    artist = get_or_create_artist(db, current_user)
    data = get_my_epk_public(db, artist)
    return EpkPublicOut(**data)


@router.patch("/me/epk-public", response_model=EpkPublicOut)
def patch_my_epk_public_route(
    body: EpkPublicPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EpkPublicOut:
    artist = get_or_create_artist(db, current_user)
    patch_epk_public(db, artist, body)
    data = get_my_epk_public(db, artist)
    return EpkPublicOut(**data)


@router.post("/me/epk-public/publish", response_model=EpkPublicOut)
def publish_my_epk_public_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EpkPublicOut:
    artist = get_or_create_artist(db, current_user)
    publish_epk_public(db, artist)
    data = get_my_epk_public(db, artist)
    return EpkPublicOut(**data)


@router.get("/me/homebase", response_model=HomebaseOut)
def get_my_homebase_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HomebaseOut:
    artist = get_or_create_artist(db, current_user)
    return HomebaseOut(**get_my_homebase(artist))


@router.patch("/me/homebase", response_model=HomebaseOut)
def patch_my_homebase_route(
    body: HomebasePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HomebaseOut:
    artist = get_or_create_artist(db, current_user)
    patch_homebase(db, artist, body)
    return HomebaseOut(**get_my_homebase(artist))


@router.post("/me/homebase/publish", response_model=HomebaseOut)
def publish_my_homebase_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HomebaseOut:
    artist = get_or_create_artist(db, current_user)
    publish_homebase(db, artist)
    return HomebaseOut(**get_my_homebase(artist))


@router.get("/me/catalog", response_model=CatalogOut)
def get_my_catalog_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogOut:
    artist = get_or_create_artist(db, current_user)
    return CatalogOut(**get_my_catalog(db, artist))


@router.post("/me/epk-public/preview-link")
def create_epk_preview_link_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a tokenized preview URL that works in a new tab (no auth header needed)."""
    artist = get_or_create_artist(db, current_user)
    from ...services.public_urls import public_epk_url

    return {
        "preview_url": create_epk_preview_link(db, artist),
        "public_epk_url": public_epk_url(artist.tenant_slug),
    }


@router.get("/epk-preview/page", response_class=HTMLResponse)
def epk_preview_page(
    token: str,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    meta = verify_epk_preview_token(token)
    artist = db.query(Artist).filter(Artist.id == meta["artist_id"]).first()
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artist not found.")
    if epk_content_hash(artist) != meta["content_hash"]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Preview is stale — click Preview EPK again from the portal.",
        )
    html_out = render_draft_booker_epk_html(db, artist, preview_token=token)
    return HTMLResponse(content=html_out, headers={"Cache-Control": "no-store"})


@router.get("/epk-preview/media/{asset_id}")
def epk_preview_media(
    asset_id: str,
    token: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    meta = verify_epk_preview_token(token)
    artist = db.query(Artist).filter(Artist.id == meta["artist_id"]).first()
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artist not found.")
    epk = coerce_epk_public(get_epk_public_raw(artist))
    data = resolve_epk_public(db, artist, epk, preview_token=token)
    return redirect_epk_asset(
        db,
        artist=artist,
        asset_id=asset_id,
        allowed_ids=collect_epk_asset_ids(data),
    )


@router.get("/public/{tenant_slug}/epk/media/{asset_id}")
def public_epk_media(
    tenant_slug: str,
    asset_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    artist = resolve_artist_by_public_slug(db, tenant_slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="EPK not found.")
    raw = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    if not raw.get("epk_public_published"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="EPK not published.")
    epk = coerce_epk_public(get_epk_public_raw(artist))
    data = resolve_epk_public(db, artist, epk)
    allowed_ids = collect_epk_asset_ids(data)
    if is_machine_request(request):
        if asset_id not in allowed_ids:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not in EPK.")
        body = consent_menu(db, artist, asset_id)
        body["settlement"] = "stub"
        return JSONResponse(status_code=402, content=body)
    return redirect_epk_asset(
        db,
        artist=artist,
        asset_id=asset_id,
        allowed_ids=allowed_ids,
    )


@router.get("/me/epk-public/pdf")
def download_my_epk_public_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    artist = get_or_create_artist(db, current_user)
    raw = artist.epk_config if isinstance(artist.epk_config, dict) else {}
    if not raw.get("epk_public_published"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Publish your EPK before exporting PDF.")
    pdf = generate_booker_epk_pdf(artist.tenant_slug)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{artist.tenant_slug}-epk.pdf"'},
    )


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

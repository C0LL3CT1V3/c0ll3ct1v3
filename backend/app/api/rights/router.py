"""Public rights, verify, and generated machine-readable declarations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from ...config import settings
from ...database import get_db
from ...services.artist_service import resolve_artist_by_public_slug
from ...services.attestation_declarations import ai_txt, robots_txt, rsl_xml, tdmrep_json
from ...services.attestation_service import get_public_history, get_public_rights, verify_claim

router = APIRouter(tags=["rights"])


def _slug_from_host(request: Request) -> str | None:
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(":")[0]
    host = host.lower()
    if host.endswith(".c0ll3ct1v3.xyz"):
        sub = host[: -len(".c0ll3ct1v3.xyz")]
        return None if sub in {"www", ""} else sub
    if host.endswith(".localhost"):
        sub = host[: -len(".localhost")]
        return None if sub in {"www", ""} else sub
    return None


def _require_artist(db: Session, request: Request):
    slug = _slug_from_host(request)
    if not slug:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not an artist host.")
    artist = resolve_artist_by_public_slug(db, slug)
    if not artist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artist not found.")
    return artist


def _origin(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or settings.public_site_domain
    return f"{proto}://{host}"


@router.get("/rights/{asset_id}")
def public_rights(asset_id: str, db: Session = Depends(get_db)) -> dict:
    return get_public_rights(db, asset_id)


@router.get("/rights/{asset_id}/history")
def public_rights_history(asset_id: str, db: Session = Depends(get_db)) -> dict:
    return get_public_history(db, asset_id)


@router.get("/verify/{claim_id}")
def public_verify(claim_id: str, db: Session = Depends(get_db)) -> dict:
    return verify_claim(db, claim_id)


@router.get("/site/tdmrep.json")
def site_tdmrep(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    artist = _require_artist(db, request)
    return JSONResponse(tdmrep_json(db, artist))


@router.get("/site/robots.txt")
def site_robots(request: Request, db: Session = Depends(get_db)) -> PlainTextResponse:
    artist = _require_artist(db, request)
    return PlainTextResponse(robots_txt(db, artist, origin=_origin(request)), media_type="text/plain")


@router.get("/site/license.xml")
def site_license(request: Request, db: Session = Depends(get_db)) -> Response:
    artist = _require_artist(db, request)
    return Response(content=rsl_xml(db, artist, origin=_origin(request)), media_type="application/xml")


@router.get("/site/ai.txt")
def site_ai_txt(request: Request, db: Session = Depends(get_db)) -> PlainTextResponse:
    artist = _require_artist(db, request)
    return PlainTextResponse(ai_txt(db, artist), media_type="text/plain")

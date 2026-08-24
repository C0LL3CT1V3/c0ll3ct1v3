"""Artist-authenticated attestation write path."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from ..manager_auth import get_manager_artist
from ...database import get_db
from ...models.artist import Artist
from ...schemas.attestation_schemas import AttestationConfirmBody, AttestationCreateBody, IngestBody
from ...services.attestation_ingest import ingest_asset, serialize_ingest
from ...services.attestation_service import (
    confirm_claim,
    dispute_claim,
    insert_draft,
    list_claims_for_artist,
    reject_claim,
    serialize_claim,
)

router = APIRouter(prefix="/manager", tags=["attestation"])


def _role_for(artist: Artist) -> str:
    if (artist.auth0_sub or "").startswith("seed:"):
        return "agent"
    return "artist"


@router.get("/attestations")
def list_attestations(
    asset_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    rows = list_claims_for_artist(db, artist, asset_id=asset_id)
    return {"claims": [serialize_claim(row) for row in rows]}


@router.post("/attestations", status_code=status.HTTP_201_CREATED)
def create_attestation(
    body: AttestationCreateBody,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    row = insert_draft(
        db,
        artist,
        claim_type=body.claim_type,
        value=body.value,
        source=body.source or "manual",
        subject_asset_id=body.subject_asset_id,
        source_ref={"path": "manual"},
    )
    db.commit()
    db.refresh(row)
    return serialize_claim(row)


@router.post("/attestations/{claim_id}/confirm")
def confirm_attestation(
    claim_id: str,
    body: AttestationConfirmBody | None = None,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    row = confirm_claim(
        db,
        artist,
        claim_id,
        value=(body.value if body else None),
        role=_role_for(artist),
    )
    db.commit()
    db.refresh(row)
    return serialize_claim(row)


@router.post("/attestations/{claim_id}/reject")
def reject_attestation(
    claim_id: str,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    row = reject_claim(db, artist, claim_id)
    db.commit()
    db.refresh(row)
    return serialize_claim(row)


@router.patch("/attestations/{claim_id}/dispute")
def dispute_attestation(
    claim_id: str,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    row = dispute_claim(db, artist, claim_id)
    db.commit()
    db.refresh(row)
    return serialize_claim(row)


@router.post("/ingest/{asset_id}")
def ingest_attestation_drafts(
    asset_id: str,
    body: IngestBody | None = None,
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    rows = ingest_asset(
        db,
        artist,
        asset_id,
        sources=body.sources if body else None,
        csv_bytes=(body.csv_text.encode("utf-8") if body and body.csv_text else None),
    )
    return serialize_ingest(rows)


@router.post("/ingest/{asset_id}/csv")
async def ingest_distributor_csv(
    asset_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    artist: Artist = Depends(get_manager_artist),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Upload a .csv export.")
    content = await file.read()
    rows = ingest_asset(
        db,
        artist,
        asset_id,
        sources=["distributor_export"],
        csv_bytes=content,
    )
    return serialize_ingest(rows)

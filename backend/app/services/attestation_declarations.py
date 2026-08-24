"""RSL / TDMRep / robots.txt generated from active consent claims."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models.artist import Artist
from ..models.attestation import AttestationClaim


def _active_consents(db: Session, artist: Artist) -> dict[str, AttestationClaim]:
    rows = (
        db.query(AttestationClaim)
        .filter(
            AttestationClaim.artist_id == artist.id,
            AttestationClaim.status == "active",
            AttestationClaim.claim_type.in_(("consent_train", "consent_sync", "consent_cite")),
        )
        .all()
    )
    out: dict[str, AttestationClaim] = {}
    for row in rows:
        if row.subject_asset_id is None:
            out.setdefault(row.claim_type, row)
        else:
            out[row.claim_type] = row
    return out


def _allowed(consents: dict[str, AttestationClaim], claim_type: str) -> bool:
    row = consents.get(claim_type)
    if not row:
        return False
    return bool((row.value or {}).get("allowed"))


def tdmrep_json(db: Session, artist: Artist) -> dict[str, Any]:
    consents = _active_consents(db, artist)
    train = _allowed(consents, "consent_train")
    return {
        "tdmrep": "1.0",
        "tdm": [{"id": "tdm-reservation", "value": "0" if train else "1"}],
        "artist": artist.tenant_slug,
    }


def robots_txt(db: Session, artist: Artist, *, origin: str) -> str:
    consents = _active_consents(db, artist)
    train = "y" if _allowed(consents, "consent_train") else "n"
    license_url = f"{origin.rstrip('/')}/license.xml"
    return (
        "User-Agent: *\n"
        "Allow: /\n"
        f"Content-Usage: train-ai={train}\n"
        f"License: {license_url}\n"
    )


def rsl_xml(db: Session, artist: Artist, *, origin: str) -> str:
    consents = _active_consents(db, artist)
    permits: list[str] = []
    if _allowed(consents, "consent_train"):
        permits.append("ai-train")
    if _allowed(consents, "consent_cite"):
        permits.append("ai-use")
    permit_xml = "".join(f"<permits type=\"usage\">{p}</permits>" for p in permits) or (
        "<prohibits type=\"usage\">ai-train</prohibits>"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rsl xmlns="https://rslstandard.org/rsl">\n'
        f'  <content url="{origin.rstrip("/")}/">\n'
        "    <license>\n"
        f"      {permit_xml}\n"
        "      <payment type=\"attribution\"/>\n"
        "      <standard>This file is generated from signed attestation claims. "
        "It is a declaration, not a binding offer.</standard>\n"
        "    </license>\n"
        "  </content>\n"
        "</rsl>\n"
    )


def ai_txt(db: Session, artist: Artist) -> str:
    consents = _active_consents(db, artist)
    train = "yes" if _allowed(consents, "consent_train") else "no"
    cite = "yes" if _allowed(consents, "consent_cite") else "no"
    sync = "yes" if _allowed(consents, "consent_sync") else "no"
    return (
        f"# generated from c0ll3ct1v3 attestation ledger for {artist.tenant_slug}\n"
        f"train: {train}\n"
        f"cite: {cite}\n"
        f"sync: {sync}\n"
    )

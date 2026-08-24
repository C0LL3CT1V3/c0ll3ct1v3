"""Attestation ledger: drafts, confirm, public rights, 402 detection."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.account import BankAccount  # noqa: F401
from app.models.artist import Artist
from app.models.attestation import AttestationClaim
from app.models.media import MediaAsset
from app.models.user import User  # noqa: F401
from app.models.vision import Vision  # noqa: F401
from app.services.attestation_crypto import sign_payload, verify_signature
from app.services.attestation_declarations import robots_txt, tdmrep_json
from app.services.attestation_ingest import ingest_asset
from app.services.attestation_service import (
    confirm_claim,
    get_public_rights,
    insert_draft,
    reject_claim,
    verify_claim,
)
from app.services.connectors.distributor_csv import parse_distributor_csv
from app.services.epk_media import is_machine_request


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        auth0_sub="auth0|attest",
        tenant_slug="pj",
        storage_namespace="pj",
        display_name="Phillip James",
        allow_training_contribution=False,
        epk_config={
            "epk_public_published": True,
            "epk_public": {
                "audio_samples": [{"asset_id": "track-1", "title": "Demo"}],
            },
        },
    )
    session.add(artist)
    session.flush()
    session.add(
        MediaAsset(
            id="track-1",
            tenant_slug="pj",
            title="Demo Song",
            asset_type="audio",
            status="ready",
            storage_region="workbench",
        )
    )
    session.commit()
    yield session, artist
    session.close()


def test_sign_and_verify_roundtrip():
    payload = {"artist_id": 1, "claim_type": "credit", "value": {"name": "A"}}
    sig, fingerprint = sign_payload(payload)
    assert verify_signature(payload, sig, fingerprint)
    assert not verify_signature({"artist_id": 2}, sig, fingerprint)


def test_ingest_writes_unsigned_drafts(db):
    session, artist = db
    rows = ingest_asset(session, artist, "track-1", sources=["consent_flag"])
    assert rows
    assert all(r.status == "draft" for r in rows)
    assert all(r.signature is None for r in rows)


def test_public_rights_hides_drafts(db):
    session, artist = db
    ingest_asset(session, artist, "track-1", sources=["consent_flag"])
    bundle = get_public_rights(session, "track-1")
    assert bundle["claims"] == []


def test_confirm_signs_and_exposes(db):
    session, artist = db
    rows = ingest_asset(session, artist, "track-1", sources=["consent_flag"])
    cite = next(r for r in rows if r.claim_type == "consent_cite")
    confirm_claim(session, artist, cite.id, role="artist")
    session.commit()
    bundle = get_public_rights(session, "track-1")
    types = {c["claim_type"] for c in bundle["claims"]}
    assert "consent_cite" in types
    assert all(c["signature"] for c in bundle["claims"])
    checked = verify_claim(session, cite.id)
    assert checked["valid"] is True


def test_two_sources_two_drafts(db):
    session, artist = db
    insert_draft(
        session,
        artist,
        claim_type="identifiers",
        value={"isrc": "USAAA0000001"},
        source="mlc",
        subject_asset_id="track-1",
    )
    insert_draft(
        session,
        artist,
        claim_type="identifiers",
        value={"isrc": "USAAA0000001"},
        source="musicbrainz",
        subject_asset_id="track-1",
    )
    session.commit()
    drafts = (
        session.query(AttestationClaim)
        .filter(AttestationClaim.status == "draft", AttestationClaim.claim_type == "identifiers")
        .all()
    )
    assert len(drafts) == 2
    assert {d.source for d in drafts} == {"mlc", "musicbrainz"}


def test_reject_keeps_out_of_rights(db):
    session, artist = db
    row = insert_draft(
        session,
        artist,
        claim_type="consent_train",
        value={"allowed": True},
        source="consent_flag",
        subject_asset_id="track-1",
    )
    reject_claim(session, artist, row.id)
    session.commit()
    bundle = get_public_rights(session, "track-1")
    assert bundle["claims"] == []


def test_mlc_never_auto_activates(db):
    session, artist = db
    insert_draft(
        session,
        artist,
        claim_type="split",
        value={"payee_name_or_id": "Writer", "percentage": 100, "right_type": "composition"},
        source="mlc",
        subject_asset_id="track-1",
    )
    session.commit()
    bundle = get_public_rights(session, "track-1")
    assert bundle["claims"] == []
    active = session.query(AttestationClaim).filter(AttestationClaim.status == "active").count()
    assert active == 0


def test_distributor_csv_parser():
    csv_text = "ISRC,Name,Share,Role\nUSAAA0000001,Ada,50,writer\nUSAAA0000001,Bo,50,writer\n"
    drafts = parse_distributor_csv(csv_text)
    types = {d["claim_type"] for d in drafts}
    assert "identifiers" in types
    assert "credit" in types
    assert "split" in types


def test_is_machine_request():
    class Req:
        def __init__(self, headers):
            self.headers = headers

    assert is_machine_request(Req({"accept": "application/json"}))
    assert is_machine_request(Req({"user-agent": "Mozilla/5.0 GPTBot", "accept": "*/*"}))
    assert not is_machine_request(
        Req({"accept": "text/html,application/xhtml+xml,application/json;q=0.9", "user-agent": "Mozilla/5.0"})
    )


def test_declarations_follow_active_train(db):
    session, artist = db
    row = insert_draft(
        session,
        artist,
        claim_type="consent_train",
        value={"allowed": True},
        source="consent_flag",
        subject_asset_id="track-1",
    )
    confirm_claim(session, artist, row.id)
    session.commit()
    body = robots_txt(session, artist, origin="https://pj.c0ll3ct1v3.xyz")
    assert "train-ai=y" in body
    assert "License:" in body
    tdm = tdmrep_json(session, artist)
    assert tdm["tdm"][0]["value"] == "0"

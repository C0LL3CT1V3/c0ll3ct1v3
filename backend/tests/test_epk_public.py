"""Tests for booker EPK public config."""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.artist import Artist
from app.models.media import MediaAsset
from app.schemas.epk_public_schemas import EpkPublicPatch
from app.services.epk_booker_completeness import evaluate_booker_completeness
from app.services.epk_public import (
    get_my_epk_public,
    patch_epk_public,
    publish_epk_public,
    resolve_epk_public,
)
from app.services.epk_public_config import coerce_epk_public


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        auth0_sub="auth0|test",
        tenant_slug="testartist",
        display_name="Test Artist",
        epk_config={"bio": "Fallback bio", "booking_email": "book@test.com"},
    )
    session.add(artist)
    session.commit()
    yield session, artist
    session.close()


def _image_asset(session, artist, asset_id="img1"):
    row = MediaAsset(
        id=asset_id,
        tenant_slug=artist.tenant_slug,
        title="Press photo",
        asset_type="image",
        status="ready",
        storage_region="workbench",
    )
    session.add(row)
    session.commit()
    return row


def test_coerce_epk_public_defaults():
    epk = coerce_epk_public({})
    assert epk.template == "booker_v1"
    assert epk.published is False


def test_patch_epk_public_photos(db):
    session, artist = db
    _image_asset(session, artist, "p1")
    _image_asset(session, artist, "p2")
    patch_epk_public(
        session,
        artist,
        EpkPublicPatch(
            photos=[{"asset_id": "p1", "caption": "Live"}, {"asset_id": "p2", "caption": ""}],
            bio="Long bio " * 30,
            booking_email="booker@venue.com",
        ),
    )
    epk = coerce_epk_public(artist.epk_config.get("epk_public"))
    assert len(epk.photos) == 2
    assert epk.bio.startswith("Long bio")


def test_evaluate_booker_completeness_partial(db):
    session, artist = db
    report = evaluate_booker_completeness(session, artist)
    assert report["required_score"] < 1.0
    assert any(i["id"] == "hero_video" for i in report["items"])


def test_get_my_epk_public_includes_completeness(db):
    session, artist = db
    data = get_my_epk_public(session, artist)
    assert "config" in data
    assert "completeness" in data
    assert data["completeness"]["items"]


def test_publish_requires_minimum_readiness(db):
    session, artist = db
    with pytest.raises(HTTPException) as exc:
        publish_epk_public(session, artist)
    assert exc.value.status_code == 400


def test_resolve_epk_public_bio_fallback(db):
    session, artist = db
    patch_epk_public(session, artist, EpkPublicPatch(bio=""))
    resolved = resolve_epk_public(session, artist)
    assert resolved["bio"] == "Fallback bio"

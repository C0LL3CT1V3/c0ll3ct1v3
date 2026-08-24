"""Tests for artist Homebase (events + Square pay)."""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.account import BankAccount  # noqa: F401
from app.models.artist import Artist
from app.models.media import MediaAsset  # noqa: F401
from app.models.store import Product  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vision import Vision  # noqa: F401
from app.schemas.homebase_schemas import HomebaseEvent, HomebasePatch, HomebasePayPatch
from app.services.homebase import (
    coerce_homebase,
    get_public_homebase,
    patch_homebase,
    publish_homebase,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        auth0_sub="auth0|homebase",
        tenant_slug="testartist",
        display_name="Test Artist",
        epk_config={"bio": "Fallback bio"},
    )
    session.add(artist)
    session.commit()
    yield session, artist
    session.close()


def test_coerce_homebase_defaults():
    hb = coerce_homebase({})
    assert hb.published is False
    assert hb.headline == ""
    assert hb.events == []
    assert hb.pay.enabled is True
    assert hb.pay.amounts == [5, 10, 20]
    assert hb.pay.button_label == "Pay"


def test_coerce_ignores_legacy_tip_provider_urls():
    hb = coerce_homebase(
        {
            "tips": {
                "enabled": True,
                "blurb": "Fuel the van",
                "amounts": [5, 10],
                "venmo": "@pjames",
                "stripe_link": "https://buy.stripe.com/x",
            }
        }
    )
    assert hb.pay.blurb == "Fuel the van"
    assert hb.pay.amounts == [5, 10]
    assert not hasattr(hb.pay, "venmo") or not getattr(hb.pay, "venmo", None)


def test_unpublished_public_homebase_is_404(db):
    session, artist = db
    with pytest.raises(HTTPException) as exc:
        get_public_homebase(session, artist.tenant_slug)
    assert exc.value.status_code == 404
    assert "not found or not published" in str(exc.value.detail).lower()


def test_missing_artist_public_homebase_is_404(db):
    session, _artist = db
    with pytest.raises(HTTPException) as exc:
        get_public_homebase(session, "no-such-slug")
    assert exc.value.status_code == 404


def test_publish_then_public_shape(db):
    session, artist = db
    patch_homebase(
        session,
        artist,
        HomebasePatch(
            headline="See you out there",
            events=[
                HomebaseEvent(
                    id="later",
                    title="Late show",
                    start="2026-10-01T21:00:00-06:00",
                    venue="The Later",
                    city="Denver",
                    ticket_url="https://tickets.example.com/late",
                ),
                HomebaseEvent(
                    id="sooner",
                    title="Early show",
                    start="2026-09-12T20:00:00-06:00",
                    venue="The sooner",
                    city="Boulder",
                ),
            ],
            pay=HomebasePayPatch(
                enabled=True,
                blurb="Fuel the van",
                amounts=[5, 10, 25],
                button_label="Tip me",
            ),
        ),
    )
    publish_homebase(session, artist)

    data = get_public_homebase(session, artist.tenant_slug)
    assert data["published"] is True
    assert data["tenant_slug"] == "testartist"
    assert data["display_name"] == "Test Artist"
    assert data["headline"] == "See you out there"
    assert [e["title"] for e in data["events"]] == ["Early show", "Late show"]
    assert data["events"][0]["venue"] == "The sooner"
    assert "tips" not in data or data.get("tips") is None
    assert data["pay"]["blurb"] == "Fuel the van"
    assert data["pay"]["amounts"] == [5, 10, 25]
    assert data["pay"]["button_label"] == "Tip me"
    assert "venmo" not in data["pay"]
    assert data["page_url"].endswith("/homebase")
    assert "checkout_available" in data


def test_url_sanitize_strips_unsafe_ticket_url(db):
    session, artist = db
    patch_homebase(
        session,
        artist,
        HomebasePatch(
            events=[
                HomebaseEvent(
                    title="Bad ticket",
                    start="2026-09-01T20:00:00Z",
                    ticket_url="javascript:alert(1)",
                ),
            ],
        ),
    )
    publish_homebase(session, artist)
    data = get_public_homebase(session, artist.tenant_slug)
    assert data["events"][0]["ticket_url"] == ""


def test_event_image_asset_must_be_vault_image(db):
    session, artist = db
    session.add(
        MediaAsset(
            id="img1",
            tenant_slug=artist.tenant_slug,
            title="Flyer",
            asset_type="image",
            status="ready",
            storage_region="workbench",
        )
    )
    session.add(
        MediaAsset(
            id="aud1",
            tenant_slug=artist.tenant_slug,
            title="Track",
            asset_type="audio",
            status="ready",
            storage_region="workbench",
        )
    )
    session.commit()

    with pytest.raises(HTTPException) as exc:
        patch_homebase(
            session,
            artist,
            HomebasePatch(
                events=[HomebaseEvent(title="Show", start="2026-09-01T20:00:00Z", image_asset_id="aud1")],
            ),
        )
    assert exc.value.status_code == 400

    patch_homebase(
        session,
        artist,
        HomebasePatch(
            events=[HomebaseEvent(title="Show", start="2026-09-01T20:00:00Z", image_asset_id="img1")],
        ),
    )
    publish_homebase(session, artist)
    data = get_public_homebase(session, artist.tenant_slug)
    assert data["events"][0]["image_asset_id"] == "img1"
    assert data["events"][0]["image_url"]
    assert "homebase/media/img1" in data["events"][0]["image_url"]
    assert "c0ll3ct1v3.xyz" not in data["events"][0]["image_url"]

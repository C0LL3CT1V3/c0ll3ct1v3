"""Tests for public musician profile API."""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.artist import Artist
from app.models.media import MediaAsset  # noqa: F401
from app.services.profile_public import get_public_profile, is_profile_published, render_public_profile_html


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        id=1,
        auth0_sub="auth0|pub",
        tenant_slug="coolband",
        display_name="Cool Band",
        epk_config={
            "tagline": "indie forever",
            "bio": "We make noise.",
            "profile_published": True,
            "profile_page": {
                "format": "html_v1",
                "html": "<main><h1>Cool Band</h1></main>",
                "css": "body { margin: 0; }",
                "asset_bindings": {},
            },
        },
    )
    session.add(artist)
    session.commit()
    yield session, artist
    session.close()


def test_is_profile_published(db_session):
    session, artist = db_session
    assert is_profile_published(artist)


def test_get_public_profile_html_v1(db_session):
    session, artist = db_session
    payload = get_public_profile(session, "coolband")
    assert payload["format"] == "html_v1"
    assert payload["profile_published"] is True
    assert payload["display_name"] == "Cool Band"


def test_render_public_profile_html(db_session):
    session, artist = db_session
    html = render_public_profile_html(session, "coolband")
    assert "<main>" in html
    assert "Cool Band" in html


def test_render_requires_published(db_session):
    session, artist = db_session
    artist.epk_config = dict(artist.epk_config)
    artist.epk_config["profile_published"] = False
    session.commit()
    with pytest.raises(HTTPException) as exc:
        render_public_profile_html(session, "coolband")
    assert exc.value.status_code == 404

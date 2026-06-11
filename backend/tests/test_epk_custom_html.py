"""Tests for custom HTML/CSS draft save."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.artist import Artist
from app.models.media import MediaAsset  # noqa: F401
from app.models.vision import Vision  # noqa: F401
from app.services.epk_html_draft import is_html_draft
from app.services.manager_epk_service import save_draft
from app.services.epk_html_draft import normalize_html_draft


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        id=1,
        auth0_sub="auth0|custom",
        tenant_slug="custom",
        display_name="Custom Artist",
        epk_config={},
    )
    session.add(artist)
    session.commit()
    yield session, artist
    session.close()


def test_normalize_and_save_custom_html(db_session):
    session, artist = db_session
    draft = normalize_html_draft(
        html="<main><h1>Hi</h1></main>",
        css="body { color: red; }",
        spec_snapshot="Custom HTML/CSS",
    )
    save_draft(session, artist, draft)
    assert is_html_draft(artist.epk_draft)
    assert "<script" not in (artist.epk_draft.get("html") or "")


def test_sanitize_strips_script_in_custom():
    draft = normalize_html_draft(
        html="<main>ok</main><script>alert(1)</script>",
        css="body {}",
    )
    assert "<script" not in draft["html"]

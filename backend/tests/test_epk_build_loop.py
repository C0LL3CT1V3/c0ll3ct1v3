"""Tests for EPK build loop (mocked LLM + Playwright)."""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.artist import Artist
from app.models.manager import ManagerThread
from app.models.media import MediaAsset
from app.models.vision import Vision
from app.services.epk_build_loop import build_epk_from_vision


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        id=1,
        auth0_sub="auth0|test",
        tenant_slug="test",
        display_name="Test Artist",
        epk_config={},
    )
    session.add(artist)
    vision = Vision(tenant_slug="test", title="Launch", sort_order=0)
    session.add(vision)
    session.commit()
    asset = MediaAsset(
        id="img1",
        tenant_slug="test",
        title="Hero",
        asset_type="image",
        status="ready",
        storage_region="workbench",
        vision_id=vision.id,
        tags={"vision_role": "media"},
    )
    session.add(asset)
    session.commit()
    thread = ManagerThread(artist_id=artist.id, mode="epk_builder", vision_id=vision.id)
    session.add(thread)
    session.commit()
    yield session, artist, vision, thread
    session.close()


@patch("app.services.epk_build_loop.capture_sim_screenshot", return_value=None)
@patch("app.services.epk_build_loop.critique_epk_screenshot")
@patch("app.services.epk_build_loop.generate_epk_html")
def test_build_epk_from_vision_persists_html_draft(mock_gen, mock_critique, _shot, db_session):
    session, artist, vision, thread = db_session
    mock_gen.return_value = {
        "reasoning_summary": "Built MVP.",
        "html": "<main><h1>Test</h1><img src='{{hero_photo}}' /></main>",
        "css": "body { margin: 0; }",
        "asset_bindings": {"hero_photo": "img1"},
    }
    mock_critique.return_value = {
        "match_score": 0.7,
        "major_gaps": [],
        "should_revise": False,
        "critique_summary": "Good enough for artist review.",
    }

    result = build_epk_from_vision(
        session,
        artist,
        thread,
        vision_id=vision.id,
        spec="Dark minimal country EPK",
    )

    assert result["format"] == "html_v1"
    assert artist.epk_draft["format"] == "html_v1"
    assert result["iteration_id"]
    assert result["sim_render_url"]
    assert mock_gen.call_count >= 1

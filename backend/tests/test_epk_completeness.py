"""Tests for EPK press-kit completeness evaluator."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.artist import Artist
from app.models.media import MediaAsset  # noqa: F401
from app.models.vision import Vision  # noqa: F401
from app.services.epk_completeness import evaluate_epk_completeness


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        id=1,
        auth0_sub="auth0|epk",
        tenant_slug="test",
        display_name="Test Artist",
        epk_config={
            "bio": "A" * 200,
            "booking_email": "book@test.com",
            "social": {"spotify": "https://open.spotify.com/artist/x", "instagram": "https://instagram.com/test"},
            "profile_published": True,
        },
        epk_draft={
            "format": "html_v1",
            "html": "<main><section class='music'>tracks</section><a href='mailto:book@test.com'>book</a></main>",
            "css": "body {}",
            "asset_bindings": {},
        },
    )
    session.add(artist)
    for i, asset_type in enumerate(["audio", "audio", "image", "image", "image", "image", "video"]):
        session.add(
            MediaAsset(
                id=f"a{i}",
                tenant_slug="test",
                title=f"Asset {i}",
                asset_type=asset_type,
                status="ready",
                storage_region="workbench",
            )
        )
    session.commit()
    yield session, artist
    session.close()


def test_evaluate_epk_completeness_ready_essentials(db_session):
    session, artist = db_session
    report = evaluate_epk_completeness(session, artist)
    assert report["required_score"] >= 0.8
    by_id = {item["id"]: item for item in report["items"]}
    assert by_id["music_tracks"]["status"] == "ready"
    assert by_id["photos"]["status"] == "ready"
    assert by_id["custom_page"]["status"] == "ready"
    assert by_id["go_live"]["status"] == "ready"
    assert report["summary"]


def test_evaluate_flags_missing_music(db_session):
    session, artist = db_session
    session.query(MediaAsset).filter(MediaAsset.asset_type == "audio").delete()
    session.commit()
    report = evaluate_epk_completeness(session, artist)
    gaps = {g["id"] for g in report["gaps"]}
    assert "music_tracks" in gaps

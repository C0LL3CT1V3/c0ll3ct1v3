"""Tests for html_v1 annotation refine path."""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.artist import Artist
from app.models.manager import EpkIteration
from app.services.epk_html_draft import normalize_html_draft
from app.services.manager_epk_service import annotate_iteration, refine_iteration


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        auth0_sub="auth0|refine",
        tenant_slug="refineartist",
        display_name="Refine Artist",
    )
    session.add(artist)
    session.commit()
    yield session, artist
    session.close()


def test_html_v1_annotate_and_refine(db):
    session, artist = db
    draft = normalize_html_draft(
        html="<main><h1>Hello</h1></main>",
        css="body { margin: 0; }",
        asset_bindings={},
        vision_id="v1",
        spec_snapshot="gritty",
    )
    parent = EpkIteration(
        artist_id=artist.id,
        step="generate",
        user_prompt="gritty page",
        design_after=draft,
        context_snapshot={"format": "html_v1", "spec": "gritty"},
    )
    session.add(parent)
    session.commit()
    session.refresh(parent)

    annotate_iteration(
        session,
        artist,
        parent.id,
        [{"note": "Make heading bigger", "bbox_norm": {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.1}, "component_ids": []}],
        None,
    )
    session.refresh(parent)
    assert parent.annotations_resolved

    with patch("app.services.manager_epk_service.refine_epk_html_from_annotations") as mock_refine:
        mock_refine.return_value = {
            "reasoning_summary": "Bigger heading",
            "html": "<main><h1 class='big'>Hello</h1></main>",
            "css": "body { margin: 0; } h1.big { font-size: 3rem; }",
            "asset_bindings": {},
        }
        child, preview, _, _ = refine_iteration(session, artist, parent)

    assert child.id != parent.id
    assert preview["format"] == "html_v1"
    assert "big" in (preview.get("html") or "")

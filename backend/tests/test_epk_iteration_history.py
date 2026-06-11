"""Tests for EPK design iteration history."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.artist import Artist
from app.models.manager import EpkIteration
from app.models.media import MediaAsset  # noqa: F401 — register FK tables
from app.models.vision import Vision  # noqa: F401
from app.services.epk_html_draft import draft_content_hash, normalize_html_draft
from app.services.epk_sim_token import mint_sim_token, verify_sim_token
from app.services.manager_epk_service import (
    get_epk_iteration_preview,
    list_epk_iterations,
    restore_epk_iteration,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    artist = Artist(
        id=1,
        auth0_sub="auth0|hist",
        tenant_slug="test",
        display_name="History Artist",
        epk_config={},
    )
    session.add(artist)
    session.commit()
    yield session, artist
    session.close()


def _html_iteration(db_session, artist, *, html="<main>v1</main>", spec="Dark hero"):
    draft = normalize_html_draft(
        html=html,
        css="body { margin: 0; }",
        vision_id="vision-1",
        spec_snapshot=spec,
    )
    row = EpkIteration(
        artist_id=artist.id,
        step="generate",
        user_prompt=spec,
        context_snapshot={"format": "html_v1", "spec": spec, "revision_cycles": 1},
        reasoning_summary="First proposal",
        design_patch={"format": "html_v1"},
        design_after=draft,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_sim_token_with_iteration_id_roundtrip():
    token = mint_sim_token(artist_id=1, draft_hash="abc123", iteration_id="iter-1")
    info = verify_sim_token(token)
    assert info["artist_id"] == 1
    assert info["draft_hash"] == "abc123"
    assert info["iteration_id"] == "iter-1"


def test_list_epk_iterations_newest_first(db_session):
    session, artist = db_session
    first = _html_iteration(session, artist, html="<main>one</main>", spec="One")
    second = _html_iteration(session, artist, html="<main>two</main>", spec="Two")
    rows = list_epk_iterations(session, artist)
    assert len(rows) == 2
    ids = {row["id"] for row in rows}
    assert first.id in ids
    assert second.id in ids
    assert rows[0]["format"] == "html_v1"


def test_get_iteration_preview_includes_sim_url(db_session):
    session, artist = db_session
    row = _html_iteration(session, artist)
    preview = get_epk_iteration_preview(session, artist, row.id)
    assert preview["format"] == "html_v1"
    assert preview["sim_render_url"]
    assert row.id in preview["sim_render_url"]
    assert preview["html"] == "<main>v1</main>"


def test_restore_epk_iteration_sets_current_draft(db_session):
    session, artist = db_session
    row = _html_iteration(session, artist, html="<main>restored</main>")
    restore_epk_iteration(session, artist, row.id)
    assert artist.epk_draft["html"] == "<main>restored</main>"
    assert draft_content_hash(artist.epk_draft) == draft_content_hash(row.design_after)


def test_restore_missing_iteration_raises(db_session):
    session, artist = db_session
    with pytest.raises(HTTPException) as exc:
        restore_epk_iteration(session, artist, "missing-id")
    assert exc.value.status_code == 404

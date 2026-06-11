"""Tests for vision pack partitions and slot rules."""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.media import MediaAsset
from app.models.vision import Vision
from app.services.url_reference import create_url_reference_asset
from app.services.vision_pack import (
    apply_folder_assignment,
    apply_vision_assignment,
    get_vision_pack,
    validate_vision_role_assignment,
    vision_role_from_tags,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    vision = Vision(tenant_slug="test", title="EPK v1", sort_order=0)
    session.add(vision)
    session.commit()
    yield session, vision
    session.close()


def _asset(session, vision_id, role, asset_type="image", asset_id="a1"):
    row = MediaAsset(
        id=asset_id,
        tenant_slug="test",
        title=f"{role}-{asset_id}",
        asset_type=asset_type,
        status="ready",
        storage_region="workbench",
        vision_id=vision_id,
        tags={"vision_role": role},
    )
    session.add(row)
    session.commit()
    return row


def test_vision_role_from_tags_defaults_media():
    assert vision_role_from_tags({}) == "media"
    assert vision_role_from_tags({"vision_role": "wireframe"}) == "wireframe"


def test_wireframe_slot_limit(db):
    session, vision = db
    _asset(session, vision.id, "wireframe", asset_id="wf1")
    second = MediaAsset(
        id="wf2",
        tenant_slug="test",
        title="wf2",
        asset_type="image",
        status="ready",
    )
    with pytest.raises(HTTPException) as exc:
        validate_vision_role_assignment(
            session,
            asset=second,
            vision_id=vision.id,
            vision_role="wireframe",
        )
    assert exc.value.status_code == 400


def test_reference_limit_three(db):
    session, vision = db
    for i in range(3):
        _asset(session, vision.id, "reference", asset_id=f"ref{i}")
    extra = MediaAsset(
        id="ref3",
        tenant_slug="test",
        title="ref3",
        asset_type="image",
        status="ready",
    )
    with pytest.raises(HTTPException):
        validate_vision_role_assignment(
            session,
            asset=extra,
            vision_id=vision.id,
            vision_role="reference",
        )


def test_get_vision_pack_partitions(db):
    session, vision = db
    _asset(session, vision.id, "wireframe", asset_id="wf")
    _asset(session, vision.id, "reference", asset_id="r1")
    _asset(session, vision.id, "media", asset_id="m1", asset_type="audio")

    pack = get_vision_pack(session, vision.id, "test")
    assert pack["wireframe"]["id"] == "wf"
    assert len(pack["references"]) == 1
    assert len(pack["media"]) == 1
    assert pack["counts"]["media"] == 1


def test_apply_folder_assignment_no_role(db):
    session, vision = db
    asset = MediaAsset(
        id="folder1",
        tenant_slug="test",
        title="track",
        asset_type="audio",
        status="ready",
        storage_region="workbench",
    )
    session.add(asset)
    session.commit()
    apply_folder_assignment(session, asset, vision_id=vision.id)
    assert asset.vision_id == vision.id
    assert "vision_role" not in (asset.tags or {})


def test_url_reference_in_vision_pack(db):
    session, vision = db
    asset = create_url_reference_asset(
        session,
        tenant_slug="test",
        vision_id=vision.id,
        url="https://example.com/ref.png",
    )
    pack = get_vision_pack(session, vision.id, "test")
    assert len(pack["references"]) == 1
    assert pack["references"][0]["id"] == asset.id
    assert pack["references"][0]["preview_url"] == "https://example.com/ref.png"


def test_apply_vision_assignment_clears_on_null(db):
    session, vision = db
    asset = _asset(session, vision.id, "media", asset_id="m1")
    apply_vision_assignment(session, asset, vision_id=None, vision_role=None)
    assert asset.vision_id is None
    assert "vision_role" not in (asset.tags or {})

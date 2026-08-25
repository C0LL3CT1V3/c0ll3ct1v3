from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.account import BankAccount  # noqa: F401
from app.models.artist import Artist  # noqa: F401
from app.models.media import MediaAsset, MediaUpload
from app.models.store import Product  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vision import Vision  # noqa: F401
from app.services.deploy_gate import SKIP_AUTH_PATHS, count_inflight_uploads, evaluate


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _asset(db):
    asset = MediaAsset(
        tenant_slug="test",
        title="take",
        asset_type="audio",
        status="inbox",
        visibility="private",
        storage_region="workbench",
        tags={},
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def test_count_skips_completed_uploads():
    db = _session()
    asset = _asset(db)
    db.add(
        MediaUpload(
            asset_id=asset.id,
            s3_upload_id="s3",
            inbox_storage_key="k",
            status="completed",
            expected_byte_size=1,
            part_count=1,
        )
    )
    db.commit()
    assert count_inflight_uploads(db) == 0


def test_count_inflight_uploading():
    db = _session()
    asset = _asset(db)
    db.add(
        MediaUpload(
            asset_id=asset.id,
            s3_upload_id="s3",
            inbox_storage_key="k",
            status="uploading",
            expected_byte_size=1,
            part_count=1,
        )
    )
    db.commit()
    assert count_inflight_uploads(db) == 1


def test_count_ignores_stale_inflight():
    db = _session()
    asset = _asset(db)
    row = MediaUpload(
        asset_id=asset.id,
        s3_upload_id="s3",
        inbox_storage_key="k",
        status="uploading",
        expected_byte_size=1,
        part_count=1,
    )
    db.add(row)
    db.commit()
    row.created_at = datetime.now(timezone.utc) - timedelta(hours=5)
    db.commit()
    assert count_inflight_uploads(db) == 0


def test_evaluate_ready_when_idle_and_no_uploads():
    db = _session()
    result = evaluate(db)
    assert result["ready"] is True
    assert result["inflight_uploads"] == 0
    assert result["redis"] == "unused"


def test_evaluate_blocks_on_upload():
    db = _session()
    asset = _asset(db)
    db.add(
        MediaUpload(
            asset_id=asset.id,
            s3_upload_id="s3",
            inbox_storage_key="k",
            status="initiating",
            expected_byte_size=1,
            part_count=1,
        )
    )
    db.commit()
    result = evaluate(db)
    assert result["ready"] is False
    assert "inflight_uploads" in result["reasons"]


def test_health_path_not_tracked():
    assert "/health" in SKIP_AUTH_PATHS

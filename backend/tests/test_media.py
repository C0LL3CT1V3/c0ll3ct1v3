"""Tests for creative media module."""

from app.models.media import MediaAsset, MediaJob, MediaUpload, MediaVariant, MediaVersion
from app.schemas.media_schemas import UploadInitBody


def test_media_models_import():
    assert MediaAsset.__tablename__ == "media_assets"
    assert MediaVersion.__tablename__ == "media_versions"
    assert MediaVariant.__tablename__ == "media_variants"
    assert MediaUpload.__tablename__ == "media_uploads"
    assert MediaJob.__tablename__ == "media_jobs"


def test_upload_init_body_validation():
    body = UploadInitBody(
        filename="track.wav",
        mime_type="audio/wav",
        byte_size=1024,
        asset_type="audio",
    )
    assert body.asset_type == "audio"

"""Tests for storage path helpers."""

import pytest

from app.services.storage_paths import (
    assert_gallery_key,
    assert_workbench_key,
    gallery_delivery_key,
    gallery_derived_key,
    is_public_delivery_key,
    workbench_master_key,
)


def test_workbench_master_key():
    key = workbench_master_key("phillipjames", "abc", 1, "track.wav")
    assert key == "tenants/phillipjames/workbench/abc/v1/track.wav"
    assert_workbench_key(key)


def test_gallery_delivery_key():
    key = gallery_delivery_key("phillipjames", "content-uuid", 2, "published.jpg")
    assert "/gallery/delivery/content-uuid/r2/published.jpg" in key
    assert_gallery_key(key)
    assert is_public_delivery_key(key)


def test_gallery_derived_key():
    key = gallery_derived_key("phillipjames", "cid", 1, "web_mp3", "stream.mp3")
    assert "/derived/web_mp3/stream.mp3" in key


def test_assert_workbench_rejects_gallery():
    with pytest.raises(ValueError):
        assert_workbench_key("tenants/x/gallery/delivery/y/r1/f.jpg")

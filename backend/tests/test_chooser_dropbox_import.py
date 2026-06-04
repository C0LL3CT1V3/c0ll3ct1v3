"""Tests for Dropbox Chooser direct-link import helpers."""

import pytest
from fastapi import HTTPException

from app.services.chooser_dropbox_import import validate_dropbox_chooser_url


def test_validate_dropbox_chooser_url_accepts_cdn():
    url = validate_dropbox_chooser_url(
        "https://dl.dropboxusercontent.com/cd/0/get/abc/file.jpg",
    )
    assert url.startswith("https://")


def test_validate_dropbox_chooser_url_rejects_other_hosts():
    with pytest.raises(HTTPException) as exc:
        validate_dropbox_chooser_url("https://evil.example.com/file.jpg")
    assert exc.value.status_code == 400


def test_validate_dropbox_chooser_url_requires_https():
    with pytest.raises(HTTPException):
        validate_dropbox_chooser_url("http://dl.dropboxusercontent.com/x")

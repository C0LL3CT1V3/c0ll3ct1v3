"""Tests for Google Picker import helpers."""

import pytest
from fastapi import HTTPException

from app.services.chooser_google_import import validate_google_file_id


def test_validate_google_file_id_accepts_drive_ids():
    assert validate_google_file_id("abc123XYZ_-") == "abc123XYZ_-"


def test_validate_google_file_id_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        validate_google_file_id("  ")
    assert exc.value.status_code == 400


def test_validate_google_file_id_rejects_unsafe_chars():
    with pytest.raises(HTTPException):
        validate_google_file_id("file/id")

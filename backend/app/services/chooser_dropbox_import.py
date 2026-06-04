"""Download files from Dropbox Chooser direct links (server-side; avoids browser CORS)."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from ..config import settings

_ALLOWED_HOST_SUFFIXES = (
    "dropboxusercontent.com",
    "dropbox.com",
)


def validate_dropbox_chooser_url(url: str) -> str:
    """Only allow HTTPS links returned by the official Chooser (direct / content CDN)."""
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Dropbox link must use HTTPS.")
    host = (parsed.hostname or "").lower()
    if not host or not any(host == suffix or host.endswith(f".{suffix}") for suffix in _ALLOWED_HOST_SUFFIXES):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid Dropbox download link.")
    return url.strip()


async def download_dropbox_chooser_link(url: str, *, expected_bytes: int | None = None) -> bytes:
    safe_url = validate_dropbox_chooser_url(url)
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        res = await client.get(safe_url)
    if res.status_code >= 400:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"Dropbox download failed ({res.status_code}).",
        )
    data = res.content
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Dropbox returned an empty file.")
    if len(data) > settings.media_max_upload_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File exceeds maximum upload size.")
    if expected_bytes and expected_bytes > 0 and len(data) != expected_bytes:
        # Chooser byte count can be slightly stale; only reject large mismatches.
        if abs(len(data) - expected_bytes) > max(1024, expected_bytes // 20):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Downloaded file size does not match Dropbox selection.",
            )
    return data

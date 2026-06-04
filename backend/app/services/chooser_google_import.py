"""Download files from Google Picker selections (server-side; avoids browser CORS)."""

from __future__ import annotations

import re

import httpx
from fastapi import HTTPException, status

from ..config import settings

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

_GOOGLE_EXPORT_MIMES = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "application/pdf",
}

_FILE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_google_file_id(file_id: str) -> str:
    fid = file_id.strip()
    if not fid or not _FILE_ID_RE.match(fid):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid Google Drive file id.")
    return fid


async def download_google_picker_file(
    access_token: str,
    *,
    file_id: str,
    name: str | None = None,
    mime_type: str | None = None,
) -> tuple[str, str, bytes]:
    """Download one Picker-selected file using the user's short-lived GIS access token."""
    token = access_token.strip()
    if not token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Google access token is required.")

    fid = validate_google_file_id(file_id)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=120.0) as client:
        meta_res = await client.get(
            f"{DRIVE_FILES_URL}/{fid}",
            params={"fields": "id,name,mimeType,size"},
            headers=headers,
        )
        if meta_res.status_code == 401:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Google access token expired or invalid.")
        if meta_res.status_code >= 400:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Google Drive file not found.")

        meta = meta_res.json()
        mime = mime_type or meta.get("mimeType") or "application/octet-stream"
        resolved_name = (name or meta.get("name") or "import").strip() or "import"

        if mime.startswith("application/vnd.google-apps."):
            export_mime = _GOOGLE_EXPORT_MIMES.get(mime, "application/pdf")
            res = await client.get(
                f"{DRIVE_FILES_URL}/{fid}/export",
                params={"mimeType": export_mime},
                headers=headers,
            )
            ext = ".pdf" if "pdf" in export_mime else ".csv"
            if not resolved_name.lower().endswith(ext):
                resolved_name = f"{resolved_name}{ext}"
            mime = export_mime
        else:
            res = await client.get(
                f"{DRIVE_FILES_URL}/{fid}",
                params={"alt": "media"},
                headers=headers,
            )

        if res.status_code >= 400:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Google Drive download failed.")

        content = res.content

    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Google Drive returned an empty file.")
    if len(content) > settings.media_max_upload_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File exceeds maximum upload size.")

    return resolved_name, mime, content

"""Google Drive API — list and download using per-user OAuth tokens."""

from __future__ import annotations

import io
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.cloud_connection import CloudConnection
from .cloud_oauth import ensure_fresh_token

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
MEDIA_QUERY = (
    "trashed=false and ("
    "mimeType contains 'image/' or mimeType contains 'audio/' or mimeType contains 'video/' "
    "or mimeType='application/zip' or mimeType='application/pdf'"
    ")"
)


async def get_google_connection(db: Session, artist_id: int) -> CloudConnection:
    row = (
        db.query(CloudConnection)
        .filter(CloudConnection.artist_id == artist_id, CloudConnection.provider == "google")
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Connect Google Drive first.")
    return row


async def list_google_files(
    db: Session,
    artist_id: int,
    *,
    page_token: str | None = None,
) -> dict[str, Any]:
    conn = await get_google_connection(db, artist_id)
    token = await ensure_fresh_token(db, conn)
    params = {
        "q": MEDIA_QUERY,
        "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime)",
        "pageSize": 50,
        "orderBy": "modifiedTime desc",
    }
    if page_token:
        params["pageToken"] = page_token

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(
            DRIVE_FILES_URL,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
    if res.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Could not list Google Drive files.")
    data = res.json()
    files = []
    for f in data.get("files", []):
        mime = f.get("mimeType") or ""
        is_folder = mime == "application/vnd.google-apps.folder"
        files.append(
            {
                "id": f["id"],
                "name": f.get("name") or "Untitled",
                "mime_type": mime,
                "size": int(f["size"]) if f.get("size") else None,
                "is_folder": is_folder,
            }
        )
    return {"files": files, "next_page_token": data.get("nextPageToken")}


async def download_google_file(db: Session, artist_id: int, file_id: str) -> tuple[str, str, bytes]:
    conn = await get_google_connection(db, artist_id)
    token = await ensure_fresh_token(db, conn)

    async with httpx.AsyncClient(timeout=120.0) as client:
        meta_res = await client.get(
            f"{DRIVE_FILES_URL}/{file_id}",
            params={"fields": "id,name,mimeType,size"},
            headers={"Authorization": f"Bearer {token}"},
        )
        if meta_res.status_code >= 400:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Google Drive file not found.")
        meta = meta_res.json()
        mime = meta.get("mimeType") or "application/octet-stream"
        name = meta.get("name") or "import"

        if mime.startswith("application/vnd.google-apps."):
            export_mime = {
                "application/vnd.google-apps.document": "application/pdf",
                "application/vnd.google-apps.spreadsheet": "text/csv",
                "application/vnd.google-apps.presentation": "application/pdf",
            }.get(mime, "application/pdf")
            res = await client.get(
                f"{DRIVE_FILES_URL}/{file_id}/export",
                params={"mimeType": export_mime},
                headers={"Authorization": f"Bearer {token}"},
            )
            ext = ".pdf" if "pdf" in export_mime else ".csv"
            if not name.lower().endswith(ext):
                name = f"{name}{ext}"
            mime = export_mime
        else:
            res = await client.get(
                f"{DRIVE_FILES_URL}/{file_id}",
                params={"alt": "media"},
                headers={"Authorization": f"Bearer {token}"},
            )

        if res.status_code >= 400:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Google Drive download failed.")
        content = res.content

    return name, mime, content

"""Dropbox API — list and download using per-user OAuth tokens."""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.cloud_connection import CloudConnection
from .cloud_oauth import ensure_fresh_token

MEDIA_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp3",
    ".wav",
    ".flac",
    ".m4a",
    ".mp4",
    ".mov",
    ".webm",
    ".zip",
    ".pdf",
)


async def get_dropbox_connection(db: Session, artist_id: int) -> CloudConnection:
    row = (
        db.query(CloudConnection)
        .filter(CloudConnection.artist_id == artist_id, CloudConnection.provider == "dropbox")
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Connect Dropbox first.")
    return row


def _is_media_entry(entry: dict) -> bool:
    if entry.get(".tag") == "folder":
        return True
    name = (entry.get("name") or "").lower()
    return any(name.endswith(ext) for ext in MEDIA_EXTENSIONS)


async def list_dropbox_files(db: Session, artist_id: int) -> dict[str, Any]:
    conn = await get_dropbox_connection(db, artist_id)
    token = await ensure_fresh_token(db, conn)

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            "https://api.dropboxapi.com/2/files/list_folder",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"path": "", "recursive": False, "limit": 100},
        )
    if res.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Could not list Dropbox files.")
    data = res.json()
    files = []
    for entry in data.get("entries", []):
        if not _is_media_entry(entry):
            continue
        tag = entry.get(".tag")
        files.append(
            {
                "id": entry.get("path_display") or entry.get("path_lower") or entry.get("id", ""),
                "name": entry.get("name") or "Untitled",
                "mime_type": None,
                "size": entry.get("size"),
                "is_folder": tag == "folder",
            }
        )
    return {"files": files, "next_page_token": None}


async def download_dropbox_file(db: Session, artist_id: int, path: str) -> tuple[str, str, bytes]:
    conn = await get_dropbox_connection(db, artist_id)
    token = await ensure_fresh_token(db, conn)

    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(
            "https://content.dropboxapi.com/2/files/download",
            headers={
                "Authorization": f"Bearer {token}",
                "Dropbox-API-Arg": json.dumps({"path": path}),
            },
        )
    if res.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Dropbox download failed.")

    name = path.rsplit("/", 1)[-1] or "import"
    mime = "application/octet-stream"
    return name, mime, res.content

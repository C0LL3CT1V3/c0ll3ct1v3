"""
RQ worker entrypoints for creative media ingestion (probe + derivatives).

Runs in a dedicated container with ffmpeg available.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from .config import settings
from .database import SessionLocal
from .models.media import MediaAsset, MediaJob, MediaVariant, MediaVersion
from .services.spaces_storage import get_s3_client

log = logging.getLogger(__name__)


def run_media_job(job_id: str) -> None:
    """RQ handler: execute a single ingest job."""
    db: Session = SessionLocal()
    try:
        row = db.query(MediaJob).filter(MediaJob.id == job_id).first()
        if not row:
            log.warning("media job %s not found", job_id)
            return
        if row.status == "succeeded":
            return

        row.status = "running"
        db.commit()
        try:
            ingest_version_media(db, row.version_id)
        except Exception:
            db.rollback()
            row = db.query(MediaJob).filter(MediaJob.id == job_id).first()
            ver = (
                db.query(MediaVersion)
                .options(joinedload(MediaVersion.asset))
                .filter(MediaVersion.id == row.version_id)
                .first()
                if row
                else None
            )
            if ver and ver.asset:
                if ver.asset.status == "processing":
                    ver.asset.status = "ready"
                db.commit()
            row = db.query(MediaJob).filter(MediaJob.id == job_id).first()
            if row:
                row.status = "failed"
                row.error_message = "ingest failed; see logs"
                db.commit()
            raise

        row = db.query(MediaJob).filter(MediaJob.id == job_id).first()
        if row:
            row.status = "succeeded"
            db.commit()
    finally:
        db.close()


def ingest_version_media(db: Session, version_id: str) -> None:
    """Run ffprobe then optional ffmpeg derivations."""
    client = get_s3_client()
    ver = (
        db.query(MediaVersion)
        .options(joinedload(MediaVersion.asset))
        .filter(MediaVersion.id == version_id)
        .first()
    )
    if not ver or not ver.asset:
        raise RuntimeError("Version not found")

    asset = ver.asset
    with tempfile.TemporaryDirectory() as td:
        src_path = os.path.join(td, "source" + Path(ver.original_filename).suffix)
        dest_dir = Path(td)
        client.download_file(settings.spaces_bucket, ver.storage_key, src_path)

        _ffprobe_and_update_version(ver, src_path, db)

        tenant = asset.tenant_slug
        if ver.mime_type.startswith("audio/"):
            mp3_path = dest_dir / "out.mp3"
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                src_path,
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(mp3_path),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            variant_key = f"tenants/{tenant}/public/{asset.id}/{ver.id}_web.mp3"
            client.upload_file(
                str(mp3_path),
                settings.spaces_bucket,
                variant_key,
                ExtraArgs={"ContentType": "audio/mpeg"},
            )
            _upsert_variant(
                db,
                ver,
                variant_kind="web_mp3",
                storage_key=variant_key,
                mime_type="audio/mpeg",
                byte_size=os.path.getsize(mp3_path),
            )
        elif ver.mime_type.startswith("image/"):
            _ingest_image_variants(db, client, asset, ver, src_path, dest_dir, tenant)

    if asset.status == "processing":
        asset.status = "ready"
    db.commit()


def _ingest_image_variants(
    db: Session,
    client,
    asset: MediaAsset,
    ver: MediaVersion,
    src_path: str,
    dest_dir: Path,
    tenant: str,
) -> None:
    """Create a display variant; fall back to copying the master if ffmpeg fails."""
    web_path = dest_dir / "display.webp"
    out_mime = "image/webp"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                src_path,
                "-vf",
                "scale=min(1400,iw):-1",
                str(web_path),
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        log.warning("ffmpeg display variant failed for %s; using master copy", ver.id)
        suffix = Path(src_path).suffix or ".bin"
        web_path = dest_dir / f"display{suffix}"
        import shutil

        shutil.copy2(src_path, web_path)
        out_mime = ver.mime_type or "application/octet-stream"

    if not web_path.is_file():
        raise RuntimeError("Could not produce image display variant")

    variant_key = f"tenants/{tenant}/public/{asset.id}/{ver.id}_display{web_path.suffix}"
    client.upload_file(
        str(web_path),
        settings.spaces_bucket,
        variant_key,
        ExtraArgs={"ContentType": out_mime},
    )
    _upsert_variant(
        db,
        ver,
        variant_kind="display_webp",
        storage_key=variant_key,
        mime_type=out_mime,
        byte_size=os.path.getsize(web_path),
    )


def _ffprobe_and_update_version(version: MediaVersion, local_path: str, db: Session) -> None:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", local_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if proc.returncode != 0 or not proc.stdout:
            return
        data = json.loads(proc.stdout)
        fmt = data.get("format") or {}
        duration_s = fmt.get("duration")
        if duration_s:
            version.duration_ms = int(float(duration_s) * 1000)
        for stream in data.get("streams") or []:
            if stream.get("codec_type") == "video" and stream.get("width"):
                version.width = int(stream["width"])
                version.height = int(stream.get("height") or 0) or None
                break
        db.merge(version)
        db.flush()
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        return


def _upsert_variant(
    db: Session,
    ver: MediaVersion,
    *,
    variant_kind: str,
    storage_key: str,
    mime_type: str,
    byte_size: int,
) -> None:
    existing = (
        db.query(MediaVariant)
        .filter(
            MediaVariant.version_id == ver.id,
            MediaVariant.variant_kind == variant_kind,
        )
        .first()
    )
    if existing:
        existing.storage_key = storage_key
        existing.mime_type = mime_type
        existing.byte_size = byte_size
        existing.ready = True
        db.merge(existing)
    else:
        row = MediaVariant(
            version_id=ver.id,
            variant_kind=variant_kind,
            storage_key=storage_key,
            mime_type=mime_type,
            byte_size=byte_size,
            ready=True,
        )
        db.add(row)


def ingest_version_inline(db: Session, version_id: str) -> None:
    """Run ingestion without RQ (dev / no Redis)."""
    ingest_version_media(db, version_id)

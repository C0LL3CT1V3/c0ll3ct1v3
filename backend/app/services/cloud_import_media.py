"""Import cloud file bytes into workbench storage."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..models.media import MediaAsset, MediaJob, MediaVersion
from ..models.user import User
from .media_type import infer_asset_type, infer_mime_type
from .spaces_storage import get_s3_client, head_object_bytes
from .storage_paths import workbench_master_key
from ..worker_tasks import ingest_version_inline

_IMAGE_MAX = 52_428_800


def import_bytes_to_workbench(
    db: Session,
    *,
    tenant_slug: str,
    created_by: str | None,
    filename: str,
    mime_type: str,
    data: bytes,
) -> MediaAsset:
    if len(data) > settings.media_max_upload_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File exceeds maximum upload size.")

    fname = Path(filename).name
    if ".." in fname:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    resolved_mime = infer_mime_type(fname, mime_type)
    resolved_type = infer_asset_type(fname, resolved_mime, "document")

    if resolved_type == "image" and len(data) > _IMAGE_MAX:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Images are limited to 50 MiB.")

    if not settings.spaces_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Object storage is disabled.")

    suffix = Path(fname).suffix.lower() or ".bin"
    safe_stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", Path(fname).stem)[:200] or "file"
    storage_key = workbench_master_key(tenant_slug, "pending", 1, f"{safe_stem}{suffix}")

    asset = MediaAsset(
        tenant_slug=tenant_slug,
        title=safe_stem,
        asset_type=resolved_type,
        status="processing",
        visibility="private",
        storage_region="workbench",
        tags={"import_source": "cloud"},
        created_by=created_by,
    )
    db.add(asset)
    db.flush()

    storage_key = workbench_master_key(tenant_slug, asset.id, 1, f"{safe_stem}{suffix}")
    client = get_s3_client()
    client.put_object(
        Bucket=settings.spaces_bucket,
        Key=storage_key,
        Body=data,
        ContentType=resolved_mime,
    )
    byte_size = head_object_bytes(client, storage_key) or len(data)

    ver = MediaVersion(
        asset_id=asset.id,
        version_number=1,
        is_current=True,
        storage_key=storage_key,
        original_filename=f"{safe_stem}{suffix}",
        mime_type=resolved_mime,
        byte_size=byte_size,
    )
    db.add(ver)
    db.flush()

    job = MediaJob(version_id=ver.id, job_type="ingest", status="pending")
    db.add(job)
    db.commit()
    db.refresh(asset)

    if settings.redis_url:
        from .media_queue import enqueue_media_ingest_job

        enqueue_media_ingest_job(job.id)
    else:
        try:
            ingest_version_inline(db, ver.id)
            job.status = "succeeded"
            asset.status = "ready"
            db.commit()
        except Exception:
            asset.status = "ready"
            job.status = "failed"
            db.commit()

    db.refresh(asset)
    return asset

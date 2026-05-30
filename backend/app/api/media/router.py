"""Admin media API (Auth0) — presigned multipart upload and asset CRUD."""

from __future__ import annotations

import math
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user
from ...config import settings
from ...database import get_db
from ...models.media import MediaAsset, MediaJob, MediaUpload, MediaVariant, MediaVersion
from ...models.user import User
from ...services.artist_service import tenant_slug_for_user
from ...services.epk_media_resolve import best_image_variant, url_for_variant
from ...schemas.media_schemas import (
    AssetDetail,
    AssetListItem,
    AssetUpdateBody,
    UploadCompleteBody,
    UploadCompleteResponse,
    UploadInitBody,
    UploadInitResponse,
    VariantOut,
    VersionOut,
    PublishResponse,
)
from ...services.media_queue import enqueue_media_ingest_job
from ...services.media_type import infer_asset_type, infer_mime_type
from ...services.spaces_storage import (
    abort_multipart_upload,
    complete_multipart_upload,
    create_multipart_upload,
    get_s3_client,
    head_object_bytes,
    presigned_get_object,
    presigned_upload_part,
    copy_object_to_key,
    public_url_for_key,
)
from ...worker_tasks import ingest_version_inline

router = APIRouter(prefix="/media", tags=["media"])

_FILENAME_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")
IMAGE_MAX_BYTES = 52_428_800  # 50 MiB


def _require_storage() -> None:
    if not settings.spaces_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is disabled. Set SPACES_ENABLED=true and configure Spaces/MinIO.",
        )


def _assert_asset_in_user_workspace(asset: MediaAsset, db: Session, user: User) -> None:
    allowed = tenant_slug_for_user(db, user)
    if asset.tenant_slug != allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found.")


def _tenant_slug(body: UploadInitBody, db: Session, current_user: User) -> str:
    allowed = tenant_slug_for_user(db, current_user)
    if body.tenant_slug:
        requested = body.tenant_slug.strip().lower()
        if requested != allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Cannot upload to another artist workspace.",
            )
        return requested
    return allowed


def _storage_client():
    _require_storage()
    try:
        return get_s3_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def _heal_stuck_processing_assets(db: Session, tenant_slug: str) -> None:
    """Unblock uploads when ingest jobs failed but the master file exists."""
    stuck = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions))
        .filter(
            MediaAsset.tenant_slug == tenant_slug,
            MediaAsset.status == "processing",
            MediaAsset.is_deleted.is_(False),
        )
        .all()
    )
    if not stuck:
        return
    changed = False
    for asset in stuck:
        ver = next((v for v in asset.versions if v.is_current), None)
        if not ver:
            continue
        job = (
            db.query(MediaJob)
            .filter(MediaJob.version_id == ver.id)
            .order_by(MediaJob.created_at.desc())
            .first()
        )
        if job and job.status == "failed" and ver.mime_type.startswith("image/"):
            try:
                ingest_version_inline(db, ver.id)
                job.status = "succeeded"
                job.error_message = None
                asset.status = "ready"
                changed = True
                continue
            except Exception:
                db.rollback()
        if job and job.status in ("failed", "succeeded"):
            asset.status = "ready"
            changed = True
    if changed:
        db.commit()


def _variant_to_out(v: MediaVariant) -> VariantOut:
    url = None
    if "/public/" in v.storage_key:
        url = public_url_for_key(v.storage_key)
    return VariantOut(
        id=v.id,
        variant_kind=v.variant_kind,
        storage_key=v.storage_key,
        mime_type=v.mime_type,
        byte_size=v.byte_size,
        ready=v.ready,
        stream_url=url,
    )


def _version_to_out(v: MediaVersion) -> VersionOut:
    return VersionOut(
        id=v.id,
        version_number=v.version_number,
        is_current=v.is_current,
        storage_key=v.storage_key,
        original_filename=v.original_filename,
        mime_type=v.mime_type,
        byte_size=v.byte_size,
        checksum_sha256=v.checksum_sha256,
        duration_ms=v.duration_ms,
        width=v.width,
        height=v.height,
        variants=[_variant_to_out(x) for x in getattr(v, "variants", []) or []],
    )


@router.post("/uploads/init", response_model=UploadInitResponse)
def init_upload(
    body: UploadInitBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadInitResponse:
    client = _storage_client()

    if body.byte_size > settings.media_max_upload_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File exceeds configured maximum size.")
    fname = Path(body.filename).name
    if fname != body.filename or ".." in body.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    resolved_type = infer_asset_type(fname, body.mime_type, body.asset_type)
    resolved_mime = infer_mime_type(fname, body.mime_type)

    if resolved_type == "image" and body.byte_size > IMAGE_MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Images are limited to 50 MiB in v1.")

    tenant = _tenant_slug(body, db, current_user)

    suffix = Path(fname).suffix.lower() or ".bin"
    safe_stem = _FILENAME_SAFE.sub("_", Path(fname).stem)[:200] or "file"

    asset = MediaAsset(
        tenant_slug=tenant,
        title=body.title or safe_stem,
        asset_type=resolved_type,
        status="inbox",
        visibility="private",
        tags={},
        created_by=current_user.auth0_sub or str(current_user.id),
    )
    db.add(asset)
    db.flush()

    version_number = 1
    upload_row = MediaUpload(
        asset_id=asset.id,
        s3_upload_id="",
        inbox_storage_key="",
        status="initiating",
        expected_byte_size=body.byte_size,
        mime_type=resolved_mime,
        part_count=0,
    )
    db.add(upload_row)
    db.flush()

    storage_key = f"tenants/{tenant}/masters/{asset.id}/v{version_number}/{safe_stem}{suffix}"
    try:
        s3_upload_id = create_multipart_upload(client, storage_key, resolved_mime)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Storage init failed: {exc}") from exc

    chunk = settings.media_multipart_chunk_bytes
    part_count = max(1, math.ceil(body.byte_size / chunk))
    upload_row.s3_upload_id = s3_upload_id
    upload_row.inbox_storage_key = storage_key
    upload_row.part_count = part_count
    upload_row.status = "uploading"
    db.commit()
    db.refresh(upload_row)

    parts = []
    for pn in range(1, part_count + 1):
        url = presigned_upload_part(client, storage_key, s3_upload_id, pn)
        parts.append({"part_number": pn, "url": url})

    return UploadInitResponse(
        asset_id=asset.id,
        upload_row_id=upload_row.id,
        multipart_storage_key=storage_key,
        s3_upload_id=s3_upload_id,
        parts=parts,
        chunk_size_bytes=chunk,
    )


@router.post("/uploads/complete", response_model=UploadCompleteResponse)
def complete_upload(
    body: UploadCompleteBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadCompleteResponse:
    client = _storage_client()

    upload = db.query(MediaUpload).filter(MediaUpload.id == body.upload_row_id).first()
    if not upload or upload.status not in {"uploading", "initiating"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Upload session not found or already finalized.")

    asset = db.query(MediaAsset).filter(MediaAsset.id == upload.asset_id, MediaAsset.is_deleted.is_(False)).first()
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset missing.")

    _assert_asset_in_user_workspace(asset, db, current_user)

    if len(body.parts) != upload.part_count:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Expected {upload.part_count} parts, received {len(body.parts)}.",
        )

    etag_parts = [
        {"ETag": p.etag if p.etag.startswith('"') else f'"{p.etag.strip()}"', "PartNumber": p.part_number}
        for p in sorted(body.parts, key=lambda x: x.part_number)
    ]

    key = upload.inbox_storage_key
    try:
        complete_multipart_upload(client, key, upload.s3_upload_id, etag_parts)
    except Exception as exc:  # noqa: BLE001
        abort_multipart_upload(client, key, upload.s3_upload_id)
        upload.status = "failed"
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Could not complete multipart upload: {exc}") from exc

    actual_size = head_object_bytes(client, key)
    byte_size = actual_size if actual_size is not None else upload.expected_byte_size

    upload.status = "completed"
    asset.status = "processing"

    ext = Path(key).suffix.lower()
    fname = Path(key).name
    mime_guess = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".zip": "application/zip",
        ".mov": "video/quicktime",
        ".mp4": "video/mp4",
    }.get(ext, "application/octet-stream")
    resolved_mime = infer_mime_type(fname, upload.mime_type or mime_guess)
    asset.asset_type = infer_asset_type(fname, resolved_mime, asset.asset_type)
    ver = MediaVersion(
        asset_id=asset.id,
        version_number=1,
        is_current=True,
        storage_key=key,
        original_filename=Path(key).name,
        mime_type=resolved_mime,
        byte_size=byte_size,
    )

    db.add(ver)
    db.flush()

    job = MediaJob(version_id=ver.id, job_type="ingest", status="pending")
    db.add(job)
    db.commit()
    db.refresh(ver)
    db.refresh(job)

    if settings.redis_url:
        enqueue_media_ingest_job(job.id)
    else:
        try:
            ingest_version_inline(db, ver.id)
            job.status = "succeeded"
            db.commit()
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error_message = str(exc)[:8192]
            asset.status = "ready"
            db.commit()

    return UploadCompleteResponse(asset_id=asset.id, version_id=ver.id, storage_key=key)


@router.get("/assets", response_model=list[AssetListItem])
def list_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = None,
    asset_type: str | None = None,
) -> list[AssetListItem]:
    workspace = tenant_slug_for_user(db, current_user)
    _heal_stuck_processing_assets(db, workspace)
    q = db.query(MediaAsset).filter(MediaAsset.is_deleted.is_(False), MediaAsset.tenant_slug == workspace)
    if status_filter:
        q = q.filter(MediaAsset.status == status_filter)
    if asset_type:
        q = q.filter(MediaAsset.asset_type == asset_type)
    return q.order_by(MediaAsset.created_at.desc()).limit(200).all()


@router.get("/assets/{asset_id}", response_model=AssetDetail)
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetDetail:
    row = (
        db.query(MediaAsset)
        .options(
            joinedload(MediaAsset.versions).joinedload(MediaVersion.variants),
        )
        .filter(MediaAsset.id == asset_id, MediaAsset.is_deleted.is_(False))
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    _assert_asset_in_user_workspace(row, db, current_user)
    return AssetDetail(
        id=row.id,
        tenant_slug=row.tenant_slug,
        title=row.title,
        asset_type=row.asset_type,
        status=row.status,
        visibility=row.visibility,
        tags=row.tags or {},
        created_at=row.created_at,
        versions=[_version_to_out(v) for v in row.versions],
    )


@router.patch("/assets/{asset_id}", response_model=AssetDetail)
def update_asset(
    asset_id: str,
    body: AssetUpdateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetDetail:
    row = db.query(MediaAsset).filter(MediaAsset.id == asset_id, MediaAsset.is_deleted.is_(False)).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    _assert_asset_in_user_workspace(row, db, current_user)
    if body.title is not None:
        row.title = body.title
    if body.tags is not None:
        row.tags = body.tags
    if body.status is not None:
        if body.status not in {"inbox", "processing", "ready", "published", "archived"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid status.")
        row.status = body.status
    db.commit()
    db.refresh(row)
    return get_asset(asset_id, db, current_user)


@router.delete(
    "/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    row = db.query(MediaAsset).filter(MediaAsset.id == asset_id, MediaAsset.is_deleted.is_(False)).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    _assert_asset_in_user_workspace(row, db, current_user)
    row.is_deleted = True
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/assets/{asset_id}/publish", response_model=PublishResponse)
def publish_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishResponse:
    """Copy current master variant to `public/` and mark asset published."""
    client = _storage_client()
    asset = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions).joinedload(MediaVersion.variants))
        .filter(MediaAsset.id == asset_id, MediaAsset.is_deleted.is_(False))
        .first()
    )
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    _assert_asset_in_user_workspace(asset, db, current_user)
    ver = next((v for v in asset.versions if v.is_current), None)
    if not ver:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No current version to publish.")

    tenant = asset.tenant_slug
    ext = Path(ver.storage_key).suffix or ".bin"
    dest_key = f"tenants/{tenant}/public/{asset.id}/published{ext}"
    try:
        copy_object_to_key(client, ver.storage_key, dest_key, content_type=ver.mime_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Publish copy failed: {exc}") from exc

    actual = head_object_bytes(client, dest_key) or ver.byte_size
    existing = (
        db.query(MediaVariant)
        .filter(MediaVariant.version_id == ver.id, MediaVariant.variant_kind == "published_delivery")
        .first()
    )
    if existing:
        existing.storage_key = dest_key
        existing.mime_type = ver.mime_type
        existing.byte_size = actual
        existing.ready = True
    else:
        db.add(
            MediaVariant(
                version_id=ver.id,
                variant_kind="published_delivery",
                storage_key=dest_key,
                mime_type=ver.mime_type,
                byte_size=actual,
                ready=True,
            )
        )
    asset.status = "published"
    asset.visibility = "public"
    db.commit()
    refreshed = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions).joinedload(MediaVersion.variants))
        .filter(MediaAsset.id == asset_id)
        .first()
    )
    ver = next((v for v in (refreshed.versions if refreshed else []) if v.is_current), None)
    pub_variants = [
        _variant_to_out(v) for v in (ver.variants if ver else []) if v.ready and "/public/" in v.storage_key
    ]
    return PublishResponse(asset_id=asset.id, public_variants=pub_variants)


@router.get("/assets/{asset_id}/preview-url")
def preview_url(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str | None]:
    """Presigned or public URL for portal thumbnails."""
    row = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions).joinedload(MediaVersion.variants))
        .filter(MediaAsset.id == asset_id, MediaAsset.is_deleted.is_(False))
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    _assert_asset_in_user_workspace(row, db, current_user)
    ver = next((v for v in row.versions if v.is_current), None)
    if not ver:
        return {"url": None}
    if row.asset_type == "image":
        best = best_image_variant(ver)
        if best:
            return {"url": url_for_variant(best)}
    try:
        client = _storage_client()
        return {"url": presigned_get_object(client, ver.storage_key)}
    except Exception:
        return {"url": None}


@router.get("/assets/{asset_id}/download")
def download_master_url(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    client = _storage_client()
    asset = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions))
        .filter(MediaAsset.id == asset_id, MediaAsset.is_deleted.is_(False))
        .first()
    )
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    _assert_asset_in_user_workspace(asset, db, current_user)
    ver = next((v for v in asset.versions if v.is_current), None)
    if not ver:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No version available.")
    url = presigned_get_object(client, ver.storage_key)
    return {"url": url, "filename": ver.original_filename}

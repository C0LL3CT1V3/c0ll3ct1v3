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
from ...models.vision import Vision
from ...models.user import User
from ...services.artist_service import tenant_slug_for_user
from ...services.media_variants import best_image_variant, url_for_variant
from ...schemas.media_schemas import (
    AssetDetail,
    AssetListItem,
    AssetUpdateBody,
    ReferenceUrlBody,
    ChooserDropboxImportBody,
    ChooserDropboxImportOut,
    ChooserGoogleImportBody,
    ChooserGoogleImportOut,
    ChooserImportResultItem,
    UploadCompleteBody,
    UploadCompleteResponse,
    UploadInitBody,
    UploadInitResponse,
    VariantOut,
    VersionOut,
)
from ...services.chooser_dropbox_import import download_dropbox_chooser_link
from ...services.chooser_google_import import download_google_picker_file
from ...services.cloud_import_media import import_bytes_to_workbench
from ...services.media_queue import enqueue_media_ingest_job
from ...schemas.vision_schemas import (
    VisionCreateBody,
    VisionOut,
    VisionPackOut,
    VisionUpdateBody,
    WorkbenchOut,
)
from ...services.url_reference import create_url_reference_asset, external_url_from_asset
from ...services.vision_pack import (
    apply_folder_assignment,
    apply_vision_assignment,
    get_vision_pack,
    vision_role_from_tags,
)
from ...services.storage_paths import workbench_master_key, is_public_delivery_key
from ...services.media_type import infer_asset_type, infer_mime_type
from ...services.spaces_storage import (
    abort_multipart_upload,
    complete_multipart_upload,
    create_multipart_upload,
    get_s3_client,
    head_object_bytes,
    presigned_get_object,
    presigned_upload_part,
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
            detail="Object storage is disabled. Set SPACES_ENABLED=true and configure S3 (AWS bucket, Spaces, or MinIO).",
        )


def _assert_asset_in_user_workspace(asset: MediaAsset, db: Session, user: User) -> None:
    allowed = tenant_slug_for_user(db, user)
    if asset.tenant_slug != allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found.")


def _tenant_slug(body: UploadInitBody, db: Session, current_user: User) -> str:
    return _resolve_tenant_slug(body.tenant_slug, db, current_user)


def _resolve_tenant_slug(requested: str | None, db: Session, current_user: User) -> str:
    allowed = tenant_slug_for_user(db, current_user)
    if requested:
        slug = requested.strip().lower()
        if slug != allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Cannot upload to another artist workspace.",
            )
        return slug
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
    if is_public_delivery_key(v.storage_key):
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
        storage_region="workbench",
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

    storage_key = workbench_master_key(tenant, asset.id, version_number, f"{safe_stem}{suffix}")
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


@router.post("/chooser/dropbox/import", response_model=ChooserDropboxImportOut)
async def dropbox_chooser_import(
    body: ChooserDropboxImportBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChooserDropboxImportOut:
    """Import files selected via Dropbox Chooser (server downloads direct links)."""
    _require_storage()
    tenant = _resolve_tenant_slug(body.tenant_slug, db, current_user)
    created_by = current_user.auth0_sub or str(current_user.id)
    imported: list[ChooserImportResultItem] = []

    for item in body.items:
        data = await download_dropbox_chooser_link(item.link, expected_bytes=item.bytes)
        mime = infer_mime_type(item.name, "application/octet-stream")
        asset = import_bytes_to_workbench(
            db,
            tenant_slug=tenant,
            created_by=created_by,
            filename=item.name,
            mime_type=mime,
            data=data,
        )
        imported.append(ChooserImportResultItem(asset_id=asset.id, title=asset.title))

    return ChooserDropboxImportOut(imported=imported)


@router.post("/chooser/google/import", response_model=ChooserGoogleImportOut)
async def google_picker_import(
    body: ChooserGoogleImportBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChooserGoogleImportOut:
    """Import files selected via Google Picker (server downloads with user's GIS token)."""
    _require_storage()
    tenant = _resolve_tenant_slug(body.tenant_slug, db, current_user)
    created_by = current_user.auth0_sub or str(current_user.id)
    imported: list[ChooserImportResultItem] = []

    for item in body.items:
        name, mime, data = await download_google_picker_file(
            body.access_token,
            file_id=item.id,
            name=item.name,
            mime_type=item.mime_type,
        )
        resolved_mime = infer_mime_type(name, mime)
        asset = import_bytes_to_workbench(
            db,
            tenant_slug=tenant,
            created_by=created_by,
            filename=name,
            mime_type=resolved_mime,
            data=data,
        )
        imported.append(ChooserImportResultItem(asset_id=asset.id, title=asset.title))

    return ChooserGoogleImportOut(imported=imported)


@router.get("/workbench", response_model=WorkbenchOut)
def get_workbench(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkbenchOut:
    """Workbench assets and vision groups for the portal."""
    workspace = tenant_slug_for_user(db, current_user)
    _heal_stuck_processing_assets(db, workspace)
    visions = (
        db.query(Vision)
        .filter(Vision.tenant_slug == workspace)
        .order_by(Vision.sort_order.asc(), Vision.created_at.asc())
        .all()
    )
    assets = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.is_deleted.is_(False),
            MediaAsset.tenant_slug == workspace,
            MediaAsset.storage_region == "workbench",
        )
        .order_by(MediaAsset.created_at.desc())
        .limit(500)
        .all()
    )
    return WorkbenchOut(visions=visions, assets=assets)


@router.get("/assets", response_model=list[AssetListItem])
def list_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = None,
    asset_type: str | None = None,
) -> list[AssetListItem]:
    workspace = tenant_slug_for_user(db, current_user)
    _heal_stuck_processing_assets(db, workspace)
    q = db.query(MediaAsset).filter(
        MediaAsset.is_deleted.is_(False),
        MediaAsset.tenant_slug == workspace,
        MediaAsset.storage_region == "workbench",
    )
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
        storage_region=row.storage_region or "workbench",
        gallery_stage=row.gallery_stage,
        gallery_rev=row.gallery_rev,
        parent_asset_id=row.parent_asset_id,
        content_id=row.content_id,
        vision_id=row.vision_id,
        tags=row.tags or {},
        created_at=row.created_at,
        versions=[_version_to_out(v) for v in row.versions],
    )


@router.post("/reference-urls", response_model=AssetDetail)
def create_reference_url(
    body: ReferenceUrlBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetDetail:
    """Add an external URL as a vision reference (no upload)."""
    workspace = tenant_slug_for_user(db, current_user)
    asset = create_url_reference_asset(
        db,
        tenant_slug=workspace,
        vision_id=body.vision_id,
        url=body.url,
        created_by=current_user.auth0_sub or str(current_user.id),
    )
    return get_asset(asset.id, db, current_user)


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
        if body.status not in {"inbox", "processing", "ready", "archived"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid status.")
        row.status = body.status
    patch_fields = body.model_dump(exclude_unset=True)
    vision_id = row.vision_id if "vision_id" not in patch_fields else body.vision_id
    vision_role = body.vision_role if "vision_role" in patch_fields else None

    if "vision_id" in patch_fields or "vision_role" in patch_fields:
        if "vision_role" not in patch_fields:
            apply_folder_assignment(db, row, vision_id=vision_id)
        elif vision_id is None and vision_role is None and "vision_id" in patch_fields:
            apply_vision_assignment(db, row, vision_id=None, vision_role=None)
        else:
            if vision_id:
                vision = (
                    db.query(Vision)
                    .filter(Vision.id == vision_id, Vision.tenant_slug == row.tenant_slug)
                    .first()
                )
                if not vision:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vision not found.")
            resolved_role = vision_role
            if vision_id and resolved_role is None:
                resolved_role = vision_role_from_tags(row.tags)
            apply_vision_assignment(
                db,
                row,
                vision_id=vision_id,
                vision_role=resolved_role,
            )
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


@router.get("/visions", response_model=list[VisionOut])
def list_visions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[VisionOut]:
    workspace = tenant_slug_for_user(db, current_user)
    return (
        db.query(Vision)
        .filter(Vision.tenant_slug == workspace)
        .order_by(Vision.sort_order.asc(), Vision.created_at.asc())
        .all()
    )


@router.post("/visions", response_model=VisionOut, status_code=status.HTTP_201_CREATED)
def create_vision(
    body: VisionCreateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VisionOut:
    workspace = tenant_slug_for_user(db, current_user)
    max_order = (
        db.query(Vision.sort_order)
        .filter(Vision.tenant_slug == workspace)
        .order_by(Vision.sort_order.desc())
        .first()
    )
    next_order = (max_order[0] + 1) if max_order and max_order[0] is not None else 0
    row = Vision(tenant_slug=workspace, title=body.title.strip(), sort_order=next_order)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/visions/{vision_id}", response_model=VisionOut)
def update_vision(
    vision_id: str,
    body: VisionUpdateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VisionOut:
    workspace = tenant_slug_for_user(db, current_user)
    row = db.query(Vision).filter(Vision.id == vision_id, Vision.tenant_slug == workspace).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vision not found.")
    if body.title is not None:
        row.title = body.title.strip()
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    db.commit()
    db.refresh(row)
    return row


@router.get("/visions/{vision_id}/pack", response_model=VisionPackOut)
def get_vision_pack_route(
    vision_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VisionPackOut:
    workspace = tenant_slug_for_user(db, current_user)
    return VisionPackOut(**get_vision_pack(db, vision_id, workspace))


@router.delete(
    "/visions/{vision_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_vision(
    vision_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    workspace = tenant_slug_for_user(db, current_user)
    row = db.query(Vision).filter(Vision.id == vision_id, Vision.tenant_slug == workspace).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vision not found.")
    db.query(MediaAsset).filter(MediaAsset.vision_id == vision_id).update({"vision_id": None})
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    external = external_url_from_asset(row)
    if external:
        return {"url": external}
    ver = next((v for v in row.versions if v.is_current), None)
    if not ver:
        return {"url": None}
    if row.storage_region == "gallery" and row.gallery_stage == "released":
        if row.asset_type == "image":
            best = best_image_variant(ver)
            if best:
                return {"url": url_for_variant(best)}
        for v in ver.variants:
            if v.ready and is_public_delivery_key(v.storage_key):
                return {"url": url_for_variant(v)}
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

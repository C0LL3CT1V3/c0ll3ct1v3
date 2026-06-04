"""Promote workbench masters into immutable gallery delivery objects."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models.media import MediaAsset, MediaJob, MediaVariant, MediaVersion
from .spaces_storage import copy_object_to_key, get_s3_client, head_object_bytes
from .storage_paths import (
    gallery_derived_key,
    gallery_promote_dest_key,
    normalize_content_id,
)

log = logging.getLogger(__name__)

def promote_workbench_asset(
    db: Session,
    *,
    workbench_asset_id: str,
) -> MediaAsset:
    """Copy workbench master → gallery delivery; create gallery MediaAsset row. Workbench row unchanged."""
    wb = (
        db.query(MediaAsset)
        .options(joinedload(MediaAsset.versions).joinedload(MediaVersion.variants))
        .filter(MediaAsset.id == workbench_asset_id, MediaAsset.is_deleted.is_(False))
        .first()
    )
    if not wb:
        raise LookupError("Asset not found")
    if (wb.storage_region or "workbench") != "workbench":
        raise ValueError("Only workbench assets can be promoted.")
    if wb.status != "ready":
        raise ValueError(f"Asset must be ready before promote (status={wb.status}).")

    ver = next((v for v in wb.versions if v.is_current), None)
    if not ver:
        raise ValueError("No current version to promote.")

    content_id = normalize_content_id(wb.id, wb.content_id)
    rev = _next_gallery_rev(db, content_id)
    tenant = wb.tenant_slug
    filename = Path(ver.original_filename).name or Path(ver.storage_key).name
    dest_key = gallery_promote_dest_key(tenant, content_id, rev, filename)

    client = get_s3_client()
    copy_object_to_key(client, ver.storage_key, dest_key, content_type=ver.mime_type)
    actual = head_object_bytes(client, dest_key) or ver.byte_size

    gallery_asset = MediaAsset(
        tenant_slug=tenant,
        title=wb.title,
        asset_type=wb.asset_type,
        status="ready",
        visibility="public",
        tags=dict(wb.tags or {}),
        created_by=wb.created_by,
        storage_region="gallery",
        gallery_rev=rev,
        parent_asset_id=wb.id,
        gallery_stage="released",
        content_id=content_id,
    )
    db.add(gallery_asset)
    db.flush()

    g_ver = MediaVersion(
        asset_id=gallery_asset.id,
        version_number=1,
        is_current=True,
        storage_key=dest_key,
        original_filename=filename,
        mime_type=ver.mime_type,
        byte_size=actual,
        duration_ms=ver.duration_ms,
        width=ver.width,
        height=ver.height,
    )
    db.add(g_ver)
    db.flush()

    _generate_gallery_derivatives(db, client, gallery_asset, g_ver, content_id, rev, tenant)

    delivery_variant = MediaVariant(
        version_id=g_ver.id,
        variant_kind="published_delivery",
        storage_key=dest_key,
        mime_type=ver.mime_type,
        byte_size=actual,
        ready=True,
    )
    db.add(delivery_variant)
    db.commit()
    db.refresh(gallery_asset)
    return gallery_asset


def _next_gallery_rev(db: Session, content_id: str) -> int:
    latest = (
        db.query(MediaAsset.gallery_rev)
        .filter(
            MediaAsset.content_id == content_id,
            MediaAsset.storage_region == "gallery",
            MediaAsset.is_deleted.is_(False),
        )
        .order_by(MediaAsset.gallery_rev.desc())
        .first()
    )
    if latest and latest[0]:
        return int(latest[0]) + 1
    return 1


def _generate_gallery_derivatives(
    db: Session,
    client,
    asset: MediaAsset,
    ver: MediaVersion,
    content_id: str,
    rev: int,
    tenant: str,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        src_path = os.path.join(td, "source" + Path(ver.original_filename).suffix)
        client.download_file(settings.spaces_bucket, ver.storage_key, src_path)
        dest_dir = Path(td)

        if ver.mime_type.startswith("audio/"):
            mp3_path = dest_dir / "out.mp3"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    src_path,
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",
                    str(mp3_path),
                ],
                check=True,
                capture_output=True,
            )
            variant_key = gallery_derived_key(tenant, content_id, rev, "web_mp3", "stream.mp3")
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
                log.warning("ffmpeg display variant failed for gallery %s", ver.id)
                import shutil

                suffix = Path(src_path).suffix or ".bin"
                web_path = dest_dir / f"display{suffix}"
                shutil.copy2(src_path, web_path)
                out_mime = ver.mime_type

            variant_key = gallery_derived_key(tenant, content_id, rev, "display", web_path.name)
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
        .filter(MediaVariant.version_id == ver.id, MediaVariant.variant_kind == variant_kind)
        .first()
    )
    if existing:
        existing.storage_key = storage_key
        existing.mime_type = mime_type
        existing.byte_size = byte_size
        existing.ready = True
    else:
        db.add(
            MediaVariant(
                version_id=ver.id,
                variant_kind=variant_kind,
                storage_key=storage_key,
                mime_type=mime_type,
                byte_size=byte_size,
                ready=True,
            )
        )
    db.flush()

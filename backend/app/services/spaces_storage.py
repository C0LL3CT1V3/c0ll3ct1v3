"""S3-compatible object storage (DigitalOcean Spaces, MinIO, AWS S3)."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from ..config import settings


def _client_facing_url(url: str) -> str:
    """Rewrite presigned URLs for browsers when internal Docker hostname differs from public host."""
    internal = settings.spaces_endpoint.rstrip("/")
    public = (settings.spaces_public_endpoint or settings.spaces_endpoint).rstrip("/")
    if public and internal and public != internal and url.startswith(internal):
        return public + url[len(internal) :]
    return url


def _presign_client(client: BaseClient) -> BaseClient:
    """Use browser-facing endpoint for presigned URLs when different from internal endpoint.

    Important: presigning is local crypto only; it does not require network access to the endpoint.
    """
    public = (settings.spaces_public_endpoint or "").rstrip("/")
    internal = settings.spaces_endpoint.rstrip("/")
    if not public or public == internal:
        return client
    return boto3.client(
        "s3",
        endpoint_url=public,
        region_name=settings.spaces_region,
        aws_access_key_id=settings.spaces_access_key,
        aws_secret_access_key=settings.spaces_secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def get_s3_client() -> BaseClient:
    if not settings.spaces_enabled:
        raise RuntimeError("Object storage is disabled (SPACES_ENABLED=false).")
    if not all(
        [
            settings.spaces_endpoint,
            settings.spaces_bucket,
            settings.spaces_access_key,
            settings.spaces_secret_key,
        ]
    ):
        raise RuntimeError("Spaces configuration incomplete; set endpoint, bucket, access key, and secret key.")

    return boto3.client(
        "s3",
        endpoint_url=settings.spaces_endpoint.rstrip("/"),
        region_name=settings.spaces_region,
        aws_access_key_id=settings.spaces_access_key,
        aws_secret_access_key=settings.spaces_secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def public_url_for_key(storage_key: str) -> str:
    """Return browser URL for a public object (CDN if configured)."""
    base = settings.media_cdn_base_url.rstrip("/") if settings.media_cdn_base_url else ""
    if not base:
        # Virtual-host style: https://bucket.region.digitaloceanspaces.com/key
        ep = settings.spaces_endpoint.rstrip("/")
        if ".digitaloceanspaces.com" in ep and settings.spaces_bucket:
            # endpoint is often https://nyc3.digitaloceanspaces.com
            base = f"{ep}/{settings.spaces_bucket}"
        else:
            base = f"{ep}/{settings.spaces_bucket}"
    return f"{base}/{storage_key.lstrip('/')}"


def create_multipart_upload(client: BaseClient, key: str, content_type: str) -> str:
    resp = client.create_multipart_upload(
        Bucket=settings.spaces_bucket,
        Key=key,
        ContentType=content_type,
    )
    upload_id = resp.get("UploadId")
    if not upload_id:
        raise RuntimeError("create_multipart_upload returned no UploadId")
    return upload_id


def presigned_upload_part(
    client: BaseClient,
    key: str,
    upload_id: str,
    part_number: int,
) -> str:
    signer = _presign_client(client)
    url = signer.generate_presigned_url(
        ClientMethod="upload_part",
        Params={
            "Bucket": settings.spaces_bucket,
            "Key": key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=settings.media_presigned_upload_expires_seconds,
        HttpMethod="PUT",
    )
    return url


def complete_multipart_upload(
    client: BaseClient,
    key: str,
    upload_id: str,
    parts: list[dict[str, Any]],
) -> None:
    # parts: [{"ETag": '"..."', "PartNumber": 1}, ...]
    client.complete_multipart_upload(
        Bucket=settings.spaces_bucket,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": sorted(parts, key=lambda p: p["PartNumber"])},
    )


def abort_multipart_upload(client: BaseClient, key: str, upload_id: str) -> None:
    try:
        client.abort_multipart_upload(Bucket=settings.spaces_bucket, Key=key, UploadId=upload_id)
    except ClientError:
        pass


def copy_object_to_key(client: BaseClient, source_key: str, dest_key: str, content_type: str | None = None) -> None:
    src = f"{settings.spaces_bucket}/{source_key}"
    extra: dict[str, Any] = {
        "Bucket": settings.spaces_bucket,
        "Key": dest_key,
        "CopySource": src,
    }
    if content_type:
        extra["ContentType"] = content_type
        extra["MetadataDirective"] = "REPLACE"
    client.copy_object(**extra)


def delete_object(client: BaseClient, key: str) -> None:
    try:
        client.delete_object(Bucket=settings.spaces_bucket, Key=key)
    except ClientError:
        pass


def presigned_get_object(client: BaseClient, key: str) -> str:
    signer = _presign_client(client)
    url = signer.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.spaces_bucket, "Key": key},
        ExpiresIn=settings.media_presigned_download_expires_seconds,
        HttpMethod="GET",
    )
    return url


def head_object_bytes(client: BaseClient, key: str) -> int | None:
    try:
        r = client.head_object(Bucket=settings.spaces_bucket, Key=key)
        return int(r.get("ContentLength", 0))
    except ClientError:
        return None

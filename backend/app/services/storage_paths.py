"""Canonical object-key layout for workbench vs gallery zones (one bucket, hard prefixes)."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

TENANT_PREFIX = "tenants/"
WORKBENCH_SEGMENT = "workbench/"
GALLERY_SEGMENT = "gallery/"


def workbench_master_key(slug: str, asset_id: str, version: int, filename: str) -> str:
    safe = Path(filename).name
    return f"tenants/{slug}/workbench/{asset_id}/v{version}/{safe}"


def gallery_delivery_key(slug: str, content_id: str, rev: int, filename: str) -> str:
    safe = Path(filename).name
    return f"tenants/{slug}/gallery/delivery/{content_id}/r{rev}/{safe}"


def gallery_derived_key(slug: str, content_id: str, rev: int, kind: str, filename: str) -> str:
    safe = Path(filename).name
    return f"tenants/{slug}/gallery/delivery/{content_id}/r{rev}/derived/{kind}/{safe}"


def assert_workbench_key(key: str) -> None:
    if not _tenant_relative(key).startswith(WORKBENCH_SEGMENT):
        raise ValueError(f"Key must be under workbench/: {key}")


def assert_gallery_key(key: str) -> None:
    rel = _tenant_relative(key)
    if not rel.startswith(GALLERY_SEGMENT):
        raise ValueError(f"Key must be under gallery/: {key}")


def is_gallery_delivery_key(key: str) -> bool:
    return "/gallery/delivery/" in key


def is_legacy_public_key(key: str) -> bool:
    return "/public/" in key


def is_public_delivery_key(key: str) -> bool:
    """Keys safe to expose on public EPK (gallery delivery or legacy public/)."""
    return is_gallery_delivery_key(key) or is_legacy_public_key(key)


def gallery_promote_dest_key(slug: str, content_id: str, rev: int, filename: str) -> str:
    return gallery_delivery_key(slug, content_id, rev, filename)


def normalize_content_id(asset_id: str, existing: str | None = None) -> str:
    """ADR-001 interim: use asset.id until dedicated content_id is set."""
    if existing:
        try:
            UUID(str(existing))
            return str(existing)
        except ValueError:
            pass
    try:
        UUID(str(asset_id))
        return str(asset_id)
    except ValueError:
        raise ValueError(f"Invalid content id: {asset_id}") from None


def _tenant_relative(key: str) -> str:
    """Strip `tenants/{slug}/` so asserts work on full keys."""
    m = re.match(r"^tenants/[^/]+/(.+)$", key.lstrip("/"))
    if not m:
        raise ValueError(f"Key must start with tenants/{{slug}}/: {key}")
    return m.group(1)

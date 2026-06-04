#!/usr/bin/env python3
"""
Copy legacy MinIO keys: masters/* → workbench/, public/* → gallery/delivery/.
Does not delete originals (ADR-003).

Run inside the backend container (deps + MinIO network):

  docker compose -f docker-compose.dev.yml exec backend python scripts/migrate_storage_prefixes.py --dry-run

Local venv (from backend/):

  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
  .venv/bin/python scripts/migrate_storage_prefixes.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from botocore.exceptions import ClientError

from app.config import settings  # noqa: E402
from app.services.spaces_storage import copy_object_to_key, get_s3_client  # noqa: E402


def _remap_key(key: str) -> str | None:
    if "/masters/" in key:
        return key.replace("/masters/", "/workbench/", 1)
    if "/public/" in key:
        parts = key.split("/")
        try:
            pub_idx = parts.index("public")
            asset_id = parts[pub_idx + 1]
            rest = "/".join(parts[pub_idx + 2 :])
            slug = parts[1]
            return f"tenants/{slug}/gallery/delivery/{asset_id}/r1/{rest}"
        except (ValueError, IndexError):
            return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not settings.spaces_enabled:
        print("SPACES_ENABLED must be true", file=sys.stderr)
        return 1

    client = get_s3_client()
    paginator = client.get_paginator("list_objects_v2")
    copied = 0
    skipped = 0

    for page in paginator.paginate(Bucket=settings.spaces_bucket, Prefix="tenants/"):
        for obj in page.get("Contents") or []:
            key = obj["Key"]
            new_key = _remap_key(key)
            if not new_key or new_key == key:
                skipped += 1
                continue
            if args.dry_run:
                print(f"would copy: {key} -> {new_key}")
            else:
                try:
                    client.head_object(Bucket=settings.spaces_bucket, Key=new_key)
                    skipped += 1
                    continue
                except ClientError:
                    pass
                copy_object_to_key(client, key, new_key)
                print(f"copied: {key} -> {new_key}")
            copied += 1

    print(f"done. copied={copied} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

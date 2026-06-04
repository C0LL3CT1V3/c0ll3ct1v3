#!/usr/bin/env python3
"""Seed first artist tenant (workspace + basic profile).

  docker exec c0ll3ct1v3_backend_1 python scripts/seed_artist_tenant.py
"""

from __future__ import annotations

import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.artist import Artist, default_epk_config  # noqa: E402


def main() -> int:
    slug = (os.environ.get("DEFAULT_MEDIA_TENANT") or settings.default_media_tenant_slug).strip().lower()
    db = SessionLocal()
    try:
        if db.query(Artist).filter(Artist.tenant_slug == slug).first():
            print(f"artist already exists: {slug}")
            return 0

        cfg = default_epk_config()
        cfg.update(
            {
                "tagline": "Composer · Performer",
                "bio": "Independent artist on c0ll3ct1v3.",
                "booking_email": "booking@phillipjames.com",
            }
        )
        db.add(
            Artist(
                auth0_sub=f"seed:{slug}",
                tenant_slug=slug,
                display_name="Phillip James",
                epk_config=cfg,
            )
        )
        db.commit()
        print(f"seeded artist tenant: {slug}")
        print(f"workbench prefix: tenants/{slug}/workbench/")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

"""Additive migrations for creative media and workbench visions."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Legacy Phase 2–4 tables (not the simplified visions model).
_ABANDONED_TABLES = (
    "gallery_item_variants",
    "gallery_items",
    "workbench_assets",
    "timelines",
    "engagement_events",
)


def run_media_schema_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("media_assets"):
        return

    with engine.begin() as connection:
        for table in _ABANDONED_TABLES:
            if inspector.has_table(table):
                connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

        if not inspector.has_table("visions"):
            connection.execute(
                text(
                    """
                    CREATE TABLE visions (
                        id VARCHAR(36) PRIMARY KEY,
                        tenant_slug VARCHAR(64) NOT NULL,
                        title VARCHAR(512) NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_visions_tenant_slug ON visions (tenant_slug)"))

        media_cols = {column["name"] for column in inspector.get_columns("media_assets")}
        if "storage_region" not in media_cols:
            connection.execute(
                text("ALTER TABLE media_assets ADD COLUMN storage_region VARCHAR(32) DEFAULT 'workbench'")
            )
        if "gallery_rev" not in media_cols:
            connection.execute(text("ALTER TABLE media_assets ADD COLUMN gallery_rev INTEGER"))
        if "parent_asset_id" not in media_cols:
            connection.execute(text("ALTER TABLE media_assets ADD COLUMN parent_asset_id VARCHAR(36)"))
        if "gallery_stage" not in media_cols:
            connection.execute(text("ALTER TABLE media_assets ADD COLUMN gallery_stage VARCHAR(32)"))
        if "content_id" not in media_cols:
            connection.execute(text("ALTER TABLE media_assets ADD COLUMN content_id VARCHAR(36)"))
        if "vision_id" not in media_cols:
            connection.execute(text("ALTER TABLE media_assets ADD COLUMN vision_id VARCHAR(36)"))
            connection.execute(
                text(
                    "ALTER TABLE media_assets ADD CONSTRAINT fk_media_assets_vision_id "
                    "FOREIGN KEY (vision_id) REFERENCES visions(id) ON DELETE SET NULL"
                )
            )

        if "epk_role" in media_cols:
            connection.execute(text("ALTER TABLE media_assets DROP COLUMN IF EXISTS epk_role"))

        connection.execute(
            text("UPDATE media_assets SET storage_region = 'workbench' WHERE storage_region IS NULL")
        )
        connection.execute(
            text(
                "UPDATE media_assets SET status = 'ready' "
                "WHERE status = 'published' AND storage_region = 'workbench'"
            )
        )

        if inspector.has_table("media_jobs"):
            job_cols = {column["name"] for column in inspector.get_columns("media_jobs")}
            if "promote_meta" not in job_cols:
                connection.execute(text("ALTER TABLE media_jobs ADD COLUMN promote_meta JSON"))

        if not inspector.has_table("cloud_connections"):
            connection.execute(
                text(
                    """
                    CREATE TABLE cloud_connections (
                        id VARCHAR(36) PRIMARY KEY,
                        artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
                        provider VARCHAR(16) NOT NULL,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT,
                        expires_at TIMESTAMPTZ,
                        account_label VARCHAR(256),
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ,
                        UNIQUE (artist_id, provider)
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_cloud_connections_artist_id ON cloud_connections (artist_id)")
            )

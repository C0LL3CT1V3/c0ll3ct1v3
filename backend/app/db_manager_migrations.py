"""Additive migrations for manager threads and EPK iterations."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def run_manager_schema_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("artists"):
        return

    with engine.begin() as connection:
        artist_cols = {column["name"] for column in inspector.get_columns("artists")}
        if "epk_draft" not in artist_cols:
            connection.execute(text("ALTER TABLE artists ADD COLUMN epk_draft JSON"))
        if "allow_training_contribution" not in artist_cols:
            connection.execute(
                text(
                    "ALTER TABLE artists ADD COLUMN allow_training_contribution BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
        if "storage_namespace" not in artist_cols:
            connection.execute(text("ALTER TABLE artists ADD COLUMN storage_namespace VARCHAR(64)"))
            connection.execute(
                text("UPDATE artists SET storage_namespace = tenant_slug WHERE storage_namespace IS NULL")
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_artists_storage_namespace "
                    "ON artists (storage_namespace) WHERE storage_namespace IS NOT NULL"
                )
            )

        if not inspector.has_table("artist_slug_aliases"):
            connection.execute(
                text(
                    """
                    CREATE TABLE artist_slug_aliases (
                        id SERIAL PRIMARY KEY,
                        artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
                        slug VARCHAR(64) NOT NULL UNIQUE,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_artist_slug_aliases_artist_id "
                    "ON artist_slug_aliases (artist_id)"
                )
            )

        if not inspector.has_table("manager_threads"):
            connection.execute(
                text(
                    """
                    CREATE TABLE manager_threads (
                        id VARCHAR(36) PRIMARY KEY,
                        artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
                        mode VARCHAR(32) NOT NULL DEFAULT 'general',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_manager_threads_artist_id ON manager_threads (artist_id)")
            )

        if not inspector.has_table("manager_messages"):
            connection.execute(
                text(
                    """
                    CREATE TABLE manager_messages (
                        id VARCHAR(36) PRIMARY KEY,
                        thread_id VARCHAR(36) NOT NULL REFERENCES manager_threads(id) ON DELETE CASCADE,
                        role VARCHAR(16) NOT NULL,
                        content TEXT NOT NULL,
                        metadata_json JSON NOT NULL DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_manager_messages_thread_id ON manager_messages (thread_id)")
            )

        if not inspector.has_table("epk_iterations"):
            connection.execute(
                text(
                    """
                    CREATE TABLE epk_iterations (
                        id VARCHAR(36) PRIMARY KEY,
                        artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
                        thread_id VARCHAR(36) REFERENCES manager_threads(id) ON DELETE SET NULL,
                        step VARCHAR(16) NOT NULL,
                        user_prompt TEXT NOT NULL DEFAULT '',
                        context_snapshot JSON NOT NULL DEFAULT '{}',
                        model_reasoning TEXT,
                        reasoning_summary TEXT,
                        design_patch JSON NOT NULL DEFAULT '{}',
                        design_after JSON NOT NULL DEFAULT '{}',
                        screenshot_storage_key VARCHAR(1024),
                        annotations_raw JSON,
                        annotations_resolved JSON,
                        parent_iteration_id VARCHAR(36) REFERENCES epk_iterations(id) ON DELETE SET NULL,
                        artist_accepted BOOLEAN NOT NULL DEFAULT FALSE,
                        consent_for_training BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_epk_iterations_artist_id ON epk_iterations (artist_id, created_at)")
            )

        if inspector.has_table("manager_threads"):
            thread_cols = {column["name"] for column in inspector.get_columns("manager_threads")}
            if "vision_id" not in thread_cols:
                connection.execute(text("ALTER TABLE manager_threads ADD COLUMN vision_id VARCHAR(36)"))

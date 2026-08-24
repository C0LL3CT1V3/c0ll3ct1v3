"""Additive migrations for the attestation ledger."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def run_attestation_schema_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("artists"):
        return
    if inspector.has_table("attestation_claims"):
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE attestation_claims (
                    id VARCHAR(36) PRIMARY KEY,
                    artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
                    subject_asset_id VARCHAR(36) REFERENCES media_assets(id) ON DELETE SET NULL,
                    claim_type VARCHAR(64) NOT NULL,
                    value JSON NOT NULL,
                    source VARCHAR(64) NOT NULL DEFAULT 'manual',
                    source_ref JSON NOT NULL,
                    attested_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    attested_by_role VARCHAR(32),
                    attested_at TIMESTAMPTZ,
                    stale_after TIMESTAMPTZ,
                    prior_version_id VARCHAR(36) REFERENCES attestation_claims(id) ON DELETE SET NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'draft',
                    signature VARCHAR(256),
                    key_fingerprint VARCHAR(128),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_attestation_claims_artist_id "
                "ON attestation_claims (artist_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_attestation_claims_subject "
                "ON attestation_claims (subject_asset_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_attestation_claims_lookup "
                "ON attestation_claims (artist_id, subject_asset_id, claim_type, status)"
            )
        )

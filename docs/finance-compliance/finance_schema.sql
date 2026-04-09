-- Baseline schema for normalized Plaid + Square ingestion.

CREATE TABLE IF NOT EXISTS finance_connections (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('plaid', 'square')),
    source_account_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    consent_basis TEXT NOT NULL,
    consented_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finance_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('plaid', 'square')),
    source_transaction_id TEXT NOT NULL,
    source_account_id TEXT NOT NULL,
    merchant_name TEXT,
    amount_minor BIGINT NOT NULL,
    currency_code TEXT NOT NULL,
    posted_at TIMESTAMP NOT NULL,
    pending BOOLEAN NOT NULL DEFAULT FALSE,
    category TEXT,
    transaction_type TEXT,
    consent_basis TEXT NOT NULL,
    retention_class TEXT NOT NULL,
    synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source, source_transaction_id)
);

CREATE TABLE IF NOT EXISTS webhook_events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('plaid', 'square')),
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_redacted TEXT NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'received',
    UNIQUE (source, event_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    metadata_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_finance_transactions_user_date
    ON finance_transactions (user_id, posted_at);

CREATE INDEX IF NOT EXISTS idx_webhook_events_source_status
    ON webhook_events (source, status);


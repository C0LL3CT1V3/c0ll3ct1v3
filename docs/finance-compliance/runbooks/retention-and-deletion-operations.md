# Retention and Deletion Operations

Operational runbook for enforcing retention windows and user-driven deletion requests.

## Scheduled retention jobs

- Daily 01:00 UTC: delete `webhook_events` older than `DATA_RETENTION_RAW_WEBHOOK_DAYS`.
- Daily 01:15 UTC: delete application logs older than `DATA_RETENTION_APP_LOG_DAYS`.
- Weekly: verify audit log retention is >= `DATA_RETENTION_AUDIT_LOG_DAYS`.

## User disconnect workflow

1. Receive disconnect request.
2. Revoke upstream provider linkage.
3. Soft-disable local `finance_connections` record.
4. Queue purge job for all user/source data.
5. Mark completion and write `audit_events` record.

## Verification queries

- Count stale webhook events pending deletion.
- Count orphaned transactions without active connection.
- Confirm audit event exists for each completed purge.

## Controls

- Every retention/deletion run must write a signed job report.
- Failed jobs trigger on-call alerts.
- Manual deletes are prohibited outside approved break-glass process.


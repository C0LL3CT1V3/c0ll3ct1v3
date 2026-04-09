# Unified Governance Controls (Plaid + Square)

This document defines required privacy/security controls for finance ingestion services.

## 1) Data classification

- **Restricted:** access tokens, refresh tokens, webhook signatures, secret keys.
- **Confidential:** account identifiers, transaction metadata, merchant details.
- **Operational:** non-sensitive service metrics and health checks.

All restricted and confidential data must be encrypted at rest and protected in transit.

## 2) Data minimization rules

- Persist only fields required for finance workflows.
- Do not store PAN/CVV or online banking credentials.
- Strip non-required identity fields from provider payloads before persistence.

## 3) Logging redaction controls

- Redact secrets/tokens/account numbers before writing logs.
- Blocklist key names in structured logs: `token`, `secret`, `authorization`, `account_number`, `routing_number`.
- Truncate payload logging to approved, redacted subsets.

Implementation helper: `scripts/log_redaction.py`.

## 4) Retention policy

- **Raw webhook payloads:** 90 days max.
- **Application logs:** 30 days.
- **Security/audit logs:** 365 days minimum.
- **Normalized transactions:** retained per legal/accounting policy.

Use policy config values in environment variables to enforce retention windows.

## 5) Deletion policy

On user disconnect or account deletion:

1. Revoke upstream connection (`/item/remove` for Plaid, revoke token/disconnect for Square as applicable).
2. Queue internal purge by `user_id` and `source_account_id`.
3. Purge raw payloads, cached artifacts, and derived analytics rows.
4. Write immutable `audit_events` entry for completion.

## 6) Access control

- Require SSO + MFA for all production operators.
- Enforce RBAC for databases, secret manager, and observability tools.
- Run quarterly access recertification.
- Break-glass access requires incident ticket and post-use review.

## 7) Auditability

- Record all privileged reads to restricted data.
- Record configuration changes, token revocations, and data export actions.
- Keep audit logs append-only and tamper-evident.

## 8) Incident response requirements

- Maintain incident runbook with severity levels and response SLAs.
- Alert on anomalous token access, repeated auth failures, or webhook verification failures.
- Perform post-incident corrective action tracking.

## 9) Governance acceptance checklist

- [x] Redaction middleware enabled in all services
- [ ] Retention jobs scheduled and validated
- [ ] Disconnect/deletion workflow tested end-to-end
- [ ] Audit event coverage validated
- [ ] Access review evidence captured


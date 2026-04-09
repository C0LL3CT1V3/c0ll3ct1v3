# Plaid Security Questionnaire Answer Bank

Use this as a source-of-truth response set when completing Plaid Launch Center compliance and data security prompts.

## 1) Product and data use

- **Use case:** User-authorized cashflow analytics, transaction categorization, and finance reporting.
- **Plaid products requested:** `transactions`, `accounts`, and optional `liabilities` for credit card balances.
- **Data minimization statement:** We collect only fields needed for reporting and reconciliation (for example `item_id`, `account_id`, transaction date, posted amount, merchant name, category, account mask).
- **Data not collected/stored:** Raw credentials, full PAN, CVV, and non-required identity fields.

## 2) Consent and user notice

- **Consent approach:** In-app just-in-time consent before Plaid Link.
- **Privacy notice:** Privacy policy names Plaid as a data processor and describes data categories and use.
- **Recordkeeping:** Persist consent timestamp, policy version, and linked institution metadata.
- **Revocation:** Users can disconnect linked accounts from app settings.

## 3) Credential and token protection

- **Storage:** Plaid `access_token` is encrypted at rest with KMS-backed envelope encryption.
- **Access control:** Decrypt permissions are restricted by least privilege to ingestion services only.
- **Secret handling:** No provider tokens in client-side code, logs, crash dumps, or analytics events.
- **Rotation:** Platform secrets and service credentials are rotated on a defined schedule.

## 4) Infrastructure and transport security

- **In transit:** TLS 1.2+ for external and internal service communication.
- **At rest:** Encrypted database volumes and object storage.
- **Hardening:** CIS-style baseline hardening, patched OS images, and dependency scanning.
- **Network controls:** Production database and secret manager are private-network-only.

## 5) Access management and auditability

- **Identity model:** SSO + MFA for admins and production operators.
- **Authorization:** RBAC and break-glass access with approvals.
- **Auditing:** Immutable logs for token access, data exports, and privileged actions.
- **Reviews:** Periodic access recertification for all privileged roles.

## 6) Logging and observability

- **Structured logs:** Store request IDs and system metadata only.
- **Redaction:** Automatic masking of tokens, account numbers, and secrets.
- **Retention:** Separate retention policy by log class; security logs retained longer than app logs.
- **Monitoring:** Alerting for auth errors, webhook failures, and unusual access patterns.

## 7) Data retention and deletion

- **Retention classes:** Operational logs (30-90 days), normalized transactions (per accounting/legal need), security audit logs (policy-defined period).
- **User deletion flow:** On user disconnect or account deletion:
  1. Call Plaid `/item/remove`.
  2. Queue internal data purge for user-scoped datasets.
  3. Persist deletion event in audit ledger.
- **Backups:** Time-bounded backup retention with encrypted storage.

## 8) Incident response and business continuity

- **IR readiness:** Documented incident response runbook with on-call and escalation matrix.
- **Breach handling:** Legal/compliance notification workflow and timeline commitments.
- **BCP/DR:** Regular backup restore tests and recovery objective targets.
- **Postmortems:** Blameless post-incident process with remediation tracking.

## 9) Vendor and subprocessors

- **Subprocessor list:** Cloud provider, KMS/secrets manager, logging/APM provider.
- **Data residency:** Documented regions for data at rest.
- **Contracts:** DPA in place with providers handling customer financial data.
- **Assurance:** Annual vendor security review.

## 10) Evidence map to prepare before submission

- Privacy policy URL
- Terms of service URL
- Security contact email and incident contact
- Encryption architecture note (token handling/data flow)
- Access control policy excerpt
- Last access review evidence
- Vulnerability scan or patch management evidence
- Penetration test summary or security assessment memo
- Data retention/deletion policy excerpt

## Suggested plain-language answers (copy/edit)

- **Why do you need Plaid data?**  
  We use account and transaction data solely to provide user-authorized finance reporting, cashflow summaries, and bookkeeping insights.

- **How do you secure access tokens?**  
  Tokens are encrypted at rest with KMS-backed keys, never exposed client-side, and only decrypted by backend services with least-privilege IAM.

- **How do users revoke access?**  
  Users can disconnect accounts in-app at any time; we then remove the Plaid Item and purge associated internal data according to policy.

- **What data do you retain and for how long?**  
  We retain only data required for product operation, reconciliation, and legal/accounting obligations. Retention windows are policy-driven and deletion workflows are automated.


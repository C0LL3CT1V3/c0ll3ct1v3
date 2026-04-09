# Data Retention and Deletion Policy

Document Owner: Security and Compliance  
Version: 1.0  
Effective Date: 2026-03-05  
Review Cadence: At least annually and after legal/regulatory or architecture changes

## 1. Purpose

This policy defines requirements for retaining and deleting data to support legal, regulatory, operational, and security obligations while minimizing privacy risk.

## 2. Scope

This policy applies to:

- All data collected, processed, or stored by the finance MCP platform
- All production and non-production environments
- All employees, contractors, vendors, and systems handling covered data
- Data from external financial integrations, including Plaid and Square

## 3. Data Classification

- **Restricted:** tokens, secrets, encryption keys, sensitive authentication material
- **Confidential:** transaction records, account identifiers, webhook payloads, customer metadata
- **Internal:** operational metrics, non-sensitive logs, service metadata
- **Public:** approved external documentation and marketing content

Retention and deletion controls are applied according to this classification.

## 4. Retention Schedule

Unless a stricter legal or contractual requirement applies, the following defaults are enforced:

- **Raw webhook payloads:** retain up to 90 days
- **Application operational logs:** retain up to 30 days
- **Security and audit logs:** retain at least 365 days
- **Normalized transaction data:** retain according to accounting/legal requirements and documented business purpose
- **Backups:** retained per backup policy with encrypted storage and automatic expiry

Data must not be retained longer than necessary for its documented purpose.

## 5. Data Minimization Requirements

- Collect only fields required for product operation and compliance.
- Do not store prohibited sensitive values (for example, full PAN/CVV).
- Redact or tokenize sensitive fields before logging or analytics processing.
- Restrict non-production datasets to synthetic or de-identified data whenever feasible.

## 6. Deletion Requirements

### 6.1 User-initiated deletion/disconnect

When a user requests deletion or disconnects financial data sources:

1. Revoke/remove upstream integration access (for example Plaid Item removal).
2. Disable related internal connection records.
3. Execute purge workflow for user-scoped data across primary stores, caches, and derivatives.
4. Record completion in immutable audit logs.

### 6.2 System-triggered deletion

- Expired data is deleted automatically by scheduled retention jobs.
- Failed deletion jobs must alert operations and be retried.
- Manual deletion outside approved processes is prohibited unless formally authorized.

## 7. Legal Hold and Exceptions

- If legal hold is issued, applicable deletion jobs are suspended for scoped records.
- Legal hold scope, owner, and release date must be documented.
- On legal hold release, standard retention/deletion resumes promptly.

## 8. Security Controls for Retained Data

- Encryption in transit (TLS 1.2+) and at rest.
- RBAC and least-privilege access to retained datasets.
- MFA for privileged administrative access.
- Centralized monitoring and audit logging for access to sensitive data.

## 9. Verification and Monitoring

- Retention and deletion jobs are monitored with alerting.
- Periodic control checks verify policy enforcement and evidence completeness.
- Access and deletion events are auditable and retained per audit schedule.
- Metrics (deletion success rate, backlog, age of oldest expired record) are reviewed regularly.

## 10. Roles and Responsibilities

- **Security/Compliance:** Own policy, review cadence, and exception approvals.
- **Engineering:** Implement technical controls and automated retention/deletion jobs.
- **Operations:** Monitor job health and incident response for control failures.
- **Legal/Privacy:** Define legal hold requirements and regulatory constraints.

## 11. Enforcement

Non-compliance with this policy may result in remediation actions, access restrictions, incident response, and disciplinary action as appropriate.

## 12. Compliance Mapping (Questionnaire Support)

This policy provides documentation for:

- Defined and enforced data retention and deletion policy
- Periodic policy review
- Compliance with applicable privacy and data protection obligations


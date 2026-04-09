# Security policy

## Reporting vulnerabilities

Please report security issues privately to the repository maintainers. Do **not** open public issues for undisclosed vulnerabilities.

## Secrets and customer data

- Never commit `.env`, API keys, Plaid/Square tokens, or live database files.
- Never commit raw bank or card **CSV exports**, filled tax forms, or K-1 PDFs with partner **PII**.
- Use `samples/` for synthetic data only. Point real imports at a private directory via `FINANCE_DB_PATH`, `BANK_CSV`, etc.

## Production finance endpoints

When `APP_ENV=production` and `FINANCE_INTEGRATIONS_ENABLED=true`, the API validates Plaid/Square and MFA-related settings at startup. See [docs/finance-compliance/runbooks/](docs/finance-compliance/runbooks/).

## Audit events

Finance integration actions emit structured audit lines to stdout by default. Replace with a durable store (e.g. `audit_events` table) before multi-tenant production use.

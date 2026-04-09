# Decision Record: Square Authentication Strategy

## Context

The finance MCP integration needs Square data access for reporting and reconciliation. Square supports:

- Personal access tokens (full account scope; single-account internal integrations)
- OAuth tokens (scoped; required for multi-seller/public marketplace apps)

## Decision

**Chosen default:** Personal access token for initial production rollout.

This is selected because the current goal is to ingest data for your own Square business account (single-tenant/internal use). It minimizes setup complexity while remaining production-acceptable for custom single-account integrations.

## Guardrails

- Store personal token in secrets manager only (never in code or client apps).
- Restrict deployment/service access by least privilege.
- Use app-level webhook signature verification and idempotency handling.
- Keep token rotation and incident revocation runbooks documented.

## Trigger to migrate to OAuth

Migrate to OAuth if any of the following become true:

- You need to connect multiple seller accounts.
- You publish or distribute the app beyond your own account.
- You need strict per-seller scoped permission grants.

## OAuth migration notes

- Use `state` for CSRF protection.
- Use PKCE for public clients.
- Request minimum scopes only.
- Implement token refresh pipeline (refresh proactively every <= 7 days).
- Handle revoked/expired token errors with user re-auth flow.

## Scope baseline for this integration

- Read payments
- Read orders
- Read refunds
- Read payouts/disputes as needed for cashflow visibility

Avoid requesting write scopes unless there is a concrete feature that requires them.


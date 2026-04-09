# Square Production Setup Runbook

This runbook covers production credential setup, least-scope permissions, webhook verification, and token lifecycle handling.

## 1) Select auth mode

- **Single-account internal integration:** use `SQUARE_ACCESS_TOKEN`.
- **Multi-seller/public integration:** use OAuth (`SQUARE_APPLICATION_ID` + `SQUARE_APPLICATION_SECRET`).

Reference decision: `decisions/square-auth-decision.md`.

## 2) Configure production credentials

- [ ] Create/verify production Square application in Developer Console.
- [ ] Load production credentials into secrets manager.
- [ ] Set `SQUARE_ENV=production`.
- [ ] Set base URL to `https://connect.squareup.com/v2`.
- [ ] Keep sandbox credentials and endpoints isolated from production.

## 3) Permission and scope hardening

- [ ] Request only read scopes required by finance ingestion features.
- [ ] Remove unused scopes to reduce blast radius.
- [ ] Validate no write-capable scope exists unless a feature requires it.
- [ ] Document scope-to-feature mapping for security review.

## 4) OAuth lifecycle controls (if OAuth mode)

- [ ] Persist access + refresh tokens encrypted at rest.
- [ ] Refresh tokens proactively every <= 7 days.
- [ ] Detect and handle `ACCESS_TOKEN_EXPIRED` and `ACCESS_TOKEN_REVOKED`.
- [ ] Implement seller re-authorization flow with user-friendly messaging.

## 5) Webhook security

- [ ] Configure webhook subscription endpoint(s) in Developer Console.
- [x] Verify signatures for every inbound webhook.
- [x] Enforce idempotency via `event_id` deduplication.
- [ ] Store replay window and reject stale events.
- [ ] Alert on repeated verification failures.

Use helper script pattern in `scripts/square_webhook_verify.py`.

## 6) Error handling and resiliency

- [ ] Gracefully handle: `UNAUTHORIZED`, `INSUFFICIENT_SCOPES`, `ACCESS_TOKEN_EXPIRED`, `ACCESS_TOKEN_REVOKED`.
- [ ] Retry transient 5xx and rate-limit responses with backoff.
- [ ] Track sync lag and failed polling/webhook attempts.
- [ ] Expose token status in an internal operations dashboard.

## 7) Validation checklist

- [ ] Successful production call to `GET /v2/locations`.
- [ ] Payments/orders/refunds ingestion path validated.
- [ ] Webhook signature verification tested with valid + invalid signatures.
- [ ] Duplicate webhook replay test confirms idempotency.
- [ ] Preflight validation run:
  `python3 scripts/preflight_validate_config.py`


# MFA Implementation Quickstart

This quickstart demonstrates the implemented MFA-protected Plaid Link flow.

## 1) Install dependencies

```bash
./scripts/ensure_venv.sh
source .venv/bin/activate
uv pip list
```

## 2) Configure environment

Use `templates/.env.finance-mcp.example` as baseline. Required MFA flags:

- `MFA_ADMIN_ENFORCED=true`
- `MFA_CONSUMER_ENFORCED=true`
- `MFA_STEP_UP_FOR_PLAID_LINK=true`
- `MFA_METHODS_ALLOWED=totp,webauthn`
- `MFA_MAX_AGE_SECONDS=900`

For local testing, keep:

- `PLAID_LINK_MODE=stub`
- `MFA_DEMO_OTP=123456`

Auth provider options:

- **Production:** `AUTH_PROVIDER=auth0`
- **Local demo:** `AUTH_PROVIDER=demo`

## 3) Start API

```bash
./scripts/run_mcp.sh
```

If `8080` is already taken:

```bash
MCP_PORT=8011 ./scripts/run_mcp.sh
```

## 4) Test step-up flow (demo mode)

Create challenge:

```bash
curl -s -X POST "http://localhost:8080/auth/step-up/challenge" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user-123" \
  -d '{"reason":"plaid_link"}'
```

Verify challenge (`otp_code` must match `MFA_DEMO_OTP`):

```bash
curl -s -X POST "http://localhost:8080/auth/step-up/verify" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user-123" \
  -d '{"challenge_id":"<challenge-id>","otp_code":"123456"}'
```

Call protected Plaid link-token endpoint:

```bash
curl -s -X POST "http://localhost:8080/plaid/link-token/create" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user-123" \
  -H "X-Mfa-Verified-At: <unix-seconds-from-verify-response>" \
  -d '{"client_name":"Finance MCP","language":"en"}'
```

Without `X-Mfa-Verified-At`, endpoint returns `403 mfa_required`.

## 5) Test Auth0 MFA-gated flow (production pattern)

- Set `AUTH_PROVIDER=auth0` and configure:
  - `AUTH0_DOMAIN`
  - `AUTH0_AUDIENCE`
  - `AUTH0_ISSUER`
  - `AUTH0_ALGORITHMS=RS256`
- Obtain a bearer token where MFA was satisfied in Auth0 (MFA reflected in `amr` or `acr`, with `auth_time` claim).
- Call protected endpoint:

```bash
curl -s -X POST "http://localhost:8080/plaid/link-token/create" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <auth0-access-token>" \
  -d '{"client_name":"Finance MCP","language":"en"}'
```

If token lacks MFA evidence or is too old, endpoint returns `403 mfa_required` or `403 mfa_reauthentication_required`.

## 6) Production hardening follow-up

- Remove demo mode from production environments.
- Persist audit events to `audit_events` table instead of stdout.
- Switch `PLAID_LINK_MODE=api` and set production Plaid credentials.


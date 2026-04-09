# Plaid Production Launch Checklist

Use this checklist to complete Plaid production enablement and avoid common onboarding blockers.

## A. Launch Center prerequisites

- [ ] Request Production access in Plaid Launch Center.
- [ ] Complete application profile (name, logo, redirect URLs, support contacts).
- [ ] Complete company profile (legal name, address, business description).
- [ ] Complete data security questionnaire using the answer bank in `compliance/plaid-security-questionnaire-answer-bank.md`.
- [ ] Publish privacy policy and terms URLs used in submission.

## B. Product and scope setup

- [ ] Confirm only required products are requested in `/link/token/create` (start with `transactions`, `accounts`).
- [ ] Verify country codes and language settings match your target institutions.
- [ ] Confirm OAuth redirect behavior for mobile and desktop flows.
- [ ] Add duplicate-item prevention logic before token exchange.

## C. Production environment cutover

- [ ] Set Plaid host to production (`https://production.plaid.com`).
- [ ] Set production `PLAID_CLIENT_ID` and `PLAID_SECRET`.
- [ ] Remove all `/sandbox/*` endpoint usage.
- [ ] Remove sandbox test users and test assumptions from code paths.
- [ ] Store all provider credentials in a secrets manager.

## D. Required reliability controls

- [ ] Implement Plaid webhook endpoint with signature/IP policy controls.
- [x] Ensure webhook handlers are idempotent (event replay safe).
- [x] Handle `ITEM_LOGIN_REQUIRED`, `PENDING_DISCONNECT`, `PENDING_EXPIRATION`.
- [ ] Trigger update mode and user notification for recoverable Item states.
- [ ] Add retry/backoff for transient API failures.

## E. Logging and operations

- [ ] Log `request_id`, `item_id`, and `account_id` (where relevant).
- [ ] Never log `access_token`, full account numbers, or secrets.
- [ ] Monitor webhook delivery failures and reconciliation lag.
- [ ] Configure on-call alerts for sustained auth or sync failures.

## F. Go-live validation

- [ ] Link a real institution in production and validate full ingestion lifecycle.
- [ ] Confirm transaction sync pagination and continuation handling.
- [x] Verify user account disconnect calls Plaid `/item/remove`.
- [ ] Verify internal deletion workflow after disconnect.
- [ ] Run preflight config validation:  
  `python3 scripts/preflight_validate_config.py`

## Completion criteria

You are ready for production when all boxes above are complete and evidence links are captured in your compliance packet.


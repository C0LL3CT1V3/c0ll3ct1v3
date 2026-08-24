---
name: e2e-suite
description: Run the host-aware Playwright E2E suite against local Compose or production. Use when testing UI changes, smoke-checking the site, running Playwright, monitoring c0ll3ct1v3.xyz, or the user mentions e2e / test:e2e / localhost / 127.0.0.1 / tenant subdomains.
---

# E2E suite

## Which script

| Command | When |
|---|---|
| `npm run test:e2e:agent` | After local UI/API work. Chromium + JSON summary. Sets `E2E_ALLOW_WRITES=1`. |
| `npm run test:e2e` | Same tests without the summary printer. |
| `npm run test:e2e:prod` | Production monitor. `@functional` only, no writes. Failures here are real public bugs. |
| `npm run test:e2e:mobile` | Optional Pixel 7 project. |

## Before local runs

1. Compose up (`npm run dev:up`). If Buildx is broken: `docker compose -f docker-compose.dev.yml up --no-build -d`.
2. `curl -I http://localhost:3030` and `curl -s http://127.0.0.1:8080/health`.
3. Then `npm run test:e2e:agent`.

## Hosts

- Apex: `http://localhost:3030`, `http://127.0.0.1:3030`, `https://c0ll3ct1v3.xyz`
- Tenant: `http://{slug}.localhost:3030`, `https://{slug}.c0ll3ct1v3.xyz` (hyphens allowed)

Override with `E2E_BASE_URL`, `E2E_TENANT_URL`, `E2E_API_URL`, `E2E_TENANT_SLUG`.

Portal UI (`@auth`): copy `e2e/.env.example` to `e2e/.env` and set `E2E_AUTH_EMAIL` / `E2E_AUTH_PASSWORD` for a dedicated Auth0 user (password connection, MFA off). Tests skip without it. Never invent credentials. Do not use `@auth` against production unless `E2E_AUTH_ALLOW_PROD=1`.

Writes (`@write`, agent-key attestation drafts) run only on loopback/`*.localhost` with `E2E_ALLOW_WRITES=1`. Never against production.

## Read the result

Stdout ends with `E2E summary: N passed, N failed, N skipped, N flaky`. Details: `test-results/e2e-results.json`. Report commands run, that summary, and skipped tags.

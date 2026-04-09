# Plaid + Square Finance MCP Pack

This folder contains production-readiness deliverables for adding Plaid and Square data into a finance MCP integration.

## What is included

- `compliance/` - Plaid questionnaire answer bank and privacy templates.
- `runbooks/` - step-by-step launch/setup checklists for Plaid and Square.
- `decisions/` - architecture and auth path decisions.
- `security/` - governance controls, retention, access, and MFA standards.
- `templates/` - environment variable template for production deployments.
- `scripts/` - validation and utility scripts for secure setup.
- `sql/` - baseline schema for normalized finance records.
- `app/` - FastAPI service with MFA step-up and Plaid link-token guard.

## Recommended execution order

1. Start with `compliance/plaid-security-questionnaire-answer-bank.md`.
2. Complete `runbooks/plaid-production-launch-checklist.md`.
3. Apply `decisions/square-auth-decision.md`.
4. Complete `runbooks/square-production-setup.md`.
5. Enforce controls in `security/unified-governance-controls.md`.
6. Implement MFA controls in `runbooks/mfa-compliance-implementation.md`.
7. Use `templates/.env.finance-mcp.example` and run `scripts/preflight_validate_config.py`.

## API implementation

This package now includes a runnable reference API:

- `POST /auth/step-up/challenge`
- `POST /auth/step-up/verify`
- `POST /plaid/link-token/create` (MFA-gated)

See `runbooks/mfa-implementation-quickstart.md` for local run and test commands.

## Python environment policy

Use the local `.venv` for all Python commands, with a uv-native workflow. This project includes:

- `.cursor/rules/venv-required.mdc` (always-on agent rule)
- `scripts/ensure_venv.sh` (installs `uv` if needed, creates/updates `.venv`)
- `scripts/run_mcp.sh` (runs MCP API from `.venv` via `uv run`)

Recommended local startup:

```bash
./scripts/run_mcp.sh
```

If port `8080` is in use:

```bash
MCP_PORT=8011 ./scripts/run_mcp.sh
```

Auth is provider-driven:

- `AUTH_PROVIDER=auth0` for production JWT verification and MFA claim enforcement
- `AUTH_PROVIDER=demo` for local step-up testing flows


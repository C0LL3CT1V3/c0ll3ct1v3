# MFA Compliance Implementation Runbook

Use this runbook to operationalize compliant MFA controls for workforce and consumer access.

## 1) Define identity architecture

- [ ] Select centralized IdP for workforce authentication.
- [ ] Configure Auth0 as primary auth provider for app/API (`AUTH_PROVIDER=auth0`).
- [ ] Define MFA factor policy (`totp`, `webauthn`, optional `push`).
- [ ] Disable password-only sign-in for privileged accounts.

## 2) Enforce workforce/admin MFA

- [ ] Require MFA for production cloud, databases, CI/CD, secrets manager, and observability tools.
- [ ] Block local/shared admin accounts where feasible.
- [ ] Require re-authentication + MFA for privileged actions.
- [ ] Validate emergency break-glass process includes approval and audit logs.

## 3) Enforce consumer MFA for finance flows

- [ ] Require user authentication before Plaid Link is shown.
- [ ] Implement step-up MFA before linking accounts and sensitive exports.
- [ ] Log consent and auth context for account-link events.
- [ ] Add risk checks for new device and unusual location behavior.

## 4) Configure policy variables

- [ ] Set `MFA_ADMIN_ENFORCED=true`
- [ ] Set `MFA_CONSUMER_ENFORCED=true`
- [ ] Set `MFA_METHODS_ALLOWED=totp,webauthn`
- [ ] Set `MFA_STEP_UP_FOR_PLAID_LINK=true`
- [ ] Set `MFA_BREAK_GLASS_APPROVAL_REQUIRED=true`

## 5) Validate technical enforcement

- [ ] Run `python3 scripts/preflight_validate_config.py`
- [ ] Verify non-MFA admin login is blocked.
- [ ] Verify Plaid Link cannot be launched without authenticated session.
- [ ] Verify step-up MFA is triggered for financial-linking actions.

## 6) Capture audit evidence

- [ ] MFA policy document (`security/mfa-standard.md`)
- [ ] IdP screenshots/settings export proving MFA enforcement
- [ ] Admin login attempts (success/failure) with MFA evidence
- [ ] Consumer step-up MFA logs for financial actions
- [ ] Break-glass logs and approvals

## 7) Ongoing review

- [ ] Quarterly review of MFA coverage and bypass events
- [ ] Annual factor policy review (deprecate weak factors where possible)
- [ ] Incident-triggered review after auth-related events


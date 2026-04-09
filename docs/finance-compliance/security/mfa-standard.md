# Multi-Factor Authentication (MFA) Standard

Document Owner: Security  
Version: 1.0  
Effective Date: 2026-03-05  
Review Cadence: At least annually and after material auth/identity changes

## 1. Purpose

This standard defines mandatory MFA controls to protect workforce and consumer access to systems handling sensitive financial data.

## 2. Scope

This standard applies to:

- Administrative and privileged access to critical systems
- Workforce access to production systems and sensitive data stores
- Consumer authentication flows for applications that surface Plaid Link
- Break-glass and emergency access processes

## 3. Mandatory Requirements

### 3.1 Workforce and admin MFA

- MFA is required for all privileged/administrative access.
- MFA is required for access to systems storing or processing consumer financial data.
- Access without MFA is prohibited unless approved under emergency break-glass procedure.

### 3.2 Consumer MFA controls

- Users must be authenticated before Plaid Link is surfaced.
- Step-up MFA is required before high-risk actions, including:
  - linking new financial institutions
  - changing payout or account settings
  - exporting sensitive financial data

### 3.3 Approved factors

Allowed factors include:

- TOTP authenticator applications
- WebAuthn / hardware-backed passkeys
- Push-based authenticator approvals

SMS-based MFA may be used only as fallback where stronger factors are unavailable.

### 3.4 Recovery and reset protections

- MFA reset requires identity verification and auditable approval.
- Recovery flows must include cooldown or risk checks to prevent account takeover.
- Helpdesk-based bypass must be time-limited and logged.

### 3.5 Session and device controls

- Enforce short session lifetime for admin consoles.
- Re-authentication and MFA re-prompt required for sensitive admin actions.
- New/untrusted device logins require additional verification.

## 4. Monitoring and Evidence

- Log all authentication attempts, factor enrollments, factor resets, and bypass events.
- Alert on repeated failed MFA attempts, unusual geo/device patterns, and bypass usage.
- Retain MFA audit logs per data retention policy.

## 5. Exceptions

- Exceptions require Security approval, documented compensating controls, and expiration date.
- Permanent exemptions are prohibited for privileged accounts.

## 6. Compliance Mapping

This standard supports controls for:

- MFA for access to critical systems handling consumer financial data
- MFA before or around consumer access to financial-linking features
- Auditable enforcement and periodic review


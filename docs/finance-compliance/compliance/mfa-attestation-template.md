# MFA Attestation Template (Plaid Compliance)

Use this response when asked to describe MFA practices. Replace placeholders with your specifics.

## Attestation text

We enforce multi-factor authentication (MFA) for privileged and critical-system access that stores or processes consumer financial data. Administrative access to production infrastructure, databases, secrets systems, and observability tooling requires MFA and is centrally managed through our identity provider.

For consumer workflows, users must be authenticated before financial linking features are shown, and step-up MFA is required for high-risk actions such as linking new institutions or exporting sensitive financial data.

Our approved MFA methods are TOTP and WebAuthn/passkeys (with stronger methods preferred). MFA resets and emergency bypass are controlled by documented procedures, require approval, and are fully logged.

MFA events (enrollment, challenge success/failure, resets, bypasses) are monitored and audited, and controls are reviewed periodically.

## Supporting evidence checklist

- [ ] `security/mfa-standard.md`
- [ ] IdP policy screenshot/export with MFA required for admins
- [ ] Consumer auth flow screenshot showing MFA gate before Plaid Link
- [ ] Sample MFA audit logs and alerting evidence


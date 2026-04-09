# Information Security Policy

Document Owner: Security  
Version: 1.0  
Effective Date: 2026-03-05  
Review Cadence: At least annually and after material business, regulatory, or architecture changes

## 1. Purpose

This policy establishes the information security requirements for protecting company systems and data, including consumer financial data, from unauthorized access, disclosure, alteration, and destruction.

## 2. Scope

This policy applies to:

- All employees, contractors, and third parties with access to company systems
- All information assets, including applications, infrastructure, endpoints, and data stores
- All environments (production, staging, development) and integrated services

## 3. Security Objectives

- Preserve confidentiality, integrity, and availability of information assets
- Enforce least privilege and strong authentication controls
- Maintain secure development and operational practices
- Detect, respond to, and recover from security incidents
- Comply with applicable legal, regulatory, and contractual obligations

## 4. Governance and Risk Management

- Security ownership is assigned to designated security leadership.
- Security risks are identified, assessed, and tracked through a risk management process.
- Policies, standards, and procedures are documented and operationalized.
- Security controls are reviewed periodically and improved based on risk, incidents, and audits.

## 5. Identity and Access Management

- Access is granted based on business need and role-based access control (RBAC).
- Privileged access is restricted, approved, logged, and periodically reviewed.
- MFA is required for administrative and critical-system access.
- Joiner/mover/leaver processes ensure timely provisioning and de-provisioning.
- Non-human access uses managed credentials (for example OAuth tokens, TLS certificates, and service identities).

## 6. Data Protection

- Data is classified according to sensitivity and protected accordingly.
- Sensitive data is encrypted in transit (TLS 1.2+) and at rest.
- Secrets and keys are stored in approved secrets/key management systems.
- Logging and telemetry must redact sensitive values.
- Data retention and deletion are governed by policy and legal requirements.

## 7. Infrastructure and Network Security

- Production systems are hardened and segmented.
- Security controls include firewalls/security groups, endpoint protection, and vulnerability management.
- Administrative interfaces are restricted and monitored.
- Changes to critical infrastructure follow change control procedures.

## 8. Secure Development and Vulnerability Management

- Security is integrated into the software development lifecycle.
- Code changes are peer-reviewed and tracked.
- Dependency and vulnerability scanning are performed regularly.
- Critical/high-risk vulnerabilities are remediated within defined SLAs.
- Security testing is performed for material changes.

## 9. Logging, Monitoring, and Detection

- Security-relevant events are centrally logged and protected from tampering.
- Monitoring and alerting are in place for suspicious activity and control failures.
- Audit trails are retained according to retention policy and compliance requirements.

## 10. Incident Response

- A documented incident response process defines triage, containment, eradication, recovery, and post-incident review.
- Security incidents are escalated according to severity and impact.
- Notifications are performed as required by law, contract, and policy.

## 11. Business Continuity and Disaster Recovery

- Critical systems have backup and recovery procedures.
- Recovery objectives are defined for key services.
- Backup restore and recovery procedures are periodically tested.

## 12. Vendor and Third-Party Security

- Third-party providers handling sensitive data are subject to security due diligence.
- Appropriate contractual protections (for example DPAs) are maintained.
- Third-party access is limited, monitored, and periodically reviewed.

## 13. Training and Awareness

- Personnel complete security awareness training at onboarding and periodically thereafter.
- Role-specific security training is provided where needed.
- Employees are expected to report suspected security events promptly.

## 14. Compliance and Enforcement

- Compliance with this policy is mandatory.
- Exceptions require documented approval, compensating controls, and expiration dates.
- Violations may result in disciplinary action, access removal, and incident management.

## 15. Related Policies

- Access Control Policy
- Data Retention and Deletion Policy
- Incident Response Plan
- Vulnerability Management Standard
- Secrets Management Standard


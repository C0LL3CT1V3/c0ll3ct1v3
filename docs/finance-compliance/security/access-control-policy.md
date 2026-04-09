# Access Control Policy

Document Owner: Security  
Version: 1.0  
Effective Date: 2026-03-05  
Review Cadence: At least annually and after material system changes

## 1. Purpose

This policy defines controls for granting, managing, monitoring, and revoking access to company systems, production assets, and sensitive data, including consumer financial data.

## 2. Scope

This policy applies to:

- All employees, contractors, and service accounts
- All production and non-production systems
- All infrastructure, applications, databases, and third-party SaaS platforms
- All systems that store, process, or transmit sensitive or regulated data

## 3. Policy Statements

### 3.1 Defined and documented access control policy

The organization maintains a defined and documented access control policy and supporting procedures. Access decisions are based on business need, least privilege, and role requirements. This policy is communicated to relevant personnel and operationalized through technical and administrative controls.

### 3.2 Role-based access control (RBAC)

Access is granted using RBAC groups/roles rather than direct user-by-user permissions where feasible.

- Roles are mapped to job functions.
- Access rights are limited to the minimum required to perform duties.
- Elevated privileges require explicit approval and are time-bounded when possible.

### 3.3 Periodic access reviews and audits

The organization performs recurring access reviews and audits.

- Production and privileged access are reviewed at least quarterly.
- Managers/system owners validate role appropriateness and necessity.
- Review evidence is retained for audit/compliance.
- Exceptions are tracked and remediated with defined timelines.

### 3.4 Automated de-provisioning / access modification

The organization uses automated identity lifecycle workflows to remove or modify access for terminated or transferred personnel.

- Terminations trigger immediate account disablement and session/token revocation.
- Role changes trigger automatic entitlement updates based on new role mapping.
- Shared credentials are prohibited; emergency credentials are rotated after use.

### 3.5 Zero trust architecture principles

Access control follows zero trust principles:

- Verify explicitly (identity, device, context) for every access request.
- Enforce least privilege and just-in-time elevation where possible.
- Assume breach and continuously monitor signals (auth anomalies, unusual access).
- Segment production systems to reduce lateral movement.

### 3.6 Centralized identity and access management

The organization uses centralized IAM for workforce and system access governance.

- Central identity provider for authentication and federation.
- Single Sign-On (SSO) for supported internal systems.
- Multi-factor authentication for privileged and critical-system access.
- Centralized logging for authentication and authorization events.

### 3.7 Non-human authentication (OAuth tokens / TLS certificates)

Machine-to-machine access uses strong non-human authentication methods.

- OAuth 2.0 access tokens are used for API integrations where supported.
- Mutual TLS and/or TLS client certificates are used for service authentication where required.
- Service credentials are stored in a managed secrets system and rotated on schedule.
- Non-human identities are scoped to minimum required permissions.

## 4. Enforcement

- Access requests require documented approval from system/data owner.
- Policy violations may result in access suspension, incident handling, and disciplinary action.
- Security may block or revoke access that presents unacceptable risk.

## 5. Evidence and Records

The following artifacts are maintained as compliance evidence:

- Access request/approval records
- Role definition matrix
- Quarterly access review reports
- HR-triggered de-provisioning logs
- Authentication and authorization audit logs
- Service account/token inventory and rotation records

## 6. Related Standards and Procedures

- Information Security Policy
- Identity Lifecycle Procedure
- Privileged Access Standard
- Secrets Management Standard
- Logging and Monitoring Standard
- Incident Response Plan

## 7. Compliance Mapping (Questionnaire Support)

This document supports attestation for:

- A defined and documented access control policy is in place
- Role-based access control (RBAC)
- Periodic access reviews and audits are performed
- Automated de-provisioning/modification of access for terminated or transferred employees
- Implementation of a zero trust access architecture
- Centralized identity and access management solutions
- Use of OAuth tokens or TLS certificates for non-human authentication


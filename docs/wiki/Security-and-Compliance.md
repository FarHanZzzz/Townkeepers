# Security and Compliance

This page summarizes security controls and compliance-oriented practices for Amader TOWNHALL. It is engineering guidance, not legal advice.

## Security Principles

- **Least privilege:** users get only actions/scopes required by role and active assignment.
- **Server-side enforcement:** UI hiding is never sufficient; every action/file/export is checked server-side.
- **Defense in depth:** validation at boundary + domain + database constraints.
- **Auditability:** material actions produce audit records.
- **Safe failure:** provider outages degrade to manual/safe paths; no silent data corruption.

## Authentication and Sessions

- Production sign-in intended via IUB Google/OIDC with allowed-domain enforcement.
- Demo login is for development only and must be disabled in production.
- Sessions use secure cookie settings in production (`Secure`, `HttpOnly`, `SameSite` as appropriate).
- Inactive users/assignments lose effective access.

## Authorization

Authorization checks include:

- profile active state
- access category ceiling
- grants/permissions
- club/term/effective-date scope
- object-state rules (e.g., which memo stage can be decided)

Out-of-scope objects return not-found to avoid leaking existence; forbidden visible actions return permission denied.

## Data Protection

| Data type | Handling |
|---|---|
| Credentials/tokens | Environment/secret manager only; never in git, logs, screenshots. |
| PII (names, emails, IDs) | Minimum necessary; synthetic data in tests/demos. |
| Uploaded files | Private storage, type/size validation, digest, authorized download. |
| Financial records | Decimal amounts, explicit currency, immutable evidence, linked adjustments. |
| Audit logs | Append-only; protected from mutation. |

## File Upload Security

- Validate file type by content/magic bytes, not only extension.
- Enforce `MAX_UPLOAD_BYTES`.
- Store outside public web root.
- Generate random/storage keys; do not trust user filenames.
- Serve via permission-checking view/proxy endpoint.
- Scan files if antivirus/malware scanning is available in deployment.

## Audit and Traceability

- Record actor, action, object, timestamp, and relevant before/after or reason.
- Keep command receipts for idempotency/replay traceability.
- For approvals/signatures, bind to immutable version/content hash.
- For corrections, create linked adjustment/correction records with reason.

## Dependency and Supply Chain

- Pin dependencies in lockfile.
- Review dependency updates for security/advisory impact.
- Avoid adding dependencies without clear value and maintenance justification.
- Use CI checks and static analysis (Ruff, Django checks, tests).

## Logging and Privacy

- Do not log secrets, raw tokens, session cookies, or sensitive file contents.
- Redact personal/sensitive fields in logs where possible.
- Include correlation/request IDs for debugging.
- Restrict log access to authorized operators.

## Compliance-Oriented Checklist

Before go-live, confirm with institutional owners:

- [ ] Approved identity provider/domain policy (IUB Google/OIDC).
- [ ] Data retention and deletion policy for user/content/audit records.
- [ ] Backup retention and restore test schedule.
- [ ] Approved email sender/domain and notification policy.
- [ ] File storage location, encryption, and access policy.
- [ ] AI/OCR provider data processing terms and consent/approval.
- [ ] Accessibility target (WCAG 2.2 AA) verification.
- [ ] Incident response contacts and escalation path.
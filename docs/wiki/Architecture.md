# Architecture

This page describes the high-level architecture of Amader TOWNHALL and the conventions that keep behavior safe, auditable, and testable.

## Architectural Principles

1. **PRD owns behavior, technical requirements own verification.** Requirement IDs (FR/UC/AC/BR/NFR) should remain traceable.
2. **Server state is authoritative.** UI, AI, and OCR never silently override authoritative records.
3. **Commands own writes.** Views parse/authorize at boundary; domain commands enforce rules and mutate state.
4. **Auditability by default.** Material actions record audit entries; immutable records are never edited in place.
5. **Safe under retries/races.** Idempotency keys, locks, constraints, and stale-revision checks prevent duplicate/conflicting writes.
6. **Provider isolation.** External providers (email, AI/OCR, publishing) go through adapters/jobs; business transactions do not depend on live provider calls.

## High-Level Components

```text
Browser (Django templates + JS)
        │
        ▼
Django web app (apps/*)
  - views/forms (boundary)
  - selectors (scoped reads)
  - commands (write rules)
  - models/migrations (authoritative data)
        │
        ├── PostgreSQL (authoritative records, constraints, locks)
        ├── Durable jobs/outbox (platform_core.jobs) ── worker ── email/providers
        └── FastAPI assistance (advisory only: scheduling/OCR contracts)
```

## Module Map

| Module | Responsibility |
|---|---|
| `apps/platform_core` | Command protocol, access control, audit, jobs, notifications, files, policy, exceptions, middleware. |
| `apps/accounts` | Profiles, grants, auth/demo sign-in, profile change requests, dashboard composition. |
| `apps/clubs` | Clubs, terms, assignments, archive corrections. |
| `apps/events` | Events, venue catalogue, bookings, calendar, availability, blocks/restrictions. |
| `apps/memos` | Templates, memo versions, signatures, decisions, export/preview. |
| `apps/finance` | Budgets, allocations/releases, expenses, evidence, adjustments, reconciliation. |
| `apps/publishing` | Internal/external publication records and attempts. |
| `apps/analytics` | Reporting/term/event analytics (incremental). |
| `assistance/` | FastAPI contracts/providers/client; advisory responses with fallback. |

## Command Protocol

All meaningful writes should go through `platform_core.protocol.execute(...)`.

**Properties:**
- Atomic transaction per command.
- Command receipt keyed by `(actor, action, operation_key)`.
- Same key + same payload => replayed result.
- Same key + different payload => conflict.
- Domain error rolls back so retry is possible.

This protects against double-submit, retries, and client/network uncertainty.

## Access Control

Access decisions combine:

- profile active state
- access category ceiling
- explicit grant (except implicit System Admin ceiling)
- scoped assignment (club/term/effective dates) where applicable

**Rules:**
- Check at boundary and recheck inside command transaction.
- Out-of-scope record: `NotFoundError` (conceal existence).
- Forbidden on visible record: `PermissionDeniedError`.
- Server-side checks apply to UI, direct requests, exports, files, previews.

## Data Integrity & Concurrency

- **PostgreSQL constraints** for invariants (uniqueness, checks, exclusion constraints).
- **Row locks** in documented order (e.g., memo/version/task; venue lock for booking confirmation).
- **`select_for_update(of=("self",))`** when joining nullable relations.
- **Stale revision checks** for mutable drafts.
- **Immutable history** for signed/approved/financial evidence records; corrections are linked records.

## Key Domain State Machines

| Domain | Typical states |
|---|---|
| Memo | Draft → Pending Advisor Confirmation → Pending Additional Signatures → Pending DoSA Approval → Approved/Rejected; Withdrawn/Revision/Amendment flows. |
| Event | Draft → Awaiting Approvals → Approved → Completed/Cancelled. |
| Booking | Pending → Confirmed/Returned/Declined/Cancelled; reschedule as linked replacement. |
| Expense/Fund release | Draft/Submitted/Verified/Returned/Rejected and Scheduled/Released/Cancelled with linked adjustments. |
| Publication | Unpublished → Publishing → Published/Failed/Uncertain → Withdrawn (per destination). |

## Observability & Audit

- `AuditEntry` for material actions (append-only).
- `Job`/delivery tracking for side effects.
- Structured domain errors mapped to HTTP/API responses.
- Request/command IDs and correlation in logs where available.

## Architecture Decisions to Preserve

- Do not send provider calls inside business transactions.
- Do not turn AI/OCR output into authoritative state automatically.
- Do not update signed/verified historical records in place.
- Do not bypass command protocol for material writes.
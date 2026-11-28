# Amader TOWNHALL Wiki

Welcome to the **Amader TOWNHALL** (Townkeepers) project wiki. This wiki is the living documentation hub for the platform: product context, architecture, setup, operations, and contribution guidance.

> **Project status:** Active development prototype. Core memo, event, booking, finance, publishing, and reporting slices are implemented incrementally; some institutional integrations and release gates remain pending. See [Implementation Context](../IMPLEMENTATION_CONTEXT.md) and [Assessment Evidence](../../ASSESSMENT.md).

## What is Amader TOWNHALL?

Amader TOWNHALL is a club administration platform for Independent University, Bangladesh (IUB). It gives clubs, Faculty Advisors, DoSA, and designated signers one auditable record for the full event lifecycle:

1. **Event draft** — EB creates and refines event details.
2. **Memo workflow** — EB drafts, Advisor confirms/rejects, optional signers endorse, DoSA Head approves/rejects.
3. **Venue booking** — booking requests, route-based decisions, conflict checks, confirmation.
4. **Publishing** — internal notices and external publishing flow (where configured).
5. **Finance & evidence** — budget requests, expenses, receipts, adjustments, reconciliation.
6. **Analytics & handover** — term/activity reporting, archive, and leadership handover.

## Key Capabilities

| Area | Capability | Notes |
|---|---|---|
| Identity & Access | Google/OIDC-ready sign-in, demo personas, role/category grants, scoped actions | Live IUB Google/domain config is pending institutional values. |
| Clubs & Terms | Club registry, terms, EB/advisor assignments, organogram, archive corrections | Single-holder designation rules enforced. |
| Memos | Template versioning, draft/send/review, e-signature, revision/amendment, A4 export | Immutable signed versions; stale/replay-safe commands. |
| Events & Venues | Event drafts, booking routes, availability, calendar heatmap, venue restrictions/blocks | Venue catalogue currently synthetic (D-23). |
| Finance | Budget requests, allocations/releases, expenses, OCR evidence (advisory), adjustments | Money is `Decimal`; currencies never mixed without conversion record. |
| Publishing | Internal notices, external publish attempts, delivery tracking | External publish fails safely when destination not configured. |
| Audit & Reliability | Audit log, durable jobs/outbox, command receipts/idempotency, stale revision protection | Provider calls happen after business transaction commit. |

## Roles / Personas

| Persona | Typical responsibilities |
|---|---|
| System Admin | Bootstrap/provision accounts, manage grants, operational admin (no memo signing). |
| DoSA Head | Final memo decision, venue/policy/admin oversight, central event authority. |
| Faculty Advisor | Confirm/reject memos, request additional signers, club-level review. |
| Designated Signer | Endorse/return signature tasks assigned to their identity. |
| Club EB Member | Create/edit events, draft/send memos, manage club records within assigned term/club. |

## Tech Stack

- **Backend:** Python 3.13, Django 6.x (server-rendered templates)
- **Assistance service:** FastAPI + Pydantic (private, advisory only)
- **Database:** PostgreSQL 17 (`btree_gist`, exclusion constraints, transaction locks)
- **Testing:** pytest, pytest-django, Playwright browser tests, contract tests
- **Quality:** Ruff, Sphinx doc build, requirement-marker checks
- **Frontend:** Accessible Django templates, plain CSS/JS, server-first UI

## Quick Links

- [[Getting Started]] — local setup, seed demo, run/test commands
- [[Architecture]] — modules, command protocol, data/state model
- [[Configuration]] — environment variables, policy/synthetic values
- [[Deployment and Operations]] — release gates, monitoring, backups, worker
- [[Security and Compliance]] — access control, audit, privacy, file handling
- [[Contributing]] — development workflow, PR expectations, tests
- [[FAQ and Troubleshooting]] — common issues and answers

## Repository Documentation

- [README](../../README.md)
- [AGENTS.md](../../AGENTS.md) — engineering standards
- [GRAND_PRD.md](../../GRAND_PRD.md) — product requirements (FR/UC/AC/BR/NFR)
- [TECHNICAL_REQUIREMENTS.md](../../TECHNICAL_REQUIREMENTS.md) — architecture/verification
- [Implementation Context](../IMPLEMENTATION_CONTEXT.md) — handover, decisions, traceability
- [Assessment Evidence](../../ASSESSMENT.md) — test/quality evidence
- [UI Heuristics](../UI-HEURISTICS.md)

## Wiki Maintenance

- Keep this wiki aligned with `AGENTS.md`, PRD, and technical requirements.
- When behavior changes, update the relevant wiki page in the same PR as code.
- Mark synthetic/institution-pending values clearly; do not present them as official.
- Prefer linking to source docs for canonical requirement IDs and evidence.
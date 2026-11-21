# Sprint 1 plan: Increments 1 and 2

**Goal.** A provisioned EB member signs in, creates an event and budget, and sends an event-permission memo. The Faculty Advisor e-signs, a Department Head can be added, and the DoSA Head rejects or approves. Every step is versioned, audited and notified.

**Definition of done.** For each item: the PRD acceptance scenario passes; the item's Success and Failure outcomes have tests carrying `@pytest.mark.req`; the AGENTS.md gate is green on PostgreSQL; ASSESSMENT.md and docs/IMPLEMENTATION_CONTEXT.md are updated.

| # | Story (PRD ID) | Acceptance | Owner | Status |
|---|---|---|---|---|
| 1 | Bootstrap the first System Admin and provision the DoSA Head (FR-IAM-03, UC-02) | AC-15 | _team_ | Done |
| 2 | Sign in with IUB Google; deny ineligible accounts (FR-IAM-01, UC-01) | AC-15 | _team_ | Done (live Google client pending) |
| 3 | Grants and dated club or term assignments (FR-IAM-02, FR-IAM-04) | AC-15, AC-17 | _team_ | Done |
| 4 | Profile corrections with routing (FR-IAM-05, UC-03) | AC-17 | _team_ | Done |
| 5 | Role dashboards (FR-IAM-06, UC-04) | AC-15 | _team_ | Done |
| 6 | Workflow settings versions (FR-IAM-08, UC-05) | | _team_ | Partial (venue rules arrive in Increment 3) |
| 7 | Club register, terms, appointments, organogram, archive (FR-CLB-01 to 05, 07) | AC-09 (partial) | _team_ | Done |
| 8 | Draft event and budget versions with Advisor endorsement (FR-EVT-01/02, FR-FIN-04) | AC-03 (partial) | _team_ | Done |
| 9 | Versioned memo templates (FR-MEM-01, UC-18) | AC-13 | _team_ | Done |
| 10 | Draft, send, sign, decide, revise, withdraw, amend, export memos (FR-MEM-02 to 13) | AC-01, AC-16 | _team_ | Done |
| 11 | Platform: audit, command receipts, durable jobs, private files, health (FR-COM-02 to 06, 08) | AC-18 (partial) | _team_ | Done |
| 12 | Assistance service contracts and fallbacks (TR sections 1, 2, 6) | | _team_ | Done (skeleton) |

**Risks carried forward.** IUB domain and Google client (PRD C.2); synthetic policy values; CI not yet run on GitHub.

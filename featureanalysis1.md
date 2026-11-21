# Townkeepers Product and Technical Feature Analysis

**Analysis revision:** 1
**Date:** 22 November 2026
**Scope:** Current implementation, requirements, test evidence, interface, integrations and release readiness

## 1. Executive assessment

Townkeepers is already technically stronger than a generic Django CRUD project. It has a substantial domain model, immutable review history, role and club scoping, command idempotency, durable jobs, private files, PostgreSQL concurrency controls, race tests and traced requirements.

The main weakness is presentation and product cohesion. The current interface communicates “administrative prototype” more clearly than “finished institutional platform.” The backend, requirements and test evidence are more mature than the navigation, visual identity and specialized workflow presentations.

The project should not be described as complete institutional software yet. It should be described as:

> A working role-scoped university club operations prototype with versioned approvals, transactional booking, finance evidence and durable integration boundaries.

## 2. Strengths to preserve

### 2.1 Technical depth

- Django is the authoritative owner of workflows and records.
- FastAPI is isolated from database writes and only provides advisory assistance.
- PostgreSQL is used for constrained state, locking and overlap protection.
- Command writes use operation keys, expected revisions and atomic transactions.
- Domain decisions and audit entries are committed together.
- Immutable memo, event, budget and signature evidence is preserved.
- The application distinguishes allocations, scheduled releases, confirmed releases and verified expenses.
- Out-of-scope records are concealed as not-found responses.
- Durable jobs and notifications keep delivery attempts separate from business decisions.

Relevant implementation surfaces include:

- `apps/platform_core/protocol.py`
- `apps/platform_core/access.py`
- `apps/memos/models.py`
- `apps/memos/commands.py`
- `apps/events/booking.py`
- `apps/events/models.py`
- `apps/finance/calculations.py`
- `apps/finance/models.py`

### 2.2 Documentation and engineering evidence

- Stable FR, UC, AC, BR and NFR identifiers are used.
- Tests have requirement markers.
- Unit, integration, race, browser, contract and acceptance layers exist.
- Command, model and transaction conventions are documented.
- `ASSESSMENT.md` records known verification gaps instead of hiding them.
- The memo workflow has realistic rejection, revision and stale-state behavior.

### 2.3 Domain alignment

The implementation follows an important real-world ordering:

`Club and term -> Event draft -> Memo approval -> Venue booking -> Publication -> Finance -> Handover`

It also separates:

- Proposed venue from confirmed reservation
- Memo approval from venue confirmation
- Draft schedule from frozen event version
- Requested budget from allocation or release
- Receipt extraction from finance verification
- Internal event state from external delivery state

## 3. Major weaknesses

## 3.1 Generic visual identity

### Findings

- The CSS is visually based on a neutral shadcn-style administrative dashboard.
- It uses nearly the same card, panel, badge and table patterns on every module.
- The application name is visible, but there is little memorable brand imagery or personality.
- The IUB and Programming Club context appears mainly in text.
- There is no distinctive design language for approval, booking, finance or handover.
- The interface could represent almost any club, student affairs or back-office system.

### Impact

- The strongest implementation differences are not visually recognizable.
- The project does not look intentionally designed.
- Reviewers may underestimate the domain and technical depth.
- The UI appears generic even when the workflows are specialized.

### Fix

- Create one deliberate visual system with an IUB or Townkeepers-inspired accent, but do not claim an official IUB brand.
- Replace the universal neutral styling with purpose-built workflow motifs:
  - timeline and version progression for memos
  - venue map or occupied/time grid for bookings
  - ledger and reconciliation hierarchy for finance
  - term and ownership view for handover
- Establish a limited brand palette, typography scale and icon system.
- Add a product logo or monogram only if it is clear and original.
- Use familiar institutional colors carefully, avoiding a copied official IUB identity.
- Define panel roles instead of using one card style everywhere:
  - primary decision panel
  - evidence panel
  - audit panel
  - operational summary panel

Relevant surface: `static/css/app.css`.

## 3.2 Dashboard is a count-and-link screen

### Findings

- The dashboard heavily relies on item counts and repeated list panels.
- The metric cards are technically useful but not action-oriented.
- Counts do not explain risk, deadline, age or blocked dependencies.
- Some sections have an obvious empty state, but no coherent next-step hierarchy.
- The dashboard does not tell each role the complete story of the role’s highest-priority job.

### Impact

- Users must enter each module to understand what actually needs attention.
- The dashboard looks like a default admin template.
- It does not demonstrate the application’s end-to-end value.

### Fix

- Build role-specific dashboard compositions:
  - EB: next event, memo blocker, booking gap, budget state, pending handover
  - Advisor: memos and budgets requiring review, urgent deadlines, rejected revisions
  - Head: approval queue, conflicts, overdue decisions, delivery failures
  - Admin: inactive profiles, grants, failed deliveries, system policy
- Replace generic metric cards with concise work cards containing:
  - primary action
  - deadline or age
  - current stage
  - blocking dependency
- Use a primary “Continue” action for one high-priority item.
- Add exception and overdue signals instead of only counts.
- Keep navigation but make the dashboard a command centre rather than a report.

Relevant surfaces:

- `apps/accounts/dashboard.py`
- `apps/*/dashboard.py`
- `apps/accounts/templates/accounts/dashboard.html`

## 3.3 Long, uniform memo review page

### Findings

- Event details, budget, attachments, feedback and memo text are all separated but presented through visually identical details elements.
- Reviewers must scan before reaching the signature and decision.
- Additional signers and rejection actions are buried in a long signature panel.
- The memo text may be shown twice: as raw fields and in the memo preview.
- Version and stage context are clear in text but weak in visual hierarchy.

### Impact

- The memo workflow is technically complete but cognitively busy.
- A reviewer may miss the most important evidence or blocker.
- The interface underrepresents the application’s signature workflow.

### Fix

- Create a memo review layout with fixed zones:
  - left: workflow timeline and version selector
  - centre: event and memo evidence
  - right: decision and signature panel
- Make the approval timeline prominent.
- Put the current version, deadline and next action at the top.
- Display differences between the current and previous version directly.
- Limit the first view to:
  - event details
  - budget summary
  - memo text
  - required attachments
- Move detailed audit and historical feedback into separate tabs or panels.
- Keep rejection and withdrawal as explicit but secondary actions.
- On mobile, present a sticky “Review version” decision bar.

Relevant surfaces:

- `apps/memos/templates/memos/memo_review.html`
- `apps/memos/templates/memos/memo_detail.html`
- `apps/memos/templates/memos/_memo_body.html`

## 3.4 Memo detail does not tell a strong workflow story

### Findings

- Status, version, dates, action and evidence are presented as separate facts.
- Review history is a table-like sequence rather than a timeline.
- Amendments and audit entries do not clearly show provenance.
- Content hashes and internal IDs are visible in places where users need meaning, not implementation detail.

### Impact

- The next actor and the reason for the current state are understandable, but not immediately memorable.
- Users see transaction evidence instead of a coherent review story.
- The page is more suitable for administration than for an institutional owner.

### Fix

- Add an explicit vertical timeline:
  - submitted
  - Advisor confirmation or rejection
  - named signer endorsements
  - DoSA approval or rejection
  - revision or amendment
- Show the actor, role, date and reason at each node.
- Separate “current version” from “history.”
- Hide raw content hashes behind an evidence detail action.
- Show stale or superseded versions as evidence, not as action targets.
- Show amendment changes as a before-and-after diff.

## 3.5 Event detail is overloaded

### Findings

- Memo status, confirmed location, bookings, publishing, outcomes, finance and memos coexist on one page.
- Booking creation and move controls are embedded among unrelated actions.
- Publishing buttons can appear before a clear eligibility summary.
- Outcome entry, reach and success status are mixed with operational actions.

### Impact

- The event is not presented as a central record.
- Critical state can be hidden among many forms.
- Users may choose an operation before understanding its prerequisites.

### Fix

- Convert the event page into a project-style workspace with tabs or sections:
  - Overview
  - Permission memo
  - Venue
  - Publication
  - Finance
  - Outcome and handover
- Show a readiness summary at the top:
  - memo approved
  - venue confirmed
  - notice published
  - budget prepared
  - expenses verified
  - outcome entered
- Hide unavailable actions when prerequisites are missing; explain why they are unavailable.
- Keep one primary action and a secondary “More actions” area.
- Preserve independent status for memo, booking and publication.

## 3.6 Finance interface is a ledger form rather than a reconciliation workspace

### Findings

- Periods, allocations, releases, attributions, conversions, expenses and adjustments are stacked together.
- “Recorded balance” is not enough context to explain where funds came from or went.
- The release confirmation and expense review tables use cramped inline controls.
- Currency context is text-heavy.

### Impact

- It is difficult to reconcile one event or one club period.
- Users may confuse allocations, schedules and confirmed release amounts.
- The current interface hides the technical safeguards from reviewers.

### Fix

- Add separate finance views:
  - club summary
  - funding period
  - event reconciliation
  - expense queue
  - adjustment history
- Provide one reconciliation card for:
  - allocation
  - scheduled release
  - confirmed release
  - attributed inflow
  - verified expense
  - adjustments
  - remaining balance
- Show one currency per reconciliation block.
- Provide a warning for missing conversion or mixed-currency evidence.
- Replace inline table controls with dedicated review dialogs or detail pages.
- Add receipt preview alongside submitted amounts.

## 3.7 Forms expose too much implementation detail

### Findings

- Operation keys, expected revisions and internal route decisions are frequently hidden.
- Placeholder-only controls are used for important finance and booking actions.
- Several forms rely on raw text inputs where controlled values or contextual selection are available.
- Some error recovery depends on going back or reading a domain message.

### Impact

- Important actions look provisional or difficult to understand.
- Users may enter data in the wrong state or format.
- The interface does not prevent mistakes as strongly as the domain layer does.

### Fix

- Use dedicated forms for every write, with clear field labels and instructions.
- Use date, time, currency and headcount controls appropriate to the field.
- Show validation immediately and preserve entered values.
- Add contextual summaries and calculated preview values before submission.
- Make stale and conflict responses offer one direct recovery action.
- Never ask the user to understand an operation key or revision number.

## 3.8 Navigation is too flat

### Findings

- The sidebar has an ungrouped list of modules, account actions and operational actions.
- Notifications and failed deliveries sit alongside core institutional modules.
- On mobile, the navigation collapses, but all modules remain a flat list.
- The first-level navigation does not communicate information architecture.

### Impact

- Users cannot quickly distinguish working features from administration and recovery.
- The interface is harder to learn for infrequent actors.

### Fix

- Group navigation into:
  - Workspace
  - Approvals
  - Events and venues
  - Finance
  - Clubs
  - Administration
- Show modules only if the actor has meaningful access.
- Use badges only for true pending work.
- Separate user profile and sign-out from business navigation.
- Add breadcrumbs and contextual back navigation.

## 3.9 Mobile behavior is responsive but not mobile designed

### Findings

- The implementation uses one sidebar that becomes a disclosure.
- Tables switch to stacked labelled rows.
- Long forms remain long and linear.
- Signature canvases and large dialogs have limited mobile optimization.
- There is no role-specific mobile priority view.

### Impact

- The app may be usable on phones, but it does not feel purpose-built.
- Advisors and EB members will be less likely to review or act while away from a desktop.

### Fix

- Build mobile-first action pages for review and approval.
- Use a sticky bottom action area for primary decisions.
- Reduce review evidence to expandable sections.
- Make the signature canvas support clear, touch and typed alternatives reliably.
- Add horizontal venue-time views or an accessible list fallback.
- Test mobile with real keyboard, touch and text enlargement behavior.

## 3.10 Status and state are not visually encoded consistently

### Findings

- Status text is repeated in badges and facts.
- Many state transitions use only labels.
- Blocked, pending and complete states may look similar.
- Delivery failure and business approval are presented in separate views.

### Impact

- Users cannot scan a complex record quickly.
- The UI does not communicate why work is blocked or which state is authoritative.

### Fix

- Establish state semantics:
  - neutral: no action yet
  - active: action required
  - waiting: another actor owns the action
  - success: confirmed
  - warning: late or missing evidence
  - danger: rejected, failed or denied
- Show the authoritative state and pending delivery separately.
- Add explanations next to status labels.
- Use icons and text, not colour alone.

## 3.11 External-looking integrations are not a visible part of the experience

### Findings

- FastAPI assistance, OCR and external publishing exist as contracts or partial slices.
- The UI does not explain advisory versus authoritative status strongly enough.
- Users may interpret extracted amounts or AI candidates as approved.
- Failed delivery and successful business state need clearer separation.

### Impact

- Integration uncertainty could reduce trust.
- Users may not understand why assistance is unverified or unavailable.

### Fix

- Add clear labels:
  - “Advisory candidate”
  - “Unverified extraction”
  - “Internal state confirmed”
  - “External delivery pending”
- Keep manual search, manual receipt entry and manual publishing available.
- Add retry and last-known-result information to the delivery view.
- Never allow an advisory result to bypass a Django command or domain review.

## 3.12 Live institutional data and identity are absent

### Findings

- Live IUB Google sign-in is pending.
- The demo bypass is useful but makes public demonstration less credible.
- Venue capacities, restrictions and organizations are synthetic.
- Official lead times and institutional policy decisions are unresolved.
- Email and external publication require configuration.
- Real receipts and provider behavior are not available.

### Impact

- The system cannot honestly be presented as production IUB software.
- Screenshots and demos can appear synthetic to reviewers.
- Institutional risk and policy questions remain unresolved.

### Fix

- Keep synthetic labels on every demo-only object.
- Complete the live IUB Google configuration in a controlled staging environment.
- Obtain and document official:
  - venue ownership and routing
  - actual venue capacities
  - working-day rules
  - lead-time policy
  - Department Head routing
  - finance authority
  - publication destinations
- Remove demo sign-in automatically outside development.
- Add a deployment and operator readiness screen.

## 3.13 Verification gaps reduce credibility

### Findings

- The assessment records the following as pending:
  - Live Google sign-in
  - GitHub Actions
  - load tests
  - restore rehearsal
  - axe and screen-reader review
  - Firefox, Safari and Edge review
  - peer review
  - Wiki and pull-request evidence

### Impact

- The project has strong local evidence but an incomplete release story.
- Accessibility and cross-browser claims are not yet established.

### Fix

- Push the repository and run CI.
- Complete a restore rehearsal.
- Run an accessibility scan and manual keyboard/screen-reader review.
- Test Chromium, Firefox and Safari or WebKit where available.
- Run the race suite with independent PostgreSQL connections in CI.
- Record exact passing commands and failures in `ASSESSMENT.md`.
- Remove or replace outdated “not yet” statements.

## 3.14 Handover and analytics are not sufficiently visible

### Findings

- Handover, analytics and historical imports are defined in the product but only partially visible.
- The EB term is central to original ownership, yet the interface may not help the outgoing President transfer unfinished work.
- Completed-event reporting may be fragmented.

### Impact

- The project does not demonstrate the leadership-change journey that distinguishes it from a memo tracker.
- Year-end reporting may not feel tied to source evidence.

### Fix

- Add an outgoing/incoming handover workspace.
- Show all unfinished records attributed to the term.
- Let the President acknowledge, assign and transfer responsibility.
- Preserve original term IDs and authorship.
- Add a year-end term view with:
  - completed events
  - outcome status
  - attendance
  - verified expenditure
  - booking and publication result
- Mark unknown reporting values instead of converting them to zero.

## 4. Technical weaknesses

## 4.1 Views may remain too large

Some view modules are still responsible for composing many independent surfaces and forms. This is not necessarily incorrect, but it makes browser behavior harder to reason about.

### Fix

- Keep request parsing in views.
- Keep authorization and state changes in commands.
- Keep read composition in selectors and dashboard modules.
- Move complex display calculations to tested presentation helpers.
- Reduce view-specific domain decisions.

## 4.2 Access and demo behavior are tightly coupled

The access engine includes demo permission behavior and real authorization behavior. This supports demonstration but increases the risk of demo rules leaking into production.

### Fix

- Keep demo permissions in a development-only adapter.
- Production settings should reject demo authentication and demo grants.
- Test that every demo grant is absent in production-like settings.
- Separate user-category ceilings from actor-specific grants more visibly in documentation.

## 4.3 User-visible changes need more specialized tests

The suite is strong, but UI-specific tests are concentrated around browser journeys and page smoke tests.

### Fix

- Add browser tests for:
  - stale memo review
  - long memo rejection and revision
  - booking conflict and replacement
  - mobile navigation
  - finance mixed-currency attempt
  - handover and term ownership
  - external delivery failure recovery
- Test keyboard navigation and focus behavior for dialogs.
- Test mobile layouts and text at 200% zoom.

## 4.4 Real integrations need failover evidence

OCR, scheduling, priority and publishing clients exist, but real provider availability and recovery remain unverified.

### Fix

- Test timeout, malformed payload, stale candidate, duplicate delivery and duplicate retry.
- Run manual fallbacks with each provider unavailable.
- Verify that no provider can change authoritative records without Django policy checks.
- Confirm that provider failures leave business decisions unchanged.

## 4.5 Empty and partial states need more explicit UI contracts

Several dashboard and detail pages know about missing deadlines, missing institutional values and missing official data.

### Fix

- Define and test every empty state.
- Distinguish:
  - no records
  - records outside scope
  - missing required institutional value
  - no live provider data
  - data intentionally unknown
- Never use zero as a substitute for missing information.

## 5. Priority implementation plan

## Priority 0: Release honesty

- Mark live dependencies clearly as pending or demo-only.
- Complete or narrow the production sign-in path.
- Push and run CI.
- Complete the strongest end-to-end test journey.
- Update stale assessment counts and evidence.

## Priority 1: Memo experience

- Rebuild memo review as a timeline-plus-evidence-plus-decision experience.
- Rebuild memo detail with version and amendment storytelling.
- Improve mobile review and signature usability.
- Add memo diff and previous-feedback visibility.

## Priority 2: Event workspace

- Split event detail into overview, memo, venue, publication, finance and outcome areas.
- Add an event readiness summary.
- Make prerequisite blockers explicit.
- Add a dedicated booking and move workspace.

## Priority 3: Finance reconciliation

- Create club summary and event reconciliation screens.
- Separate period, ledger and expense queues.
- Improve release, attribution and adjustment explanations.
- Add receipt evidence beside the verification decision.

## Priority 4: Dashboard and navigation

- Replace flat navigation with grouped role-based navigation.
- Create role-specific next-action dashboards.
- Prioritize deadlines and blockers over generic counts.
- Keep true pending work badges concise.

## Priority 5: Visual identity

- Replace the neutral template system with a limited Townkeepers visual language.
- Improve typography, state hierarchy and domain-specific components.
- Complete desktop and mobile page specifications.
- Audit the interface using accessibility, keyboard and browser tests.

## Priority 6: Complete the remaining product

- Publishing
- Analytics
- Historical imports
- Handover
- Real institutions and providers
- Reporting and export

## 6. Suggested one-release UI scope

The most persuasive next release should demonstrate one complete scenario with a coherent visual system:

1. EB creates an event.
2. EB prepares the memo and optional budget.
3. Advisor reviews and may reject or confirm.
4. Additional signer endorses or returns.
5. Head approves.
6. EB submits a venue request.
7. Required approver confirms the booking.
8. EB publishes the approved internal notice.
9. EB submits evidence and expense.
10. Reviewer verifies expense.
11. Event closes and the outcome is recorded.
12. Term handover lists unfinished work and transfer history.

The UI and test suite should make this journey easy to demonstrate in under 15 minutes.

## 7. Acceptance criteria for the redesign

The redesign should be complete only when it satisfies all of the following:

- A reviewer can identify the current state and next actor within five seconds.
- Every rejection, return and stale state explains how to recover.
- Every protected action is denied consistently by direct request and normal UI.
- Every screen separates authoritative state from advisory or delivery state.
- Synthetic demo data is clearly identified.
- No mixed-currency balance is presented as a combined figure.
- Mobile users can complete a memo decision without desktop-only controls.
- Every status is available as text and not through colour alone.
- Every form is labelled, keyboard reachable and connected to error fields.
- A complete event journey works with providers unavailable.
- Tests cover the success path, refusal path, stale retry, duplicate operation and recovery path.

## 8. Requirement alignment

The analysis applies primarily to:

- FR-IAM-02: persona, scope and privileges
- FR-IAM-06: role dashboard and navigation
- FR-MEM-02 to FR-MEM-13: memo editing and decision lifecycle
- FR-EVT-03 to FR-EVT-12: venue and event lifecycle
- FR-FIN-01 to FR-FIN-10: finance and evidence
- FR-PUB-01 to FR-PUB-06: publication lifecycle
- FR-ANL-01 to FR-ANL-06: analytics and handover
- FR-COM-01 to FR-COM-06: shared platform behavior
- NFR-USE-01 to NFR-USE-04: usability
- NFR-ACC-01 to NFR-ACC-02: accessibility
- NFR-REL-01 to NFR-REL-02: recovery and resilience
- BR-02, BR-05, BR-06, BR-07, BR-09 and BR-11

The final requirement coverage status must be confirmed with:

`uv run python tools/check_req_markers.py --markdown`

## 9. Verification plan

Before each visual or workflow phase, run the smallest relevant test set, then run the full gate when the phase is complete.

```sh
uv run ruff format --check .
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
uv run pytest
```

Additional required verification:

- Browser journey for EB → Advisor → signer → Head
- Stale review and duplicate decision tests
- Booking conflict and two-day race tests
- Mixed-currency and adjustment finance tests
- Mobile keyboard and touch tests
- Accessibility scan and manual screen-reader review
- Cross-browser smoke tests
- Provider timeout and malformed-response tests
- Restore and worker recovery rehearsal
- Production-like `check --deploy`

## 10. Final judgement

Townkeepers has strong institutional-domain and engineering foundations. The backend is not generic; the current presentation is.

The next phase should not primarily add modules. It should:

1. Make the memo lifecycle visually unmistakable.
2. Turn the event page into a clear workspace.
3. Turn finance into a reconciliation experience.
4. Replace flat navigation with role-based workspaces.
5. Establish an intentional visual identity.
6. Remove or clearly label demo-only elements.
7. Complete the verification and release evidence.

This would make the project feel less like a collection of correctly implemented Django forms and more like a purpose-built university operations platform.

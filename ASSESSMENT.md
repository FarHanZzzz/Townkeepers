# Assessment evidence

This file collects the course evidence required by AGENTS.md section 7, TECHNICAL_REQUIREMENTS.md section 9 and PRD Appendix C.3. Add a row with every change. Report skipped or failing checks exactly as they happened.

## 1. Build and environment

| Item | Value |
|---|---|
| Build revision | Working tree on `main` after commit `9776360` (changes not yet committed) |
| Policy version | Initial synthetic `PolicyVersion` from migration `platform_core/0002`: 7 days, 1 month, approval buffer 2 days, review window 3 days, working days Sunday to Thursday |
| Test data | Synthetic only: `tests/factories.py`, `tests/memo_helpers.py`, and `seed_demo` (`@townhall.test`) |
| Environment | Windows 11, Python 3.13.7, PostgreSQL 17.12 (local service), Django 6.1.3, FastAPI 0.165.0, Playwright Chromium |

## 2. Change log (PRD C.3 format)

| Change | FR / UC | Entry points | Tests actually run | Migration effects | Remaining verification |
|---|---|---|---|---|---|
| Platform core | FR-COM-02/03/04/06, FR-IAM-08 | `protocol.execute`, `audit.record`, `jobs.run_once`, `/files/<uuid>/`, `/exports/<id>/`, `/deliveries/`, `/settings/policy/`, `/health/*`, `run_worker` | `tests/integration/test_platform_core.py` (9 passed), `tests/unit/test_deadline_policy.py` (7 passed) | `platform_core/0001` tables; `0002` adds `btree_gist`, the audit trigger and the initial synthetic policy | Restore rehearsal (NFR-REL-02); worker under load |
| Increment 1 accounts | FR-IAM-01 to 07, UC-01 to 04 | `/auth/google/start`, `/auth/google/callback`, `/auth/sign-out/`, `/dev/login/`, `/profile/`, `/accounts/...`, `bootstrap_admin` | `test_provisioning.py` (9), `test_accounts.py` (24), AC-15, AC-17 | `accounts/0001` | Live IUB Google client and domain (pending live verification) |
| Increment 1 clubs | FR-CLB-01 to 05 and 07, UC-06 to 08 | `/clubs/...`, `seed_demo` | `test_clubs.py` (10) | `clubs/0001` | Handover (FR-CLB-06) in Increment 6 |
| Increment 2 events and budget | FR-EVT-01/02, FR-FIN-04, UC-11, UC-27 | `/events/...`, `/finance/events/<id>/budget/` | `test_events_budget.py` (8) | `events/0001`, `finance/0001` | Approved-event amendments (Increment 3) |
| Increment 2 memos | FR-MEM-01 to 13, UC-18 to 26 | `/memos/...`, `POST /memos/<id>/decisions` (form and JSON), `/memos/<id>/preview/`, `/memos/<id>/export` | `test_memos.py` (17), AC-01 (2), AC-13, AC-16, `tests/race` (4), `tests/browser` (1) | `memos/0001` | Event, venue and notice effects of approved amendments (Increments 3 and 5) |
| Assistance service | TR sections 1, 2, 6; FR-AIS-05/06, FR-AIP-06 | `assistance.app:app`, `assistance.client` | `tests/contract` (9) | None (no database) | Real provider approval (PRD C.2) |
| Workspace presentation and demonstration fill | FR-IAM-06 | Dashboard template, `static/css/app.css`, `seed_demo` | `seed_demo` against the local database; browser check of the DoSA Head dashboard at 1440px. Full gate re-run after the calendar pass (section 9) | None | Sign in as the Advisor, President and Department Head to see their own queues |
| Calendar workspace | FR-EVT-03, FR-EVT-10, UC-33 | `/events/calendar/`, `/events/calendar-data/`, `/events/venue-availability/`, event and booking forms | `tests/integration/test_calendar_workspace.py` (5), `tests/integration/test_booking_calendar.py` (1), full gate (section 9); browser check of the booking popup at 785 px: four synthetic venues loaded, selection returned date/time/venue, no console errors | None | Week view and separate date filter for FR-EVT-10; screen-reader and phone-width check of the popup |
| Navigation scope | FR-IAM-06 | Sidebar through `platform_core.context_processors.navigation` | `tests/integration/test_navigation_scope.py` (4); full suite 151 passed | None | Confirm the reduced sidebar for the seeded Advisor and President in a browser |
| DoSA-only restricted hours | FR-EVT-03 | `/events/venues/restrict/`, Venues screen, `booking.add_restriction` | `tests/integration/test_venue_restriction_scope.py` (11); full suite 151 passed | None | None |

## 3. Quality gate results (AGENTS.md section 5), PostgreSQL 17

| Command | Result |
|---|---|
| `uv run ruff format --check .` | Pass: all files formatted |
| `uv run ruff check .` | Pass: all checks passed |
| `uv run python manage.py check` | Pass: no issues |
| `uv run python manage.py makemigrations --check --dry-run` | Pass: no changes detected |
| `uv run python manage.py migrate --noinput` | Pass |
| `uv run pytest` | Pass: 151 passed, 0 skipped, 0 failed. One warning comes from the pytest-playwright plugin fixture, not from project code |
| `manage.py check --deploy` (production settings, SMTP) | Pass: no issues |
| `tools/check_req_markers.py` | Pass: no unknown IDs |
| `sphinx-build -W` | Pass |
| GitHub Actions | **Not yet run.** The repository has not been pushed |

The final verification run is recorded in section 9.

## 4. Acceptance scenarios (PRD Appendix B)

| AC | Result | Test | Role(s) and data | Notes |
|---|---|---|---|---|
| AC-01 | Pass | `tests/acceptance/test_ac01_memo_resubmission.py` (2), `tests/browser/test_memo_journey.py` | EB President, Advisor, Department Head signer, DoSA Head; synthetic club | Rejection email reaches the EB and Advisor; version 2 needs fresh signatures; the Department Head blocks the Head queue until endorsing |
| AC-13 | Pass | `tests/acceptance/test_ac13_template_versioning.py` | Head, EB | The submitted memo keeps template version 1 after revision and deactivation |
| AC-15 | Pass | `tests/acceptance/test_ac15_account_access.py` | Admin, Head, EB, Advisor | Personal Google, inactive and anonymous requests are denied; out-of-scope club returns 404 |
| AC-16 | Pass | `tests/acceptance/test_ac16_advisor_rejection.py`, `tests/race/test_memo_races.py::test_simultaneous_head_approve_and_reject_commit_exactly_one_decision` | Advisor, Head | The Head gets no rejection email; two connections at a barrier produce one decision |
| AC-17 | Pass | `tests/acceptance/test_ac17_permission_changes.py` | EB Treasurer, Head | A previously opened event and budget link returns 404 after the assignment ends |
| AC-18 | Partial | `tests/race/*`, `test_platform_core.py` | | Memo handoff, decision replay and email retry pass. Venue and finance parts come in Increments 3 and 4 |
| AC-19 | Partial | `tests/unit/test_deadline_policy.py` | | 7-day, 6-day, month-end and leap-year boundaries pass. Venue intervals come in Increment 3 |
| Others | Not started | | | See `docs/IMPLEMENTATION_CONTEXT.md` section 8.3 |

## 5. Coverage (measured, reported separately)

| Scope | Command | Result |
|---|---|---|
| Unit and contract only | `pytest tests/unit tests/contract --cov` | 25% of `apps`, `assistance` and `config` (16 tests; pure policy and assistance modules covered 78% to 98%) |
| Full suite (unit, integration, race, contract, browser, acceptance) | `pytest --cov` | 82% (4,541 statements, 803 missed) |

## 6. Docstring coverage inventory

`uv run interrogate -v` over `apps/*/commands.py` (nested handler closures and private helpers excluded, threshold 90%):

| Module | Covered |
|---|---|
| accounts/commands.py | 16/16 |
| clubs/commands.py | 12/12 |
| events/commands.py | 6/6 |
| finance/commands.py | 4/4 |
| memos/commands.py | 18/18 |
| platform_core/commands.py | 3/3 |
| **Total** | **59/59 (100%)** |

**Qualitative examples, one per major domain.** Each states actor scope, inputs, transaction effects, errors, the FR, and why a stale or repeated call is safe.

- **Accounts:** `provision_profile`. Actor is a System Admin, or a DoSA Head for signer, EB and Advisor profiles. The profile, grants, audit, notice and email job commit together. A replay returns the same profile, and the case-insensitive unique index rejects a concurrent duplicate.
- **Clubs:** `correct_archive_record`. Only closed terms can be corrected. The previous value is kept in `ArchiveCorrection`. A superseded revision raises `StaleRevisionError`.
- **Memos:** `decide_memo`. Explains each stage's actor, the notification recipients (an Advisor rejection does not email the Head), and how concurrent decisions serialize on the memo lock and the one-decision-per-stage constraint.
- **Finance:** `save_budget_version`. Versions are immutable. A stale `expected_version_number` raises without changing any existing version.
- **Platform:** `jobs` module docstring. States the lock discipline and the delivery guarantee (one intent per side effect, no promise of exactly-once email).

The HTML API reference is built by `uv run sphinx-build -W -b html docs/sphinx docs/sphinx/_build/html`.

## 7. Heuristic inspection: Nielsen's ten heuristics

Inspection by the implementer on synthetic data. A human peer review is still required (section 8).

| # | Heuristic | Finding | Evidence |
|---|---|---|---|
| 1 | Visibility of system status | Every memo page shows status, version, next actor, and the separate handoff, queue, deadline and event dates. Delivery status is visible per notice | [advisor-review-desktop.png](docs/assessment/advisor-review-desktop.png) |
| 2 | Match with the real world | Office Memo layout follows Appendix D (To, Through, From, Date, Subject); campus time shown as "(Dhaka)"; BDT amounts | `memos/_memo_body.html` |
| 3 | User control and freedom | The reject dialog has "Keep pending"; drafts are saved incomplete; rejected memos reopen as a revision; withdrawal comes with a reason | [reject-dialog-desktop.png](docs/assessment/reject-dialog-desktop.png) |
| 4 | Consistency and standards | One form renderer; consistent action labels (SDS); statuses shown as text badges with symbols | `templates/includes/*.html`, `static/css/app.css` |
| 5 | Error prevention | Irreversible actions ask for confirmation; reject needs a reason and a confirmation tick; send lists missing items first; stale pages are refused with the current state | [memo-draft-desktop.png](docs/assessment/memo-draft-desktop.png) |
| 6 | Recognition rather than recall | Recipient guidance next to To and Through; template instructions on the draft; dashboards list pending work | memo draft screen |
| 7 | Flexibility and efficiency | The dashboard links straight to the review; the queue is ordered by deadline; status filters on memo and event lists | `memos/memo_list.html` |
| 8 | Aesthetic and minimalist design | Plain layout; review sections collapse (Budget, Attachments, Earlier feedback) | review screen |
| 9 | Recover from errors | Error summary at the top with links to the fields, focus moved to it, entered values kept; domain errors explain how to proceed | `includes/form.html`, `static/js/app.js` |
| 10 | Help and documentation | Help text on fields such as the proposed venue ("does not reserve a room") and the requested amount ("not an allocation"); README and runbook | forms |

**Issues found and fixed during inspection:**
- Raw `18:00:00` times on the review summary, now shown as `18:00`.
- The confirmation label "I confirm this reject" changed to "I confirm rejecting".
- Extra top spacing on panel headings.
- Calendar CSS written in the previous pass contained a UTF-8 BOM and mojibake (`â€”` for `—`); rewritten as plain UTF-8.
- Superseded first-draft calendar CSS removed, and the new `.cal-legend` markup given a layout rule.
- Booking forms now start with an empty venue choice; submitting without one opens the picker and marks the field.
- Browser check showed the popup close button dropping below the title after CSS cleanup; the flex rule was restored.

## 8. Accessibility, responsive and cross-browser review

| Check | Status |
|---|---|
| Keyboard-only memo decision | Pass (automated): the typed-signature path in `tests/browser/test_memo_journey.py` uses label-based controls only |
| Labels and errors linked (`aria-describedby`, `aria-invalid`), error summary focus | Implemented in `includes/field.html` and `app.js`; screen-reader review **pending** |
| Status shown in text, not colour alone | Implemented (badges carry text and a symbol) |
| Phone layout (390 px) | Checked by screenshot: navigation collapses into a Menu disclosure, tables stack as labelled rows ([advisor-dashboard-mobile.png](docs/assessment/advisor-dashboard-mobile.png)) |
| Automated accessibility scan (axe) and WCAG 2.2 AA manual review | **Pending** |
| Firefox, Safari, Edge | **Pending** (Chromium only so far) |

## 9. Final verification run (this change)

Run on 27 Nov 2026 against local PostgreSQL 17.12 after the calendar workspace pass and its documentation changes. The previous Increments 1 and 2 run on 22 Nov 2026 is superseded by these numbers:

| Step | Exit | Last line of output |
|---|---|---|
| `ruff format --check .` | 0 | 185 files already formatted |
| `ruff check .` | 0 | All checks passed! |
| `python manage.py check` | 0 | System check identified no issues (0 silenced). |
| `python manage.py makemigrations --check --dry-run` | 0 | No changes detected |
| `python manage.py migrate --noinput` | 0 | No migrations to apply. |
| `pytest` | 0 | 151 passed, 1 warning (pytest-playwright plugin) |
| `python tools/check_req_markers.py` | 0 | FR 66/91, UC 19/47, AC 15/20, NFR 10/22, BR 4/12 referenced; no unknown IDs |
| `interrogate apps/*/commands.py` | 0 | PASSED (minimum 90.0%, actual 100.0%) |
| `sphinx-build -W -b html docs/sphinx docs/sphinx/_build/html` | 0 | Build succeeded, no warnings |
| `manage.py check --deploy` (production settings, SMTP backend) | not re-run in this pass | Previously passed with no issues; `DEMO_AUTH=true` correctly fails with `townhall.E001` |

The commands were run with `.venv\Scripts\python.exe` and the venv executables because `uv` is not on this machine's PATH. Not run: the GitHub Actions pipeline (nothing pushed yet), load tests (NFR-PER-01/02), restore rehearsal (NFR-REL-02), screen-reader and non-Chromium browser reviews.

## 10. Peer review, team and Wiki links

| Item | Link |
|---|---|
| Pull request and GitHub review | _to be added after push_ |
| Team card | _to be added_ |
| Wiki: coverage and heuristic evidence | _to be added_ |
| Release rehearsal tag | _to be added_ |

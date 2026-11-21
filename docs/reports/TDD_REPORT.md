# TDD report: Increments 1 and 2

This report follows AGENTS.md section 1 (one behavior at a time: red, green, refactor) and TECHNICAL_REQUIREMENTS.md section 7. Each slice names its requirement, the failing evidence, the change that made it pass, and the regression tests added afterwards.

## 1. First slice: first-Head provisioning (PRD Appendix C.3)

| Step | Evidence |
|---|---|
| Requirement | FR-IAM-03, UC-02, AC-15: "A failing test for a duplicate institutional address" |
| Red | `tests/integration/test_provisioning.py::test_provisioning_rejects_duplicate_iub_address` was written before `apps/accounts/commands.py` existed. Run: `uv run pytest tests/integration/test_provisioning.py` gave `ImportError while importing test module ... ModuleNotFoundError: No module named 'apps.accounts.commands'`, which is the missing behavior, not broken setup |
| Green | Smallest path: `ProfileInput`, `provision_profile` with a case-insensitive duplicate check plus the `profile_unique_iub_email` index, a grant set, an audit row and one invitation job. The same run gave `1 passed in 1.70s` |
| Refactor and extend | Added the slice's denial, retry and race paths: replay with the same key, key reuse with different content (409), the Head's delegation limit, out-of-role and unknown grants, missing fields and an ineligible domain, a single active Head, idempotent `bootstrap_admin`, and `test_concurrent_provisioning_of_one_address_creates_one_profile` (two connections) |

## 2. Slices and their first failing tests

| Slice | Requirement | First failing test | Paths added afterwards |
|---|---|---|---|
| Durable email intent | FR-COM-02, AC-18 | `test_worker_recovers_an_expired_lease_and_keeps_one_email_intent` | Failure leads to retryable, then failed, then manual retry; repeated `notify` creates no duplicates |
| Audit immutability | FR-COM-03, NFR-SEC-04 | `test_audit_entries_cannot_be_edited_or_deleted` | Trigger in migration `platform_core/0002` |
| Upload protection | FR-COM-06 | `test_upload_validation_sniffs_content_and_enforces_size` | Unregistered owner type gives 404; anonymous request redirects |
| Sign-in | FR-IAM-01, AC-15 | `test_first_sign_in_binds_issuer_and_subject_and_later_uses_the_binding` | Six denial cases, explicit test account, session rotation, deactivation, demo isolation |
| Scope | FR-IAM-02/04, AC-17 | `test_grant_change_applies_to_the_next_request_on_an_open_page` | Empty grants, stale or self edits, inclusive assignment dates |
| Profile corrections | FR-IAM-05 | `test_ordinary_correction_applies_once_and_is_audited` | Protected routing, changed-during-review conflict, invalid values |
| Terms and appointments | FR-CLB-02/03 | `test_overlapping_terms_are_blocked_unless_a_transition_is_approved` | No early access, close ends access, single-holder posts, archive corrections |
| Deadline policy | FR-MEM-11, AC-19 | `test_exactly_seven_days_is_on_time_and_six_days_is_late` | Month-end and leap-year clamps, Big precedence |
| Budget versions | FR-FIN-04, AC-03 | `test_budget_revisions_keep_earlier_versions_and_identify_changed_lines` | Stale save, invalid amounts, Advisor endorse or return |
| Memo send | FR-MEM-05/06 | `test_send_freezes_version_records_dates_and_notifies_advisor_once` | Missing items, attachments, late flag, double send (race) |
| Memo decisions | FR-MEM-04/07/08 | `test_out_of_sequence_or_unassigned_reviewers_cannot_decide` | Extra signers, signer return, stale reviewer, simultaneous Head decisions (race), JSON endpoint |
| Revision, withdrawal, amendment | FR-MEM-09/12/13 | `test_revision_after_rejection_needs_fresh_signatures` | Withdraw eligibility, amendment keeps the approved version, PDF export access |
| Assistance contracts | FR-AIS-05/06, FR-AIP-06 | `test_endpoints_require_the_service_token` | Invented candidate filtered, malformed gives 502, timeout gives 503, stopped service falls back, unknown fields give 422, OCR digest check |

## 3. Defects found by tests (regression tests first, AGENTS.md section 1.4)

| Defect | How it was found | Fix | Regression test |
|---|---|---|---|
| `SELECT ... FOR UPDATE` with `select_related` on a nullable foreign key raised `NotSupportedError: FOR UPDATE cannot be applied to the nullable side of an outer join` | `test_stale_draft_save_keeps_the_newer_version` and the budget review tests failed on PostgreSQL | `select_for_update(of=("self",))` in `save_event_draft`, `review_budget_request`, `set_template_active` and `_lock_memo` (which also follows the documented memo-only lock) | `tests/integration/test_events_budget.py` (3 tests) |
| Transactional tests truncate the migration-seeded policy, so later sends failed with "No workflow policy is in force" | Two race tests failed after the first race test truncated tables | `initial_policy` fixture in `tests/conftest.py`, used by race and browser tests | `tests/race/test_memo_races.py` |
| Test expectation error: an EB member of another club acting as a signer received 404 (concealed), not 403 | `test_additional_signer_must_endorse_before_the_head_queue` | The test now asserts 404 for the other club and 403 for a same-club member without a task, which is the correct behavior per BR-01 and AC-11 | Same test |
| Browser journey: the drawn signature was not captured because the canvas was outside Playwright's 1024x576 viewport | Playwright screenshot showed "Add your e-signature before continuing" | Scroll the canvas into view before drawing. Product behavior was correct | `tests/browser/test_memo_journey.py` |

## 4. Test layers (AGENTS.md section 4)

| Layer | Location | Count |
|---|---|---|
| Pure Python | `tests/unit/` | 7 |
| Django request and command | `tests/integration/` | 78 |
| PostgreSQL transaction (independent connections, Barrier) | `tests/race/` | 4 |
| FastAPI contract (real HTTP server) | `tests/contract/` | 9 |
| Browser journey (Playwright) | `tests/browser/` | 1 |
| Acceptance (PRD Appendix B) | `tests/acceptance/` | 6 |
| **Total** | | **105 passing** |

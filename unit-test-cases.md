# Unit Test Cases Conducted

## Run details
- **Command:** `& ".venv\Scripts\python.exe" -m pytest tests/unit -v`
- **Date run:** 2026-11-27 (local workspace run)
- **Result:** **13 passed, 0 failed** (0.39s)
- **Scope:** `tests/unit` (booking policy and deadline policy)

## Test cases

| # | Test file | Test case | What it verifies |
|---|-----------|-----------|------------------|
| 1 | `tests/unit/test_booking_policy.py` | `test_identical_partial_and_contained_ranges_overlap_and_adjacent_ones_do_not` | Overlap detection treats identical, partial, and contained time ranges as conflicts, while adjacent ranges do not overlap. |
| 2 | `tests/unit/test_booking_policy.py` | `test_setup_buffer_makes_an_otherwise_adjacent_booking_overlap` | Setup/transition buffer causes an otherwise adjacent booking to be treated as overlapping/conflicting. |
| 3 | `tests/unit/test_booking_policy.py` | `test_large_venue_rejects_349_accepts_350_and_rejects_over_capacity` | Large-venue capacity boundary: 349 rejected, 350 accepted, and over-capacity rejected. |
| 4 | `tests/unit/test_booking_policy.py` | `test_evening_classroom_routes_to_advisor_then_dosa_without_a_department_head` | Evening classroom booking routes to Advisor then DoSA (no department head in that path). |
| 5 | `tests/unit/test_booking_policy.py` | `test_friday_full_day_routes_to_dosa_then_admin_and_a_hall_routes_to_dosa` | Friday full-day booking routes to DoSA then Admin; hall booking routes to DoSA. |
| 6 | `tests/unit/test_booking_policy.py` | `test_two_day_booking_is_consecutive_and_a_longer_span_is_rejected` | Two-day booking is accepted as consecutive; longer spans are rejected. |
| 7 | `tests/unit/test_deadline_policy.py` | `test_submission_target_follows_calendar_days_and_months[first_date0-False-target0]` | Submission target calculation follows calendar days/months for parametrized case 1. |
| 8 | `tests/unit/test_deadline_policy.py` | `test_submission_target_follows_calendar_days_and_months[first_date1-True-target1]` | Submission target calculation follows calendar days/months for parametrized case 2. |
| 9 | `tests/unit/test_deadline_policy.py` | `test_submission_target_follows_calendar_days_and_months[first_date2-True-target2]` | Submission target calculation follows calendar days/months for parametrized case 3. |
| 10 | `tests/unit/test_deadline_policy.py` | `test_submission_target_follows_calendar_days_and_months[first_date3-True-target3]` | Submission target calculation follows calendar days/months for parametrized case 4. |
| 11 | `tests/unit/test_deadline_policy.py` | `test_exactly_seven_days_is_on_time_and_six_days_is_late` | Boundary check: exactly 7 days before is on time; 6 days before is late. |
| 12 | `tests/unit/test_deadline_policy.py` | `test_big_takes_precedence_and_uses_the_calendar_month_boundary` | Big-event rule takes precedence and uses calendar month boundary. |
| 13 | `tests/unit/test_deadline_policy.py` | `test_default_approval_deadline_counts_back_from_the_first_date` | Default approval deadline is calculated by counting back from the event’s first date. |

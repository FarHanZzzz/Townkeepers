"""Pure-Python boundaries for the submission deadline rule (FR-MEM-11, AC-19)."""

from datetime import date

import pytest

from apps.platform_core.policy import (
    default_approval_deadline,
    is_late_submission,
    submission_target,
)

RULE = {"standard_lead_days": 7, "big_event_lead_months": 1}


@pytest.mark.req("FR-MEM-11", "AC-19")
@pytest.mark.parametrize(
    ("first_date", "is_big", "target"),
    [
        (date(2026, 12, 18), False, date(2026, 12, 11)),  # PRD 2.6 classroom workshop example
        (date(2027, 3, 31), True, date(2027, 2, 28)),  # PRD 2.6 Big event with month-end clamp
        (date(2028, 3, 31), True, date(2028, 2, 29)),  # leap-year clamp
        (date(2027, 1, 15), True, date(2026, 12, 15)),  # crosses a year boundary
    ],
)
def test_submission_target_follows_calendar_days_and_months(first_date, is_big, target):
    assert submission_target(first_date, is_big=is_big, **RULE) == target


@pytest.mark.req("FR-MEM-11", "AC-19")
def test_exactly_seven_days_is_on_time_and_six_days_is_late():
    event = date(2026, 12, 18)
    assert is_late_submission(date(2026, 12, 11), event, is_big=False, **RULE) is False
    assert is_late_submission(date(2026, 12, 12), event, is_big=False, **RULE) is True


@pytest.mark.req("FR-MEM-11", "AC-19")
def test_big_takes_precedence_and_uses_the_calendar_month_boundary():
    event = date(2027, 3, 31)
    assert is_late_submission(date(2027, 2, 28), event, is_big=True, **RULE) is False
    assert is_late_submission(date(2027, 3, 1), event, is_big=True, **RULE) is True
    assert is_late_submission(date(2027, 3, 1), event, is_big=False, **RULE) is False


def test_default_approval_deadline_counts_back_from_the_first_date():
    assert default_approval_deadline(date(2026, 12, 18), 2) == date(2026, 12, 16)

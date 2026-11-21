"""Effective workflow policy lookup and the pure submission-deadline rule (FR-MEM-11, FR-IAM-08)."""

from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from .exceptions import ValidationFailed
from .models import PolicyVersion


def effective_policy(on: date) -> PolicyVersion:
    """Return the policy version in force on a campus-local date."""
    policy = (
        PolicyVersion.objects.filter(effective_from__lte=on)
        .order_by("-effective_from", "-id")
        .first()
    )
    if policy is None:
        raise ValidationFailed(
            "No workflow policy is in force. Ask the DoSA Head to configure one."
        )
    return policy


def submission_target(
    first_event_date: date, *, is_big: bool, standard_lead_days: int, big_event_lead_months: int
) -> date:
    """Latest on-time submission date for an event's first local date.

    Big events use calendar months and take precedence; month-end clamps to the last valid day
    (31 Mar 2027 minus one month is 28 Feb 2027). Other events use calendar days
    (18 Dec minus seven days is 11 Dec).
    """
    if is_big:
        return first_event_date - relativedelta(months=big_event_lead_months)
    return first_event_date - timedelta(days=standard_lead_days)


def is_late_submission(submitted_on: date, first_event_date: date, **rule) -> bool:
    """True when the local submission date falls after the target. Exactly on target is on time.

    A late flag informs reviewers only; it never blocks, approves or rejects (FR-MEM-11).
    """
    return submitted_on > submission_target(first_event_date, **rule)


def default_approval_deadline(first_event_date: date, approval_buffer_days: int) -> date:
    """Approval deadline used until an authorized reviewer changes it (synthetic policy value)."""
    return first_event_date - timedelta(days=approval_buffer_days)

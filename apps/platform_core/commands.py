"""Platform commands: workflow policy versions (FR-IAM-08, UC-05)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from apps.platform_core import audit, clock
from apps.platform_core.access import Action, require
from apps.platform_core.exceptions import ValidationFailed
from apps.platform_core.models import PolicyVersion
from apps.platform_core.protocol import CommandResult, execute


@dataclass(frozen=True)
class PolicyInput:
    """Workflow rule values for a new policy version (FR-IAM-08)."""

    effective_from: date
    standard_lead_days: int
    big_event_lead_months: int
    approval_buffer_days: int
    review_window_days: int
    working_days: tuple[int, ...]
    email_on_submission: bool
    is_synthetic: bool
    note: str = ""


def save_policy_version(actor, data: PolicyInput, *, operation_key: str | None) -> CommandResult:
    """Save a new policy version effective from a date (FR-IAM-08).

    Actor scope: ``settings.manage`` (DoSA Head). Earlier versions stay for audit and for memos
    already in review, which keep their submission-time version. A past effective date is
    rejected so history cannot be rewritten. Invalid values leave the current policy in force.
    """

    def handler() -> CommandResult:
        require(actor, Action.SETTINGS_MANAGE)
        errors: dict[str, list[str]] = {}
        if data.effective_from < clock.local_today():
            errors["effective_from"] = ["The effective date cannot be in the past."]
        if not 1 <= data.standard_lead_days <= 365:
            errors["standard_lead_days"] = ["Enter 1 to 365 days."]
        if not 1 <= data.big_event_lead_months <= 12:
            errors["big_event_lead_months"] = ["Enter 1 to 12 months."]
        if not 0 <= data.approval_buffer_days <= 60:
            errors["approval_buffer_days"] = ["Enter 0 to 60 days."]
        if not 1 <= data.review_window_days <= 60:
            errors["review_window_days"] = ["Enter 1 to 60 days."]
        if not data.working_days or any(d not in range(1, 8) for d in data.working_days):
            errors["working_days"] = ["Choose at least one working day."]
        if errors:
            raise ValidationFailed(field_errors=errors)
        policy = PolicyVersion.objects.create(
            issued_by=actor,
            created_at=clock.now(),
            **{**asdict(data), "working_days": sorted(set(data.working_days))},
        )
        audit.record(
            actor,
            "policy.save",
            policy,
            after={**asdict(data), "working_days": list(data.working_days)},
        )
        return CommandResult("platform_core.policyversion", policy.pk, "saved")

    payload = {**asdict(data), "working_days": list(data.working_days)}
    return execute(
        actor=actor,
        action="policy.save",
        operation_key=operation_key,
        payload=payload,
        handler=handler,
    )

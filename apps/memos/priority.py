"""Explain and, with a reason, reorder the DoSA queue (FR-AIP-01, FR-AIP-03, FR-AIP-05, FR-AIP-06).

The order itself is the approval deadline, then the event start (FR-AIP-02). A missing deadline
is labelled missing. The event date is not used in its place. This explanation does not approve
or reject the memo.
"""

from __future__ import annotations

from apps.platform_core import clock


def explain(version) -> list[str]:
    factors = []
    if version.approval_deadline is None:
        factors.append("Approval deadline is missing. It is not replaced with the event date.")
    else:
        today = clock.local_today()
        factors.append(f"Approval deadline {version.approval_deadline:%d %b %Y}.")
        if version.approval_deadline < today:
            factors.append("Overdue: the approval deadline has passed.")
        else:
            remaining = (version.approval_deadline - today).days
            factors.append(f"{remaining} days remain before the approval deadline.")
    if version.event_starts_at is not None:
        factors.append(f"Event starts {version.event_starts_at:%d %b %Y %H:%M}.")
        if clock.to_local(version.event_starts_at).date() < clock.local_today():
            factors.append("The event start date has passed.")
    factors.append("Queue order is the approval deadline, then the event start.")
    return factors


def ordered_queue(versions):
    """Apply unexpired overrides. A missing override keeps the deadline order."""
    from apps.platform_core import clock

    from .models import QueueOverride

    today = clock.local_today()
    overrides = {
        row.memo_id: row
        for row in QueueOverride.objects.filter(
            expires_on__gte=today, memo_id__in=[v.memo_id for v in versions]
        )
    }
    indexed = list(enumerate(versions))

    def sort_key(item):
        index, version = item
        override = overrides.get(version.memo_id)
        return (override.position, index) if override else (10_000 + index, index)

    return [version for _index, version in sorted(indexed, key=sort_key)]


def set_queue_override(
    actor, memo_id: int, *, position: int, reason: str, expires_on, operation_key
):
    """Record who moved a memo, the previous place, the reason, and when it expires (FR-AIP-05)."""
    from apps.platform_core import audit, clock
    from apps.platform_core.access import Action, can
    from apps.platform_core.exceptions import NotFoundError, PermissionDeniedError, ValidationFailed
    from apps.platform_core.protocol import CommandResult, execute

    from .models import Memo, QueueOverride
    from .selectors import dosa_queue

    def handler():
        if not can(actor, Action.QUEUE_MANAGE):
            raise PermissionDeniedError()
        memo = Memo.objects.filter(pk=memo_id).first()
        if memo is None:
            raise NotFoundError()
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter the reason for the new order."]})
        current = [row.memo_id for row in dosa_queue()]
        prior = current.index(memo.pk) + 1 if memo.pk in current else 0
        row = QueueOverride.objects.create(
            memo=memo,
            actor=actor,
            reason=reason.strip(),
            prior_order=prior,
            position=position,
            expires_on=expires_on,
            created_at=clock.now(),
        )
        audit.record(
            actor,
            "queue.override",
            memo,
            reason=reason.strip(),
            after={"prior": prior, "position": position, "expires": str(expires_on)},
        )
        return CommandResult("memos.queueoverride", row.pk, "recorded")

    return execute(
        actor=actor,
        action="queue.override",
        operation_key=operation_key,
        payload={"memo": memo_id, "position": position, "reason": reason},
        handler=handler,
    )

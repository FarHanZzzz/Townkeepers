"""Budget commands (FR-FIN-04, UC-11). Lock order: Budget row, then BudgetVersion row."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from apps.platform_core import audit, clock
from apps.platform_core.access import Action, can, is_assigned_advisor
from apps.platform_core.exceptions import (
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    StaleRevisionError,
    ValidationFailed,
)
from apps.platform_core.notifications import notify
from apps.platform_core.protocol import CommandResult, execute

from .models import Budget, BudgetLine, BudgetRequestReview, BudgetVersion, Currency

TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class BudgetLineInput:
    """One planned budget line; amounts are Decimal with an explicit currency."""

    description: str
    planned_amount: Decimal
    currency: str = Currency.BDT
    quantity: Decimal | None = None
    unit: str = ""


def _money(value, field: str, errors: dict, *, allow_zero: bool = True) -> Decimal | None:
    try:
        amount = Decimal(str(value)).quantize(TWO_PLACES)
    except (InvalidOperation, ValueError, TypeError):
        errors.setdefault(field, []).append("Enter an amount with up to two decimal places.")
        return None
    if amount < 0 or (amount == 0 and not allow_zero):
        errors.setdefault(field, []).append(
            "Enter a positive amount." if not allow_zero else "Negative amounts are not allowed."
        )
        return None
    return amount


def save_budget_version(
    actor,
    event_id: int,
    *,
    lines: list[BudgetLineInput],
    requested_amount: Decimal | None,
    requested_currency: str,
    purpose: str,
    expected_version_number: int,
    operation_key: str | None,
) -> CommandResult:
    """Save a new immutable budget version for an event (FR-FIN-04).

    Actor scope: ``finance.edit_budget`` for the event's club. ``expected_version_number`` is the
    latest version the editor saw (0 for the first); a concurrent save raises StaleRevisionError
    and never alters an existing version. Changed line descriptions are recorded for reviewers.
    """
    from apps.events.models import Event

    def handler():
        event = Event.objects.select_related("club").filter(pk=event_id).first()
        if (
            event is None
            or event.club_id is None
            or not can(actor, Action.FINANCE_VIEW, event.club)
        ):
            raise NotFoundError()
        if not can(actor, Action.FINANCE_EDIT_BUDGET, event.club):
            raise PermissionDeniedError()
        if event.club.is_archived:
            raise InvalidTransitionError("This club is archived and cannot start new requests.")
        budget, _ = Budget.objects.get_or_create(
            event=event, defaults={"club": event.club, "created_at": clock.now()}
        )
        budget = Budget.objects.select_for_update().get(pk=budget.pk)
        latest = budget.versions.order_by("-number").first()
        latest_number = latest.number if latest else 0
        if expected_version_number != latest_number:
            raise StaleRevisionError(current_state={"latest_version": latest_number})
        errors: dict[str, list[str]] = {}
        clean: list[BudgetLineInput] = []
        if not lines:
            errors["lines"] = ["Add at least one line item."]
        for i, line in enumerate(lines, start=1):
            if not line.description.strip():
                errors.setdefault("lines", []).append(f"Line {i}: enter a description.")
            amount = _money(line.planned_amount, "lines", errors)
            qty = None
            if line.quantity not in (None, ""):
                try:
                    qty = Decimal(str(line.quantity))
                    if qty <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    errors.setdefault("lines", []).append(
                        f"Line {i}: quantity must be greater than zero."
                    )
            if line.currency not in Currency.values:
                errors.setdefault("lines", []).append(f"Line {i}: choose a currency.")
            if amount is not None:
                clean.append(
                    BudgetLineInput(
                        line.description.strip(), amount, line.currency, qty, line.unit.strip()
                    )
                )
        req = None
        if requested_amount not in (None, ""):
            req = _money(requested_amount, "requested_amount", errors, allow_zero=False)
        if requested_currency not in Currency.values:
            errors["requested_currency"] = ["Choose a currency."]
        if req is not None and not purpose.strip():
            errors["purpose"] = ["State the purpose of the requested amount."]
        if errors:
            raise ValidationFailed(field_errors=errors)
        previous = (
            {(ln.description, ln.planned_amount, ln.currency) for ln in latest.lines.all()}
            if latest
            else set()
        )
        current = {(ln.description, ln.planned_amount, ln.currency) for ln in clean}
        changed = sorted({d for d, _, _ in previous ^ current})
        version = BudgetVersion.objects.create(
            budget=budget,
            number=latest_number + 1,
            requested_amount=req,
            requested_currency=requested_currency,
            purpose=purpose.strip(),
            changed_lines=changed,
            created_by=actor,
            created_at=clock.now(),
        )
        BudgetLine.objects.bulk_create(
            [
                BudgetLine(
                    version=version,
                    position=i,
                    description=ln.description,
                    quantity=ln.quantity,
                    unit=ln.unit,
                    planned_amount=ln.planned_amount,
                    currency=ln.currency,
                )
                for i, ln in enumerate(clean, start=1)
            ]
        )
        audit.record(
            actor,
            "budget.save_version",
            version,
            after={
                "number": version.number,
                "requested": str(req) if req else None,
                "currency": requested_currency,
                "changed_lines": changed,
            },
        )
        return CommandResult(
            "finance.budgetversion", version.pk, "saved", {"number": version.number}
        )

    payload = {
        "event": event_id,
        "expected": expected_version_number,
        "req": str(requested_amount),
        "cur": requested_currency,
        "purpose": purpose,
        "lines": [
            [ln.description, str(ln.planned_amount), ln.currency, str(ln.quantity), ln.unit]
            for ln in lines
        ],
    }
    return execute(
        actor=actor,
        action="budget.save_version",
        operation_key=operation_key,
        payload=payload,
        handler=handler,
    )


def review_budget_request(
    actor, version_id: int, *, endorse: bool, reason: str = "", operation_key: str | None
) -> CommandResult:
    """Faculty Advisor endorses or returns a version's requested amount (FR-FIN-04, AC-03).

    Endorsement is a recommendation for the next finance step; it is not an allocation or a
    release. Only the latest version with a requested amount can be reviewed, once.
    """

    def handler():
        try:
            version = (
                BudgetVersion.objects.select_for_update(of=("self",))
                .select_related("budget__event__club")
                .get(pk=version_id)
            )
        except BudgetVersion.DoesNotExist as exc:
            raise NotFoundError() from exc
        club = version.budget.event.club
        if not can(actor, Action.FINANCE_VIEW, club):
            raise NotFoundError()
        if not (
            can(actor, Action.FINANCE_ENDORSE_BUDGET, club) and is_assigned_advisor(actor, club)
        ):
            raise PermissionDeniedError()
        if version.requested_amount is None:
            raise InvalidTransitionError("This budget version has no requested amount to review.")
        if version.budget.versions.filter(number__gt=version.number).exists():
            raise ConflictError("A newer budget version exists. Review the latest version.")
        if BudgetRequestReview.objects.filter(version=version).exists():
            raise ConflictError("This budget request was already reviewed.")
        if not endorse and not reason.strip():
            raise ValidationFailed(
                field_errors={"reason": ["Give feedback when returning a request."]}
            )
        review = BudgetRequestReview.objects.create(
            version=version,
            decision=BudgetRequestReview.Decision.ENDORSED
            if endorse
            else BudgetRequestReview.Decision.RETURNED,
            reviewer=actor,
            reason=reason.strip(),
            decided_at=clock.now(),
        )
        audit.record(
            actor,
            "budget.review_request",
            version,
            after={"decision": review.decision},
            reason=reason,
        )
        notify(
            [version.created_by],
            event_key=f"budget:{version.pk}:review",
            event_type="budget.reviewed",
            object_type="finance.budgetversion",
            object_id=version.pk,
            subject=f"Budget request {review.get_decision_display().lower()}",
            message=(
                f"The requested {version.requested_currency} {version.requested_amount} for "
                f"{version.budget.event.title} was {review.get_decision_display().lower()}."
                + (f" Feedback: {reason}" if reason else "")
            ),
            link=f"/finance/events/{version.budget.event_id}/budget/",
        )
        return CommandResult("finance.budgetversion", version.pk, review.decision)

    return execute(
        actor=actor,
        action="budget.review_request",
        operation_key=operation_key,
        payload={"v": version_id, "endorse": endorse, "reason": reason},
        handler=handler,
    )

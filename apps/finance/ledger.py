"""Allocation, release, expense and adjustment commands (FR-FIN-01, FR-FIN-02, FR-FIN-06, FR-FIN-10)."""

from __future__ import annotations

from decimal import Decimal

from apps.platform_core import audit, clock
from apps.platform_core.access import AccessCategory, Action, can
from apps.platform_core.exceptions import (
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    ValidationFailed,
)
from apps.platform_core.protocol import CommandResult, execute

from .models import Adjustment, Allocation, EventInflow, Expense, FundingPeriod, FundRelease


def _finance_actor(actor, club):
    if actor.access_category in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
        return
    if can(actor, Action.FINANCE_EDIT_BUDGET, club):
        return
    raise PermissionDeniedError()


def open_funding_period(actor, *, label, start_date, end_date, operation_key):
    """Open a reporting period. Amounts from different periods are not added together (FR-FIN-03)."""

    def handler():
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if not label.strip() or end_date < start_date:
            raise ValidationFailed(
                field_errors={"label": ["Enter a label and an end date on or after the start."]}
            )
        if FundingPeriod.objects.filter(label=label.strip()).exists():
            raise ConflictError("A funding period with this label already exists.")
        period = FundingPeriod.objects.create(
            label=label.strip(), start_date=start_date, end_date=end_date
        )
        audit.record(actor, "finance.open_period", period, after={"label": period.label})
        return CommandResult("finance.fundingperiod", period.pk, "opened")

    return execute(
        actor=actor,
        action="finance.open_period",
        operation_key=operation_key,
        payload={"label": label, "start": str(start_date), "end": str(end_date)},
        handler=handler,
    )


def cancel_release(actor, release_id: int, *, reason: str, operation_key):
    """Cancel a scheduled release. A cancelled release cannot later be confirmed (FR-FIN-02)."""

    def handler():
        row = FundRelease.objects.select_for_update().filter(pk=release_id).first()
        if row is None:
            raise NotFoundError()
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if row.status != FundRelease.Status.SCHEDULED:
            raise InvalidTransitionError("Only a scheduled release can be cancelled.")
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter the reason for cancellation."]})
        row.status = FundRelease.Status.CANCELLED
        row.save(update_fields=["status"])
        audit.record(actor, "finance.cancel_release", row, reason=reason.strip())
        return CommandResult("finance.fundrelease", row.pk, "cancelled")

    return execute(
        actor=actor,
        action="finance.cancel_release",
        operation_key=operation_key,
        payload={"release": release_id, "reason": reason},
        handler=handler,
    )


def _resolve_active_period(club, allocated_on=None):
    """Resolve funding period from the club's active term; auto-create if needed."""
    from apps.clubs.models import Term

    active_term = (
        Term.objects.filter(club=club, status=Term.Status.ACTIVE).order_by("-start_date").first()
    )
    if not active_term:
        raise ValidationFailed(
            "This club has no active term. Set an active term before allocating funds.",
            field_errors={"club": ["This club has no active term."]},
        )
    if allocated_on and (allocated_on < active_term.start_date or allocated_on > active_term.end_date):
        raise ValidationFailed(
            "Allocation date must fall within the club's active term dates.",
            field_errors={"allocated_on": ["Date must be within the active term."]},
        )
    label = f"{club.short_code} {active_term.label}".strip()[:40]
    period, _ = FundingPeriod.objects.get_or_create(
        label=label,
        defaults={"start_date": active_term.start_date, "end_date": active_term.end_date},
    )
    # Keep period dates aligned with the term if term changed.
    if period.start_date != active_term.start_date or period.end_date != active_term.end_date:
        period.start_date = active_term.start_date
        period.end_date = active_term.end_date
        period.save(update_fields=["start_date", "end_date"])
    return period


def record_allocation(
    actor, *, club_id, period_id, amount, currency, source, allocated_on, operation_key
):
    """Record funding assigned to a club for one period (FR-FIN-01)."""

    def handler():
        from apps.clubs.models import Club

        club = Club.objects.filter(pk=club_id).first()
        if club is None:
            raise NotFoundError()
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if Decimal(amount) < 0 or not source.strip():
            raise ValidationFailed(
                "Enter a zero or positive amount and a source.",
                field_errors={"amount": ["Enter a zero or positive amount and a source."]},
            )
        if period_id:
            period = FundingPeriod.objects.filter(pk=period_id).first()
            if period is None:
                raise NotFoundError()
        else:
            period = _resolve_active_period(club, allocated_on=allocated_on)
        row = Allocation.objects.create(
            club=club,
            period=period,
            amount=amount,
            currency=currency,
            source=source.strip(),
            allocated_on=allocated_on,
            created_by=actor,
            created_at=clock.now(),
        )
        audit.record(
            actor, "finance.allocate", row, after={"amount": str(amount), "currency": currency}
        )
        return CommandResult("finance.allocation", row.pk, "recorded")

    return execute(
        actor=actor,
        action="finance.allocate",
        operation_key=operation_key,
        payload={"club": club_id, "period": period_id, "amount": str(amount)},
        handler=handler,
    )


def schedule_release(actor, *, club_id, period_id, amount, currency, operation_key):
    def handler():
        from apps.clubs.models import Club

        club = Club.objects.filter(pk=club_id).first()
        period = FundingPeriod.objects.filter(pk=period_id).first()
        if club is None or period is None:
            raise NotFoundError()
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if Decimal(amount) <= 0:
            raise ValidationFailed(field_errors={"amount": ["Enter a positive scheduled amount."]})
        row = FundRelease.objects.create(
            club=club,
            period=period,
            scheduled_amount=amount,
            currency=currency,
            created_by=actor,
            created_at=clock.now(),
        )
        audit.record(actor, "finance.schedule_release", row, after={"amount": str(amount)})
        return CommandResult("finance.fundrelease", row.pk, "scheduled")

    return execute(
        actor=actor,
        action="finance.schedule_release",
        operation_key=operation_key,
        payload={"club": club_id, "amount": str(amount)},
        handler=handler,
    )


def confirm_release(actor, release_id: int, *, amount, reference: str, operation_key):
    """Mark a scheduled release as released. A cancelled release cannot be released (FR-FIN-02)."""

    def handler():
        row = FundRelease.objects.select_for_update().filter(pk=release_id).first()
        if row is None:
            raise NotFoundError()
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if row.status == FundRelease.Status.CANCELLED:
            raise InvalidTransitionError("A cancelled release cannot be marked released.")
        if row.status == FundRelease.Status.RELEASED:
            raise InvalidTransitionError("This release is already confirmed.")
        if Decimal(amount) <= 0 or not reference.strip():
            raise ValidationFailed(
                field_errors={"reference": ["Enter the released amount and a reference."]}
            )
        row.released_amount = amount
        row.reference = reference.strip()
        row.status = FundRelease.Status.RELEASED
        row.save(update_fields=["released_amount", "reference", "status"])
        audit.record(actor, "finance.confirm_release", row, after={"amount": str(amount)})
        return CommandResult("finance.fundrelease", row.pk, "released")

    return execute(
        actor=actor,
        action="finance.confirm_release",
        operation_key=operation_key,
        payload={"release": release_id, "amount": str(amount)},
        handler=handler,
    )


def attribute_release(actor, release_id: int, *, event_id: int, amount, operation_key):
    def handler():
        from apps.events.models import Event

        row = FundRelease.objects.filter(pk=release_id).first()
        event = Event.objects.filter(pk=event_id).first()
        if row is None or event is None:
            raise NotFoundError()
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if row.status != FundRelease.Status.RELEASED:
            raise InvalidTransitionError("Only a confirmed release can be attributed to an event.")
        if Decimal(amount) <= 0 or Decimal(amount) > row.released_amount:
            raise ValidationFailed(
                field_errors={"amount": ["Attribute a positive amount within the release."]}
            )
        inflow = EventInflow.objects.create(
            release=row, event=event, amount=amount, currency=row.currency
        )
        audit.record(
            actor, "finance.attribute", inflow, after={"event": event.pk, "amount": str(amount)}
        )
        return CommandResult("finance.eventinflow", inflow.pk, "attributed")

    return execute(
        actor=actor,
        action="finance.attribute",
        operation_key=operation_key,
        payload={"release": release_id, "event": event_id, "amount": str(amount)},
        handler=handler,
    )


def submit_expense(
    actor,
    *,
    club_id,
    event_id,
    amount,
    currency,
    description,
    incurred_on,
    evidence_note,
    operation_key,
):
    def handler():
        from apps.clubs.models import Club
        from apps.events.models import Event

        club = Club.objects.filter(pk=club_id).first()
        event = Event.objects.filter(pk=event_id).first() if event_id else None
        if club is None:
            raise NotFoundError()
        _finance_actor(actor, club)
        if Decimal(amount) <= 0 or not description.strip() or not evidence_note.strip():
            raise ValidationFailed(
                field_errors={
                    "evidence": ["Enter a positive amount, a description, and the receipt note."]
                }
            )
        row = Expense.objects.create(
            club=club,
            event=event,
            amount=amount,
            currency=currency,
            description=description.strip(),
            incurred_on=incurred_on,
            evidence_note=evidence_note.strip(),
            status=Expense.Status.SUBMITTED,
            created_by=actor,
            created_at=clock.now(),
        )
        audit.record(actor, "finance.submit_expense", row)
        return CommandResult("finance.expense", row.pk, "submitted")

    return execute(
        actor=actor,
        action="finance.submit_expense",
        operation_key=operation_key,
        payload={"club": club_id, "amount": str(amount), "evidence": evidence_note},
        handler=handler,
    )


def verify_expense(actor, expense_id: int, *, operation_key):
    """A person verifies the expense. An OCR suggestion never verifies it by itself (FR-FIN-10)."""

    def handler():
        row = Expense.objects.select_for_update().filter(pk=expense_id).first()
        if row is None:
            raise NotFoundError()
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if row.status != Expense.Status.SUBMITTED:
            raise InvalidTransitionError("Only a submitted expense can be verified.")
        if not row.evidence_note:
            raise InvalidTransitionError("A receipt is required before verification.")
        row.status = Expense.Status.VERIFIED
        row.save(update_fields=["status"])
        audit.record(actor, "finance.verify_expense", row)
        return CommandResult("finance.expense", row.pk, "verified")

    return execute(
        actor=actor,
        action="finance.verify_expense",
        operation_key=operation_key,
        payload={"expense": expense_id},
        handler=handler,
    )


def attach_receipt(actor, expense_id: int, *, data: bytes, filename: str, operation_key):
    """Store the original bill privately. The claim stays unverified (FR-FIN-07)."""

    def handler():
        from apps.platform_core import files

        row = Expense.objects.select_for_update().filter(pk=expense_id).first()
        if row is None or not can(actor, Action.FINANCE_EDIT_BUDGET, row.club):
            raise NotFoundError()
        stored = files.store_bytes(
            data,
            original_name=filename,
            uploaded_by=actor,
            purpose="expense evidence",
            owner_type="expense_evidence",
            owner_id=row.pk,
            club=row.club,
        )
        row.evidence_key = str(stored.key)
        if not row.evidence_note:
            row.evidence_note = filename
        row.save(update_fields=["evidence_key", "evidence_note"])
        audit.record(actor, "finance.attach_receipt", row, after={"sha256": stored.sha256})
        return CommandResult("finance.expense", row.pk, "attached")

    return execute(
        actor=actor,
        action="finance.attach_receipt",
        operation_key=operation_key,
        payload={"expense": expense_id, "filename": filename},
        handler=handler,
    )


def decide_expense(actor, expense_id: int, *, decision: str, reason: str, operation_key):
    """Verify, return, or reject a submitted expense (FR-FIN-10)."""

    def handler():
        row = Expense.objects.select_for_update().filter(pk=expense_id).first()
        if row is None:
            raise NotFoundError()
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if row.status != Expense.Status.SUBMITTED:
            raise InvalidTransitionError("Only a submitted expense can be reviewed.")
        if decision == "verify":
            if not row.evidence_note and not row.evidence_key:
                raise InvalidTransitionError("A receipt is required before verification.")
            row.status = Expense.Status.VERIFIED
        elif decision in {"return", "reject"}:
            if not reason.strip():
                raise ValidationFailed(field_errors={"reason": ["Enter the reason."]})
            row.status = (
                Expense.Status.RETURNED if decision == "return" else Expense.Status.REJECTED
            )
        else:
            raise ValidationFailed(field_errors={"decision": ["Choose verify, return, or reject."]})
        row.save(update_fields=["status"])
        audit.record(actor, f"finance.expense_{decision}", row, reason=reason.strip())
        return CommandResult("finance.expense", row.pk, row.status)

    return execute(
        actor=actor,
        action="finance.decide_expense",
        operation_key=operation_key,
        payload={"expense": expense_id, "decision": decision},
        handler=handler,
    )


def record_conversion(actor, *, from_currency, to_currency, rate, recorded_on, note, operation_key):
    """Record the rate required before two currencies can be combined (FR-FIN-03)."""

    def handler():
        from decimal import Decimal

        from .models import ConversionRecord

        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if from_currency == to_currency or Decimal(rate) <= 0 or not note.strip():
            raise ValidationFailed(
                field_errors={
                    "rate": ["Enter two different currencies, a positive rate, and a note."]
                }
            )
        row = ConversionRecord.objects.create(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            recorded_on=recorded_on,
            note=note.strip(),
            created_by=actor,
            created_at=clock.now(),
        )
        audit.record(actor, "finance.conversion", row, after={"rate": str(rate)})
        return CommandResult("finance.conversionrecord", row.pk, "recorded")

    return execute(
        actor=actor,
        action="finance.conversion",
        operation_key=operation_key,
        payload={"from": from_currency, "to": to_currency, "rate": str(rate)},
        handler=handler,
    )


def note_extraction(actor, expense_id: int, *, amount, operation_key):
    """Store an unverified reading of the receipt (FR-FIN-08). It does not change the claimed amount."""

    def handler():
        row = Expense.objects.select_for_update().filter(pk=expense_id).first()
        if row is None:
            raise NotFoundError()
        if actor.access_category not in {
            AccessCategory.DOSA_HEAD,
            AccessCategory.SYSTEM_ADMIN,
        } and not can(actor, Action.FINANCE_EDIT_BUDGET, row.club):
            raise PermissionDeniedError()
        row.extraction_amount = amount
        row.extraction_state = "unverified"
        row.save(update_fields=["extraction_amount", "extraction_state"])
        audit.record(actor, "finance.ocr_suggestion", row, after={"unverified": str(amount)})
        return CommandResult("finance.expense", row.pk, "suggested")

    return execute(
        actor=actor,
        action="finance.ocr_suggestion",
        operation_key=operation_key,
        payload={"expense": expense_id, "amount": str(amount)},
        handler=handler,
    )


def apply_adjustment(
    actor,
    *,
    club_id,
    event_id,
    direction,
    source_type,
    source_id,
    amount,
    currency,
    reason,
    operation_key,
):
    """Apply one linked correction. The same operation key does not apply it twice."""

    def handler():
        from apps.clubs.models import Club

        if Adjustment.objects.filter(operation_key=operation_key).exists():
            existing = Adjustment.objects.get(operation_key=operation_key)
            return CommandResult("finance.adjustment", existing.pk, "replayed", replayed=True)
        club = Club.objects.filter(pk=club_id).first()
        if club is None:
            raise NotFoundError()
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if Decimal(amount) <= 0 or not reason.strip():
            raise ValidationFailed(
                field_errors={"reason": ["Enter a positive adjustment and a reason."]}
            )
        row = Adjustment.objects.create(
            club=club,
            event_id=event_id,
            direction=direction,
            source_type=source_type,
            source_id=source_id,
            amount=amount,
            currency=currency,
            reason=reason.strip(),
            operation_key=operation_key or "",
            created_by=actor,
            created_at=clock.now(),
        )
        audit.record(actor, "finance.adjust", row, reason=reason.strip())
        return CommandResult("finance.adjustment", row.pk, "applied")

    if not operation_key:
        raise ValidationFailed(
            field_errors={"operation_key": ["An adjustment needs an operation key."]}
        )
    try:
        return execute(
            actor=actor,
            action="finance.adjust",
            operation_key=operation_key,
            payload={"source": source_id, "amount": str(amount), "direction": direction},
            handler=handler,
        )
    except ConflictError:
        existing = Adjustment.objects.filter(operation_key=operation_key).first()
        if existing is None:
            raise
        return CommandResult("finance.adjustment", existing.pk, "replayed", replayed=True)

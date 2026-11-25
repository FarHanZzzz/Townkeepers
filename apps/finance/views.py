"""Event budget page: versions, line items and the Advisor's review (FR-FIN-04, UC-11)."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render

from apps.events.selectors import get_event
from apps.platform_core.access import Action, can, is_assigned_advisor
from apps.platform_core.exceptions import DomainError, NotFoundError, PermissionDeniedError
from apps.platform_core.forms import apply_domain_error

from . import commands
from .forms import BudgetHeaderForm, BudgetLineFormSet, BudgetReviewForm
from .models import BudgetVersion


def event_budget(request, event_id):
    event = get_event(request.user, event_id)
    if event.club_id is None or not can(request.user, Action.FINANCE_VIEW, event.club):
        raise NotFoundError()
    budget = getattr(event, "budget", None) if hasattr(event, "budget") else None
    versions = list(budget.versions.prefetch_related("lines").order_by("-number")) if budget else []
    latest = versions[0] if versions else None
    can_edit = (
        can(request.user, Action.FINANCE_EDIT_BUDGET, event.club) and not event.club.is_archived
    )
    if request.method == "POST" and not can_edit:
        raise PermissionDeniedError()
    header = BudgetHeaderForm(
        request.POST or None,
        initial={
            "expected_version_number": latest.number if latest else 0,
            "requested_amount": latest.requested_amount if latest else None,
            "requested_currency": latest.requested_currency if latest else "BDT",
            "purpose": latest.purpose if latest else "",
        },
        prefix="h",
    )
    initial_lines = (
        [
            {
                "description": ln.description,
                "quantity": ln.quantity,
                "unit": ln.unit,
                "planned_amount": ln.planned_amount,
                "currency": ln.currency,
            }
            for ln in latest.lines.all()
        ]
        if latest
        else []
    )
    lines = BudgetLineFormSet(request.POST or None, initial=initial_lines, prefix="l")
    if request.method == "POST" and can_edit and header.is_valid() and lines.is_valid():
        items = [
            commands.BudgetLineInput(
                description=f.cleaned_data.get("description", ""),
                planned_amount=f.cleaned_data.get("planned_amount"),
                currency=f.cleaned_data.get("currency", "BDT"),
                quantity=f.cleaned_data.get("quantity"),
                unit=f.cleaned_data.get("unit", ""),
            )
            for f in lines
            if f.cleaned_data.get("description") or f.cleaned_data.get("planned_amount") is not None
        ]
        cd = header.cleaned_data
        try:
            result = commands.save_budget_version(
                request.user,
                event.pk,
                lines=items,
                requested_amount=cd["requested_amount"],
                requested_currency=cd["requested_currency"],
                purpose=cd["purpose"],
                expected_version_number=cd["expected_version_number"],
                operation_key=cd["operation_key"],
            )
            messages.success(
                request, f"Budget version {result.data['number']} saved. Earlier versions are kept."
            )
            return redirect("finance:event_budget", event_id=event.pk)
        except DomainError as exc:
            apply_domain_error(header, exc)
    review_form = None
    if (
        latest
        and latest.requested_amount
        and not hasattr(latest, "review")
        and is_assigned_advisor(request.user, event.club)
        and can(request.user, Action.FINANCE_ENDORSE_BUDGET, event.club)
    ):
        review_form = BudgetReviewForm()
    return render(
        request,
        "finance/event_budget.html",
        {
            "event": event,
            "versions": versions,
            "latest": latest,
            "header": header,
            "lines": lines,
            "can_edit": can_edit,
            "review_form": review_form,
        },
    )


def review_budget(request, version_id):
    version = BudgetVersion.objects.select_related("budget__event").filter(pk=version_id).first()
    if version is None or request.method != "POST":
        raise NotFoundError()
    get_event(request.user, version.budget.event_id)
    form = BudgetReviewForm(request.POST)
    if form.is_valid():
        try:
            commands.review_budget_request(
                request.user,
                version.pk,
                endorse=form.cleaned_data["decision"] == "endorse",
                reason=form.cleaned_data["reason"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(request, "Budget request review recorded.")
        except DomainError as exc:
            messages.error(
                request, " ".join([exc.message, *[m for v in exc.field_errors.values() for m in v]])
            )
    else:
        messages.error(request, "Choose endorse or return.")
    return redirect("finance:event_budget", event_id=version.budget.event_id)


def overview(request):
    """Club funding for the viewer's clubs (FR-FIN-03)."""
    from apps.clubs.selectors import visible_clubs
    from apps.events.models import Event
    from apps.platform_core.access import AccessCategory

    from .calculations import club_balance
    from .models import Expense, FundingPeriod, FundRelease

    if not can(request.user, Action.FINANCE_VIEW):
        from apps.platform_core.exceptions import PermissionDeniedError

        raise PermissionDeniedError()
    rows = []
    for club in visible_clubs(request.user):
        releases = [
            row.released_amount
            for row in club.releases.filter(status="released")
            if row.released_amount is not None
        ]
        verified_amounts = []
        for expense in club.expenses.filter(status="verified"):
            reduction = sum(
                item.amount
                for item in club.adjustments.filter(
                    direction="reduce_expense", source_id=expense.pk
                )
            )
            verified_amounts.append(expense.amount - reduction)
        rows.append({"club": club, "balance": club_balance(releases, verified_amounts)})
    return render(
        request,
        "finance/overview.html",
        {
            "rows": rows,
            "periods": FundingPeriod.objects.all(),
            "releases": FundRelease.objects.filter(club__in=visible_clubs(request.user)).order_by(
                "-id"
            )[:30],
            "club_events": Event.objects.filter(club__in=visible_clubs(request.user)).order_by(
                "title"
            )[:100],
            "expenses": Expense.objects.filter(club__in=visible_clubs(request.user)).order_by(
                "-id"
            )[:30],
            "can_record": request.user.access_category
            in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN},
        },
    )


def record(request):
    """DoSA posts a period, allocation, release, attribution, or conversion (FR-FIN-01 to FR-FIN-03)."""
    from datetime import datetime
    from decimal import Decimal

    from . import ledger

    action = request.POST.get("action", "")
    key = request.POST.get("operation_key")
    try:
        if action == "period":
            ledger.open_funding_period(
                request.user,
                label=request.POST.get("label", ""),
                start_date=datetime.strptime(request.POST["start_date"], "%Y-%m-%d").date(),
                end_date=datetime.strptime(request.POST["end_date"], "%Y-%m-%d").date(),
                operation_key=key,
            )
        elif action == "allocation":
            ledger.record_allocation(
                request.user,
                club_id=int(request.POST["club"]),
                period_id=int(request.POST["period"]),
                amount=Decimal(request.POST["amount"]),
                currency=request.POST.get("currency") or "BDT",
                source=request.POST.get("source", ""),
                allocated_on=datetime.strptime(request.POST["allocated_on"], "%Y-%m-%d").date(),
                operation_key=key,
            )
        elif action == "schedule":
            ledger.schedule_release(
                request.user,
                club_id=int(request.POST["club"]),
                period_id=int(request.POST["period"]),
                amount=Decimal(request.POST["amount"]),
                currency=request.POST.get("currency") or "BDT",
                operation_key=key,
            )
        elif action == "confirm":
            ledger.confirm_release(
                request.user,
                int(request.POST["release"]),
                amount=Decimal(request.POST["amount"]),
                reference=request.POST.get("reference", ""),
                operation_key=key,
            )
        elif action == "cancel":
            ledger.cancel_release(
                request.user,
                int(request.POST["release"]),
                reason=request.POST.get("reason", ""),
                operation_key=key,
            )
        elif action == "attribute":
            ledger.attribute_release(
                request.user,
                int(request.POST["release"]),
                event_id=int(request.POST["event"]),
                amount=Decimal(request.POST["amount"]),
                operation_key=key,
            )
        elif action == "conversion":
            ledger.record_conversion(
                request.user,
                from_currency=request.POST.get("from_currency", ""),
                to_currency=request.POST.get("to_currency", ""),
                rate=Decimal(request.POST["rate"]),
                recorded_on=datetime.strptime(request.POST["recorded_on"], "%Y-%m-%d").date(),
                note=request.POST.get("note", ""),
                operation_key=key,
            )
        elif action == "expense":
            ledger.submit_expense(
                request.user,
                club_id=int(request.POST["club"]),
                event_id=int(request.POST["event"]) if request.POST.get("event") else None,
                amount=Decimal(request.POST["amount"]),
                currency=request.POST.get("currency") or "BDT",
                description=request.POST.get("description", ""),
                incurred_on=datetime.strptime(request.POST["incurred_on"], "%Y-%m-%d").date(),
                evidence_note=request.POST.get("evidence_note", ""),
                operation_key=key,
            )
        elif action == "adjustment":
            ledger.apply_adjustment(
                request.user,
                club_id=int(request.POST["club"]),
                event_id=int(request.POST["event"]) if request.POST.get("event") else None,
                direction=request.POST.get("direction", ""),
                source_type=request.POST.get("source_type", "expense"),
                source_id=int(request.POST["source_id"]),
                amount=Decimal(request.POST["amount"]),
                currency=request.POST.get("currency") or "BDT",
                reason=request.POST.get("reason", ""),
                operation_key=key,
            )
        else:
            messages.error(request, "Choose a finance action.")
            return redirect("finance:overview")
        messages.success(request, "Finance record saved.")
    except DomainError as exc:
        messages.error(request, exc.message)
    except (KeyError, ValueError):
        messages.error(request, "Check the dates and amounts.")
    return redirect("finance:overview")


def _note_unverified_reading(request, expense_id: int, data: bytes) -> None:
    """Store a fake reading only when it returns an amount. It never verifies the expense."""
    import hashlib

    from assistance.contracts import OcrRequest
    from assistance.providers.fake import FakeProvider

    from . import ledger

    reading = FakeProvider().extract(
        OcrRequest(
            job_id=f"expense-{expense_id}",
            content_type="application/pdf",
            source_sha256=hashlib.sha256(data).hexdigest(),
            content_base64="cGRm",
        ),
        data,
    )
    amount = reading["fields"]["amount"]["value"]
    if not amount:
        return
    ledger.note_extraction(
        request.user,
        expense_id,
        amount=amount,
        operation_key=f"read-{expense_id}-{hashlib.sha256(data).hexdigest()[:12]}",
    )


def attach_receipt(request, expense_id: int):
    from . import ledger

    upload = request.FILES.get("receipt")
    if request.method == "POST" and upload is not None:
        try:
            data = upload.read()
            ledger.attach_receipt(
                request.user,
                expense_id,
                data=data,
                filename=upload.name,
                operation_key=request.POST.get("operation_key"),
            )
            _note_unverified_reading(request, expense_id, data)
            messages.success(
                request, "Receipt stored. It is not verified until a reviewer checks it."
            )
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("finance:overview")


def decide_expense(request, expense_id: int):
    from . import ledger

    if request.method == "POST":
        try:
            ledger.decide_expense(
                request.user,
                expense_id,
                decision=request.POST.get("decision", ""),
                reason=request.POST.get("reason", ""),
                operation_key=request.POST.get("operation_key"),
            )
            messages.success(request, "Expense review recorded.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("finance:overview")

"""Availability, calendar, publish, completion and outcome screens."""

from __future__ import annotations

from datetime import datetime

from django.contrib import messages
from django.shortcuts import redirect, render

from apps.platform_core.access import AccessCategory, Action, require
from apps.platform_core.exceptions import DomainError, PermissionDeniedError

from . import booking, suggestions
from .models import BookingRequest, Venue
from .selectors import get_event


def availability_search(request):
    require(request.user, Action.EVENTS_VIEW)
    day = request.GET.get("date")
    start = request.GET.get("start") or "18:00"
    end = request.GET.get("end") or "21:00"
    capacity = request.GET.get("capacity")
    intended = request.GET.get("use") or ""
    rows = []
    if day:
        on = datetime.strptime(day, "%Y-%m-%d").date()
        start_t = datetime.strptime(start, "%H:%M").time()
        end_t = datetime.strptime(end, "%H:%M").time()
        venues = Venue.objects.filter(is_active=True).order_by("name")
        if capacity and capacity.isdigit():
            venues = venues.filter(capacity__gte=int(capacity))
        if intended in {Venue.Kind.CLASSROOM, Venue.Kind.LARGE_HALL}:
            venues = venues.filter(kind=intended)
        for venue in venues:
            rows.append({"venue": venue, "label": booking.availability(venue, on, start_t, end_t)})
    return render(
        request,
        "events/availability.html",
        {
            "rows": rows,
            "date": day,
            "start": start,
            "end": end,
            "capacity": capacity or "",
            "intended": intended,
            "venue_kinds": Venue.Kind.choices,
        },
    )


def event_publish(request, pk):
    from apps.publishing.commands import publish_notice, withdraw_notice

    event = get_event(request.user, pk)
    if request.method == "POST":
        try:
            if request.POST.get("action") == "withdraw":
                withdraw_notice(
                    request.user, event.pk, operation_key=request.POST.get("operation_key")
                )
                messages.success(request, "Notice withdrawn.")
            else:
                publish_notice(
                    request.user,
                    event.pk,
                    destination=request.POST.get("destination") or "internal",
                    operation_key=request.POST.get("operation_key"),
                )
                messages.success(request, "Publication recorded.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("events:detail", pk=event.pk)


def event_preview(request, pk):
    event = get_event(request.user, pk)
    confirmed = (
        event.bookings.filter(status=BookingRequest.Status.CONFIRMED)
        .select_related("venue")
        .first()
    )
    return render(
        request,
        "events/preview.html",
        {"event": event, "venue": confirmed.venue.name if confirmed else "Not confirmed"},
    )


def booking_move(request, booking_id: int):
    """Move a confirmed booking. A taken slot leaves the original reservation (FR-EVT-09)."""
    from datetime import datetime

    from .models import BookingRequest

    row = (
        BookingRequest.objects.select_related("event")
        .filter(pk=booking_id, status=BookingRequest.Status.CONFIRMED)
        .first()
    )
    if row is None:
        from django.http import Http404

        raise Http404
    get_event(request.user, row.event_id)
    if request.method == "POST":
        try:
            booking.reschedule_booking(
                request.user,
                row.pk,
                venue_id=int(request.POST["venue"]),
                data={
                    "first_date": datetime.strptime(request.POST["first_date"], "%Y-%m-%d").date(),
                    "last_date": datetime.strptime(request.POST["last_date"], "%Y-%m-%d").date(),
                    "start_time": datetime.strptime(request.POST["start_time"], "%H:%M").time(),
                    "end_time": datetime.strptime(request.POST["end_time"], "%H:%M").time(),
                    "setup_minutes": int(request.POST.get("setup_minutes") or 0),
                    "cleanup_minutes": int(request.POST.get("cleanup_minutes") or 0),
                    "headcount": int(request.POST["headcount"]),
                    "filer_designation": request.POST.get("filer_designation")
                    or request.user.designation,
                    "justification": request.POST.get("justification", ""),
                },
                expected_revision=int(request.POST["revision"]),
                operation_key=request.POST.get("operation_key"),
            )
            messages.success(request, "Booking moved.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("events:detail", pk=row.event_id)


def event_complete(request, pk):
    event = get_event(request.user, pk)
    if request.method == "POST":
        try:
            booking.complete_event(
                request.user, event.pk, operation_key=request.POST.get("operation_key")
            )
            messages.success(request, "Event marked completed.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("events:detail", pk=event.pk)


def event_outcome(request, pk):
    event = get_event(request.user, pk)
    if request.method == "POST":
        attendance = request.POST.get("attendance")
        try:
            booking.record_outcome(
                request.user,
                event.pk,
                attendance=int(attendance) if attendance else None,
                note=request.POST.get("note", ""),
                reach=request.POST.get("reach") or "unknown",
                successful=request.POST.get("successful") == "yes",
                operation_key=request.POST.get("operation_key"),
            )
            messages.success(request, "Attendance and outcome recorded.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("events:detail", pk=event.pk)


def slot_suggestions(request):
    require(request.user, Action.EVENTS_VIEW)
    rows = []
    day = request.GET.get("date")
    if day:
        rows = suggestions.suggest_slots(
            day=datetime.strptime(day, "%Y-%m-%d").date(),
            start=datetime.strptime(request.GET.get("start") or "18:00", "%H:%M").time(),
            duration_minutes=int(request.GET.get("duration") or 60),
            headcount=int(request.GET.get("headcount") or 40),
        )
    return render(request, "events/suggestions.html", {"rows": rows, "date": day or ""})


def venue_restrict(request):
    require(request.user, Action.EVENTS_VIEW)
    if request.user.access_category != AccessCategory.DOSA_HEAD:
        raise PermissionDeniedError()
    if request.method == "POST":
        try:
            from datetime import date as _date

            effective_from = request.POST.get("effective_from")
            effective_until = request.POST.get("effective_until")
            booking.add_restriction(
                request.user,
                venue_id=int(request.POST["venue"]) if request.POST.get("venue") else None,
                weekday=int(request.POST["weekday"]) if request.POST.get("weekday") else None,
                local_start=datetime.strptime(request.POST["local_start"], "%H:%M").time(),
                local_end=datetime.strptime(request.POST["local_end"], "%H:%M").time(),
                reason=request.POST.get("reason", ""),
                operation_key=request.POST.get("operation_key"),
                effective_from=_date.fromisoformat(effective_from) if effective_from else None,
                effective_until=_date.fromisoformat(effective_until) if effective_until else None,
            )
            messages.success(request, "Restricted hours recorded.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("events:venues")

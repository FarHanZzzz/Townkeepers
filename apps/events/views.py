"""Event views for the draft path and separate status display (FR-EVT-01, FR-EVT-02, FR-EVT-12)."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render

from apps.clubs.selectors import visible_clubs
from apps.platform_core import clock
from apps.platform_core.access import AccessCategory, Action, can, effective_actions, require
from apps.platform_core.exceptions import DomainError, PermissionDeniedError
from apps.platform_core.forms import apply_domain_error

from . import commands, selectors
from .forms import EventForm
from .models import Event, Venue

FIELDS = (
    "title",
    "event_type",
    "is_big",
    "description",
    "contact",
    "first_date",
    "last_date",
    "start_time",
    "end_time",
    "proposed_venue",
    "expected_headcount",
)


def _owners(user):
    owners = [
        (str(c.pk), c.name) for c in visible_clubs(user, Action.EVENTS_EDIT).filter(status="active")
    ]
    if can(user, Action.EVENTS_CREATE_CENTRAL):
        owners.insert(0, ("central", "DoSA (central event)"))
    return owners


def event_list(request):
    if Action.EVENTS_VIEW not in effective_actions(request.user):
        require(request.user, Action.EVENTS_VIEW)
    events = selectors.visible_events(request.user)
    status = request.GET.get("status", "")
    club = request.GET.get("club", "")
    if status in Event.Status.values:
        events = events.filter(status=status)
    if club.isdigit():
        events = events.filter(club_id=int(club))
    return render(
        request,
        "events/event_list.html",
        {
            "events": events[:300],
            "status": status,
            "club": club,
            "statuses": Event.Status.choices,
            "clubs": visible_clubs(request.user, Action.EVENTS_VIEW),
            "can_create": bool(_owners(request.user)),
        },
    )


def _input(cd) -> commands.EventInput:
    return commands.EventInput(**{f: cd[f] for f in FIELDS})


def event_new(request):
    owners = _owners(request.user)
    if not owners:
        require(request.user, Action.EVENTS_EDIT)
    form = EventForm(request.POST or None, owners=owners)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        try:
            result = commands.create_event(
                request.user,
                club_id=None if cd["owner"] == "central" else int(cd["owner"]),
                data=_input(cd),
                operation_key=cd["operation_key"],
            )
            messages.success(
                request,
                "Event saved as a draft. Add a budget or start the event-permission memo next.",
            )
            return redirect("events:detail", pk=result.object_id)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(request, "events/event_form.html", {"form": form, "title": "Create an event"})


def event_edit(request, pk):
    event = selectors.get_event(request.user, pk)
    initial = {f: getattr(event, f) for f in FIELDS}
    initial["expected_revision"] = event.revision
    form = EventForm(request.POST or None, initial=initial, editing=True)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        try:
            commands.save_event_draft(
                request.user,
                event.pk,
                data=_input(cd),
                expected_revision=cd["expected_revision"] or 0,
                operation_key=cd["operation_key"],
            )
            messages.success(request, "Event draft saved.")
            return redirect("events:detail", pk=event.pk)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "events/event_form.html",
        {"form": form, "title": f"Edit draft: {event.title}", "event": event},
    )


def event_detail(request, pk):
    event = selectors.get_event(request.user, pk)
    memos = event.memos.select_related("current_version").order_by("created_at")
    original = next((m for m in memos if m.kind == "original" and m.status != "withdrawn"), None)
    budget = getattr(event, "budget", None) if hasattr(event, "budget") else None
    outstanding = []
    if original is None:
        outstanding.append("Start the event-permission memo.")
    elif original.status != "approved":
        outstanding.append(f"Event-permission memo: {original.get_status_display()}.")
    bookings = event.bookings.select_related("venue")
    if event.club_id and not bookings.filter(status="confirmed").exists():
        outstanding.append("Venue booking is still required before the event can be approved.")
    return render(
        request,
        "events/event_detail.html",
        {
            "event": event,
            "bookings": bookings,
            "venues": Venue.objects.filter(is_active=True).order_by("name"),
            "memos": memos,
            "original": original,
            "budget": budget,
            "latest_budget": budget.latest if budget else None,
            "editable": selectors.is_draft_editable(event)
            and (
                can(request.user, Action.EVENTS_EDIT, event.club)
                if event.club_id
                else can(request.user, Action.EVENTS_CREATE_CENTRAL)
            ),
            "can_budget": event.club_id and can(request.user, Action.FINANCE_VIEW, event.club),
            "can_memo": event.club_id
            and can(request.user, Action.MEMOS_AUTHOR, event.club)
            and original is None,
            "outstanding": outstanding,
        },
    )


def venue_list(request):
    if request.user.access_category != AccessCategory.DOSA_HEAD:
        raise PermissionDeniedError()
    return render(
        request,
        "events/venue_list.html",
        {
            "venues": Venue.objects.order_by("name"),
            "can_manage": request.user.access_category
            in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN},
            "can_restrict": request.user.access_category == AccessCategory.DOSA_HEAD,
        },
    )


def _venue_form_data(request):
    from datetime import datetime

    return {
        "name": request.POST.get("name", "").strip(),
        "location": request.POST.get("location", "").strip(),
        "capacity": int(request.POST.get("capacity") or 0),
        "kind": request.POST.get("kind") or Venue.Kind.CLASSROOM,
        "facilities": request.POST.get("facilities", "").strip(),
        "opens_at": datetime.strptime(request.POST.get("opens_at") or "08:00", "%H:%M").time(),
        "closes_at": datetime.strptime(request.POST.get("closes_at") or "22:00", "%H:%M").time(),
        "is_active": request.POST.get("is_active") == "on",
        "is_synthetic": request.POST.get("is_synthetic") == "on",
    }


def venue_new(request):
    if request.user.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
        require(request.user, Action.EVENTS_CREATE_CENTRAL)
    if request.method == "POST":
        try:
            data = _venue_form_data(request)
            if not data["name"] or data["capacity"] < 1 or data["opens_at"] >= data["closes_at"]:
                raise ValueError("invalid")
            venue = Venue.objects.create(created_at=clock.now(), revision=1, **data)
            from apps.platform_core import audit

            audit.record(request.user, "venue.create", venue, after={"name": venue.name})
            messages.success(request, "Venue added.")
            return redirect("events:venues")
        except (ValueError, KeyError):
            messages.error(request, "Enter a name, capacity, and valid opening hours.")
    return render(request, "events/venue_form.html", {"title": "Add a venue", "venue": None})


def venue_edit(request, pk):
    if request.user.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
        require(request.user, Action.EVENTS_CREATE_CENTRAL)
    venue = Venue.objects.filter(pk=pk).first()
    if venue is None:
        from django.http import Http404

        raise Http404
    if request.method == "POST":
        try:
            data = _venue_form_data(request)
            if not data["name"] or data["capacity"] < 1 or data["opens_at"] >= data["closes_at"]:
                raise ValueError("invalid")
            for field, value in data.items():
                setattr(venue, field, value)
            venue.revision += 1
            venue.save()
            from apps.platform_core import audit

            audit.record(request.user, "venue.update", venue, after={"name": venue.name})
            messages.success(request, "Venue updated.")
            return redirect("events:venues")
        except (ValueError, KeyError):
            messages.error(request, "Enter a name, capacity, and valid opening hours.")
    return render(
        request, "events/venue_form.html", {"title": f"Edit {venue.name}", "venue": venue}
    )


def venue_block(request):
    if request.user.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
        require(request.user, Action.EVENTS_CREATE_CENTRAL)
    if request.method == "POST":
        from datetime import datetime

        try:
            from . import booking as booking_commands

            booking_commands.add_block(
                request.user,
                venue_id=int(request.POST["venue"]),
                starts_at=datetime.strptime(request.POST["starts_at"], "%Y-%m-%dT%H:%M"),
                ends_at=datetime.strptime(request.POST["ends_at"], "%Y-%m-%dT%H:%M"),
                reason=request.POST.get("reason", ""),
                operation_key=request.POST.get("operation_key"),
            )
            messages.success(request, "Venue block recorded.")
        except DomainError as exc:
            messages.error(request, exc.message)
        except (KeyError, ValueError):
            messages.error(request, "Enter the venue, interval, and reason.")
    return redirect("events:venues")


def booking_new(request, pk):
    event = selectors.get_event(request.user, pk)
    require(request.user, Action.EVENTS_EDIT, event.club)
    if request.method == "POST":
        from datetime import datetime

        from . import booking as booking_commands

        try:
            booking_commands.submit_booking_request(
                request.user,
                event.pk,
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
                operation_key=request.POST.get("operation_key") or None,
            )
            messages.success(request, "Booking request submitted. It does not hold the room yet.")
            return redirect("events:detail", pk=event.pk)
        except DomainError as exc:
            messages.error(request, exc.message)
        except (KeyError, ValueError):
            messages.error(request, "Enter the venue, dates, times, and headcount.")
    return redirect("events:detail", pk=event.pk)


def booking_decide(request, booking_id: int):
    from . import booking as booking_commands
    from .models import BookingRequest

    booking = BookingRequest.objects.select_related("event").filter(pk=booking_id).first()
    if booking is None:
        from django.http import Http404

        raise Http404
    if request.method == "POST":
        try:
            booking_commands.decide_booking(
                request.user,
                booking.pk,
                decision=request.POST["decision"],
                reason=request.POST.get("reason", ""),
                expected_revision=int(request.POST["revision"]),
                operation_key=request.POST.get("operation_key") or None,
            )
            messages.success(request, "Booking decision recorded.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("events:detail", pk=booking.event_id)

"""Calendar page, heatmap JSON, and the venue availability the modal needs.

Heat scale (product rule): 0 events is free, 1-2 is green, exactly 3 is orange,
more than 3 is red. The same rule is applied on the page and in the JSON so the
modal and the full-page calendar can never disagree.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from apps.clubs.selectors import visible_clubs
from apps.platform_core import clock
from apps.platform_core.access import Action, require

from . import booking
from .models import BookingRequest, Event, Venue
from .selectors import visible_events

CONFIRMED = BookingRequest.Status.CONFIRMED


def _event_card(event: Event) -> dict:
    """One event, in the shape both the page and the modal render."""
    confirmed = next((b for b in event.bookings.all() if b.status == CONFIRMED), None)
    venue_name = confirmed.venue.name if confirmed else (event.proposed_venue or "Not confirmed")
    return {
        "id": event.pk,
        "url": reverse("events:detail", args=[event.pk]),
        "title": event.title,
        "club": event.owner_label,
        "venue": venue_name,
        "start_time": event.start_time.strftime("%H:%M") if event.start_time else "",
        "end_time": event.end_time.strftime("%H:%M") if event.end_time else "",
        "status": event.get_status_display(),
        "is_big": event.is_big,
        "first_date": event.first_date.isoformat(),
        "last_date": event.last_date.isoformat(),
    }


def heat_level(count: int) -> str:
    """Product rule: fewer than three events is free (green), three is busy
    (orange), more than three is packed (red)."""
    if count < 3:
        return "green"
    if count == 3:
        return "orange"
    return "red"


def _month_cells(queryset, year: int, month: int):
    """Return (cells, days) for one month.

    ``cells`` includes ``None`` for the blanks before the first weekday and
    after the last day, so the template can render a 7-column grid directly.
    """
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])

    days: dict[str, list[dict]] = {}
    for event in queryset.filter(first_date__lte=last, last_date__gte=first):
        card = _event_card(event)
        cursor = max(event.first_date, first)
        stop = min(event.last_date, last)
        while cursor <= stop:
            days.setdefault(cursor.isoformat(), []).append(card)
            cursor += timedelta(days=1)

    cells = [None] * ((first.weekday() + 1) % 7)  # Sunday-first offset
    for day in range(1, last.day + 1):
        key = date(year, month, day).isoformat()
        events = days.get(key, [])
        cells.append(
            {
                "key": key,
                "day": day,
                "count": len(events),
                "level": heat_level(len(events)),
                "events": events,
            }
        )
    while len(cells) % 7:
        cells.append(None)
    return cells, days


def _scoped_events(request):
    queryset = visible_events(request.user).prefetch_related("bookings__venue")
    club = request.GET.get("club") or ""
    venue = request.GET.get("venue") or ""
    status = request.GET.get("status") or ""
    if club.isdigit():
        queryset = queryset.filter(club_id=int(club))
    if venue.isdigit():
        queryset = queryset.filter(bookings__venue_id=int(venue)).distinct()
    if status in Event.Status.values:
        queryset = queryset.filter(status=status)
    return queryset, {"club": club, "venue": venue, "status": status}


def calendar(request):
    require(request.user, Action.EVENTS_VIEW)
    today = clock.local_today()

    raw_start = request.GET.get("start")
    try:
        anchor = datetime.strptime(raw_start, "%Y-%m-%d").date() if raw_start else today
    except (TypeError, ValueError):
        anchor = today
    first = date(anchor.year, anchor.month, 1)

    queryset, filters = _scoped_events(request)
    cells, days = _month_cells(queryset, first.year, first.month)
    valid_days = {cell["key"] for cell in cells if cell}

    selected = request.GET.get("date") or ""
    if selected not in valid_days:
        selected = ""

    base = {key: value for key, value in filters.items() if value}

    def month_url(delta: int) -> str:
        target = (first + timedelta(days=32 * delta)).replace(day=1)
        return "?" + urlencode({**base, "start": target.isoformat()})

    def day_url(key: str) -> str:
        return "?" + urlencode({**base, "start": first.isoformat(), "date": key})

    for cell in cells:
        if cell is not None:
            cell["url"] = day_url(cell["key"])
            cell["is_today"] = cell["key"] == today.isoformat()

    upcoming = [
        _event_card(event)
        for event in queryset.filter(last_date__gte=today)
        .order_by("first_date", "start_time")
        .distinct()[:8]
    ]

    return render(
        request,
        "events/calendar.html",
        {
            "cells": cells,
            "month_label": first.strftime("%B %Y"),
            "prev_url": month_url(-1),
            "next_url": month_url(1),
            "today_url": "?"
            + urlencode(
                {**base, "start": today.replace(day=1).isoformat(), "date": today.isoformat()}
            ),
            "selected_key": selected,
            "selected_label": date.fromisoformat(selected).strftime("%A, %d %B %Y")
            if selected
            else "",
            "selected_events": days.get(selected, []),
            "today_key": today.isoformat(),
            "upcoming": upcoming,
            "filters": filters,
            "clubs": visible_clubs(request.user, Action.EVENTS_VIEW),
            "venues": Venue.objects.filter(is_active=True).order_by("name"),
            "statuses": Event.Status.choices,
            "start_value": first.isoformat(),
            "weekdays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        },
    )


def calendar_data(request):
    """JSON for the modal: every day of a month with its heat level and events."""
    require(request.user, Action.EVENTS_VIEW)
    today = clock.local_today()
    try:
        year = int(request.GET.get("year") or today.year)
        month = int(request.GET.get("month") or today.month)
        date(year, month, 1)
    except (TypeError, ValueError):
        year, month = today.year, today.month

    queryset = visible_events(request.user).prefetch_related("bookings__venue")
    cells, days = _month_cells(queryset, year, month)
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])

    payload = {}
    for cell in cells:
        if cell is None:
            continue
        events = days.get(cell["key"], [])
        payload[cell["key"]] = {
            "count": cell["count"],
            "level": cell["level"],
            "events": events,
        }

    return JsonResponse(
        {
            "year": year,
            "month": month,
            "first_day": first.isoformat(),
            "last_day": last.isoformat(),
            "days": payload,
        }
    )


def venue_availability_data(request):
    """JSON: which rooms are free for a day and a time range."""
    require(request.user, Action.EVENTS_VIEW)
    day = request.GET.get("date")
    start = request.GET.get("start") or "18:00"
    end = request.GET.get("end") or "21:00"
    capacity = request.GET.get("capacity")
    intended = request.GET.get("use") or ""

    rows: list[dict] = []
    try:
        on = datetime.strptime(day, "%Y-%m-%d").date() if day else None
        start_t = datetime.strptime(start, "%H:%M").time()
        end_t = datetime.strptime(end, "%H:%M").time()
    except (TypeError, ValueError):
        on = None

    if on is not None and start_t < end_t:
        venues = Venue.objects.filter(is_active=True).order_by("name")
        if capacity and capacity.isdigit():
            venues = venues.filter(capacity__gte=int(capacity))
        if intended in {Venue.Kind.CLASSROOM, Venue.Kind.LARGE_HALL}:
            venues = venues.filter(kind=intended)
        for venue in venues:
            rows.append(
                {
                    "id": venue.pk,
                    "name": venue.name,
                    "location": venue.location,
                    "capacity": venue.capacity,
                    "kind": venue.get_kind_display(),
                    "status": booking.availability(venue, on, start_t, end_t),
                    "opens_at": venue.opens_at.strftime("%H:%M") if venue.opens_at else "",
                    "closes_at": venue.closes_at.strftime("%H:%M") if venue.closes_at else "",
                }
            )

    return JsonResponse({"date": day, "start": start, "end": end, "venues": rows})

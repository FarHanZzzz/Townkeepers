"""Slot suggestions that already pass the booking rules (FR-AIS-02).

A suggestion does not hold a room. The caller still submits a normal booking request.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from apps.platform_core.clock import combine_local

from .booking import availability
from .models import Venue
from .policies import LARGE_VENUE_MINIMUM


def suggest_slots(*, day: date, start: time, duration_minutes: int, headcount: int) -> list[dict]:
    """Return free venues that fit the headcount and opening hours."""
    end_at = combine_local(day, start) + timedelta(minutes=duration_minutes)
    end = end_at.timetz().replace(tzinfo=None)
    if end <= start:
        return []
    found = []
    for venue in Venue.objects.filter(is_active=True).order_by("name"):
        if headcount > venue.capacity:
            continue
        if venue.kind == Venue.Kind.LARGE_HALL and headcount < LARGE_VENUE_MINIMUM:
            continue
        label = availability(venue, day, start, end)
        if label != "free":
            continue
        found.append(
            {
                "venue_id": venue.pk,
                "venue": venue.name,
                "starts": datetime.combine(day, start).strftime("%H:%M"),
                "ends": end.strftime("%H:%M"),
                "reason": "Passes the booking rules. It does not hold the room.",
            }
        )
    return found

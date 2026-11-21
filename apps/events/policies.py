"""Venue booking rules (FR-EVT-05, FR-EVT-06, AC-14, AC-19, decisions D-22 and D-23).

Intervals are half-open: occupancy is [start minus setup, end plus cleanup). Adjacent bookings
do not overlap. A large hall needs at least 350 expected students and must fit the room.
An evening classroom (18:00-21:00) is confirmed by the Faculty Advisor and then the DoSA Head.
A full-day Friday or Saturday classroom (synthetic bounds 09:00-17:00) needs DoSA and then
the System Admin. Official venue hours are not supplied; callers pass the venue's own hours.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from apps.platform_core.clock import combine_local

LARGE_VENUE_MINIMUM = 350
FULL_DAY_START = time(9, 0)
FULL_DAY_END = time(17, 0)
EVENING_START = time(18, 0)
EVENING_END = time(21, 0)


def occupied_bounds(
    day: date, start: time, end: time, setup_minutes: int, cleanup_minutes: int
) -> tuple[datetime, datetime]:
    """Return the half-open occupancy instants for one campus-local day."""
    if end <= start:
        raise ValueError("The end time must be after the start time.")
    if setup_minutes < 0 or cleanup_minutes < 0:
        raise ValueError("Setup and cleanup cannot be negative.")
    return (
        combine_local(day, start) - timedelta(minutes=setup_minutes),
        combine_local(day, end) + timedelta(minutes=cleanup_minutes),
    )


def ranges_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """True when two half-open ranges share any instant. Adjacent ranges do not overlap."""
    return start_a < end_b and start_b < end_a


def booking_days(first: date, last: date) -> list[date]:
    """One day, or two consecutive days. Anything else is rejected by the caller."""
    if last < first:
        raise ValueError("The last date cannot be before the first date.")
    span = (last - first).days
    if span > 1:
        raise ValueError("A booking covers one day or two consecutive days.")
    return [first + timedelta(days=offset) for offset in range(span + 1)]


def large_venue_error(headcount: int, capacity: int) -> str | None:
    """AC-14: 349 fails, 350 proceeds when it also fits the room."""
    if headcount < LARGE_VENUE_MINIMUM:
        return f"A large venue needs at least {LARGE_VENUE_MINIMUM} expected students."
    if headcount > capacity:
        return "The expected headcount is above this venue's capacity."
    return None


def confirmation_route(venue_type: str, day: date, start: time, end: time) -> tuple[str, ...]:
    """Who must confirm, in order (D-22). A large hall is confirmed by the DoSA Head."""
    if venue_type == "large_hall":
        return ("dosa",)
    if day.weekday() in (4, 5) and start <= FULL_DAY_START and end >= FULL_DAY_END:
        return ("dosa", "admin")
    if start >= EVENING_START and end <= EVENING_END:
        return ("advisor", "dosa")
    return ("dosa",)


def within_hours(start: time, end: time, opens: time, closes: time) -> bool:
    return opens <= start and end <= closes

"""Canonical clock. All business timestamps come from here so tests can control time."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

CAMPUS_TZ = ZoneInfo("Asia/Dhaka")


def now() -> datetime:
    """Return the current aware instant (UTC)."""
    return timezone.now()


def local_now() -> datetime:
    """Return the current instant in the campus time zone (Asia/Dhaka)."""
    return now().astimezone(CAMPUS_TZ)


def local_today() -> date:
    """Return today's campus-local date, used for assignment dates and deadlines."""
    return local_now().date()


def to_local(value: datetime) -> datetime:
    """Convert an aware instant to campus-local time."""
    return value.astimezone(CAMPUS_TZ)


def combine_local(day: date, time_of_day) -> datetime:
    """Build an aware instant from a campus-local date and time (NFR-DAT-01)."""
    return datetime.combine(day, time_of_day, tzinfo=CAMPUS_TZ)

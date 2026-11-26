"""Event records and venue booking (FR-EVT-01 to FR-EVT-12)."""

from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.contrib.postgres.indexes import OpClass
from django.db import models
from django.db.models import F, Q

from apps.platform_core import clock


class EventType(models.TextChoices):
    WORKSHOP = "workshop", "Workshop"
    CLASSROOM = "classroom", "Classroom session"
    SEMINAR = "seminar", "Seminar"
    COMPETITION = "competition", "Competition"
    CULTURAL = "cultural", "Cultural event"
    OTHER = "other", "Other"


class Event(models.Model):
    """The working record of an event. Approval-relevant content is frozen in EventVersion."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_APPROVALS = "awaiting_approvals", "Awaiting Approvals"
        APPROVED = "approved", "Approved"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    club = models.ForeignKey(
        "clubs.Club",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="events",
        help_text="Empty for a central DoSA event.",
    )
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    is_big = models.BooleanField(default=False, help_text="Big events use the one-month lead time.")
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    contact = models.CharField(max_length=200, blank=True)
    first_date = models.DateField(help_text="First campus-local event date.")
    last_date = models.DateField()
    start_time = models.TimeField(help_text="Daily start time (Asia/Dhaka).")
    end_time = models.TimeField(help_text="Daily end time (Asia/Dhaka).")
    proposed_venue = models.CharField(max_length=200, blank=True)
    expected_headcount = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    reach = models.CharField(
        max_length=20,
        default="unknown",
        help_text="unknown, campus, national, or international (FR-ANL-05).",
    )
    outcome = models.CharField(
        max_length=20,
        default="unknown",
        help_text="unknown until the Faculty Advisor confirms the outcome (FR-ANL-05).",
    )
    attendance_count = models.PositiveIntegerField(null=True, blank=True)
    attendance_note = models.CharField(max_length=200, blank=True)
    memo_approved_version = models.ForeignKey(
        "EventVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Event version approved through the event-permission memo.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-first_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(last_date__gte=F("first_date")), name="event_last_date_not_before_first"
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")), name="event_end_after_start"
            ),
        ]
        indexes = [models.Index(fields=["club", "status"])]

    def __str__(self) -> str:
        return self.title

    @property
    def starts_at(self):
        return clock.combine_local(self.first_date, self.start_time)

    @property
    def owner_label(self) -> str:
        return self.club.name if self.club_id else "DoSA (central)"


class EventVersion(models.Model):
    """Immutable snapshot of event details used by a memo version (BR-02, FR-COM-05)."""

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField()
    snapshot = models.JSONField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["event", "number"]
        constraints = [
            models.UniqueConstraint(fields=["event", "number"], name="event_version_unique_number")
        ]

    def __str__(self) -> str:
        return f"{self.event} v{self.number}"


class Venue(models.Model):
    """A bookable room. The seeded catalogue is synthetic (D-23) when ``is_synthetic`` is set."""

    class Kind(models.TextChoices):
        CLASSROOM = "classroom", "Classroom"
        LARGE_HALL = "large_hall", "Large hall"

    name = models.CharField(max_length=120, unique=True)
    location = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    facilities = models.TextField(blank=True)
    opens_at = models.TimeField()
    closes_at = models.TimeField()
    is_active = models.BooleanField(default=True)
    is_synthetic = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class VenueRestriction(models.Model):
    """A repeating or dated interval when a venue, or every venue, cannot be booked."""

    venue = models.ForeignKey(
        Venue, null=True, blank=True, on_delete=models.CASCADE, related_name="restrictions"
    )
    weekday = models.PositiveSmallIntegerField(null=True, blank=True)
    local_start = models.TimeField()
    local_end = models.TimeField()
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=200)

    def __str__(self) -> str:
        target = self.venue.name if self.venue_id else "All venues"
        return f"{target}: {self.reason}"


class VenueBlock(models.Model):
    """A one-off closure or central activity (FR-EVT-03)."""

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="blocks")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=200)

    def __str__(self) -> str:
        return f"{self.venue} closed: {self.reason}"


class BookingRequest(models.Model):
    """A venue request. Pending requests do not hold the room (FR-EVT-05, FR-EVT-07)."""

    class FormKind(models.TextChoices):
        CLASSROOM = "classroom", "Classroom form"
        LARGE_VENUE = "large_venue", "Large-venue form"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        RETURNED = "returned", "Returned for Correction"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="bookings")
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="bookings")
    form_kind = models.CharField(max_length=20, choices=FormKind.choices)
    first_date = models.DateField()
    last_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    setup_minutes = models.PositiveSmallIntegerField(default=0)
    cleanup_minutes = models.PositiveSmallIntegerField(default=0)
    headcount = models.PositiveIntegerField()
    filer_designation = models.CharField(max_length=120)
    justification = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    route = models.JSONField(default=list)
    route_index = models.PositiveSmallIntegerField(default=0)
    replaces = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="replacements"
    )
    revision = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event} at {self.venue} ({self.status})"

    @property
    def current_step(self) -> str:
        if self.route_index >= len(self.route):
            return ""
        return self.route[self.route_index]


class BookingDecision(models.Model):
    """One confirmation, return, or decline on a route step."""

    class Decision(models.TextChoices):
        CONFIRM = "confirm", "Confirm"
        RETURN = "return", "Return"
        DECLINE = "decline", "Decline"

    booking = models.ForeignKey(BookingRequest, on_delete=models.PROTECT, related_name="decisions")
    step = models.CharField(max_length=20)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    decision = models.CharField(max_length=20, choices=Decision.choices)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "step", "decision"],
                condition=Q(decision="confirm"),
                name="booking_one_confirmation_per_step",
            )
        ]

    def __str__(self) -> str:
        return f"{self.booking_id} {self.step} {self.decision}"


class Reservation(models.Model):
    """Active occupancy of one venue. Overlaps are rejected by a GiST exclusion constraint."""

    booking = models.ForeignKey(
        BookingRequest, on_delete=models.PROTECT, related_name="reservations"
    )
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="reservations")
    occupied = DateTimeRangeField()
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="reservation_no_active_overlap",
                expressions=[
                    (OpClass("venue", name="gist_int8_ops"), RangeOperators.EQUAL),
                    (OpClass("occupied", name="range_ops"), RangeOperators.OVERLAPS),
                ],
                condition=Q(active=True),
            )
        ]

    def __str__(self) -> str:
        return f"{self.venue_id} {self.occupied}"

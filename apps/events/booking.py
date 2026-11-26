"""Venue catalogue and booking commands (FR-EVT-03 to FR-EVT-09, UC-28 to UC-32).

Confirmation locks the venue, re-reads rules and occupancy, then inserts the reservation.
An exclusion-constraint conflict becomes a normal conflict and keeps the previous reservation.
A request does not hold the room. Two consecutive days are reserved together or not at all.
"""

from __future__ import annotations

from datetime import date, time

from django.db import IntegrityError, transaction
from django.db.backends.postgresql.psycopg_any import DateTimeTZRange
from django.db.models import Q

from apps.platform_core import audit, clock
from apps.platform_core.access import AccessCategory, Action, can, is_assigned_advisor
from apps.platform_core.exceptions import (
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    ValidationFailed,
)
from apps.platform_core.protocol import CommandResult, execute

from . import policies
from .lifecycle import refresh_event_status
from .models import (
    BookingDecision,
    BookingRequest,
    Event,
    Reservation,
    Venue,
    VenueBlock,
    VenueRestriction,
)


def _bounds(booking: BookingRequest):
    days = policies.booking_days(booking.first_date, booking.last_date)
    return [
        policies.occupied_bounds(
            day,
            booking.start_time,
            booking.end_time,
            booking.setup_minutes,
            booking.cleanup_minutes,
        )
        for day in days
    ]


def _problems(
    venue: Venue, booking_fields: dict, *, ignore: BookingRequest | None = None
) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if not venue.is_active:
        errors["venue"] = ["This venue is not available for new requests."]
    headcount = booking_fields["headcount"]
    if headcount > venue.capacity:
        errors["headcount"] = ["The expected headcount is above this venue's capacity."]
    if venue.kind == Venue.Kind.LARGE_HALL:
        message = policies.large_venue_error(headcount, venue.capacity)
        if message:
            errors["headcount"] = [message]
    try:
        days = policies.booking_days(booking_fields["first_date"], booking_fields["last_date"])
    except ValueError as exc:
        errors["last_date"] = [str(exc)]
        return errors
    start, end = booking_fields["start_time"], booking_fields["end_time"]
    if end <= start:
        errors["end_time"] = ["The end time must be after the start time."]
        return errors
    if not policies.within_hours(start, end, venue.opens_at, venue.closes_at):
        errors["start_time"] = ["The booking must fall inside this venue's opening hours."]
    for day in days:
        reason = _restricted(venue, day, start, end)
        if reason:
            errors["start_time"] = [f"Booking blocked by restriction: {reason}"]
            break
        start_at, end_at = policies.occupied_bounds(
            day, start, end, booking_fields["setup_minutes"], booking_fields["cleanup_minutes"]
        )
        if _blocked(venue, start_at, end_at) or _reserved(venue, start_at, end_at, ignore=ignore):
            errors["start_time"] = ["This time is already confirmed or closed for this venue."]
            break
    return errors


def _restricted(venue: Venue, day: date, start: time, end: time) -> str | None:
    rows = VenueRestriction.objects.filter(Q(venue=venue) | Q(venue__isnull=True))
    for row in rows:
        if row.weekday is not None and row.weekday != day.weekday():
            continue
        if row.effective_from and day < row.effective_from:
            continue
        if row.effective_until and day > row.effective_until:
            continue
        # Overnight restrictions wrap past midnight.
        if row.local_start < row.local_end:
            if start < row.local_end and row.local_start < end:
                return row.reason or "This time is restricted."
        else:
            if start < row.local_end or row.local_start < end:
                return row.reason or "This time is restricted."
    return None


def _blocked(venue: Venue, start_at, end_at) -> bool:
    return any(
        policies.ranges_overlap(start_at, end_at, block.starts_at, block.ends_at)
        for block in venue.blocks.all()
    )


def _reserved(venue: Venue, start_at, end_at, *, ignore: BookingRequest | None = None) -> bool:
    span = DateTimeTZRange(start_at, end_at, "[)")
    qs = Reservation.objects.filter(venue=venue, active=True, occupied__overlap=span)
    if ignore is not None:
        qs = qs.exclude(booking=ignore)
    return qs.exists()


def create_venue(
    actor, *, name, location, capacity, kind, opens_at, closes_at, synthetic, operation_key
):
    """Add a venue. Actor: DoSA Head or System Admin (FR-EVT-03)."""

    def handler():
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        if capacity < 1 or not name.strip():
            raise ValidationFailed(field_errors={"name": ["Enter a name and a positive capacity."]})
        venue = Venue.objects.create(
            name=name.strip(),
            location=location.strip(),
            capacity=capacity,
            kind=kind,
            opens_at=opens_at,
            closes_at=closes_at,
            is_synthetic=synthetic,
            created_at=clock.now(),
        )
        audit.record(
            actor, "venue.create", venue, after={"name": venue.name, "synthetic": synthetic}
        )
        return CommandResult("events.venue", venue.pk, "created")

    return execute(
        actor=actor,
        action="venue.create",
        operation_key=operation_key,
        payload={"name": name},
        handler=handler,
    )


def add_block(actor, venue_id: int, *, starts_at, ends_at, reason: str, operation_key):
    """Record a closure. Actor: DoSA Head or System Admin."""

    def handler():
        if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
            raise PermissionDeniedError()
        venue = Venue.objects.select_for_update().filter(pk=venue_id).first()
        if venue is None:
            raise NotFoundError()
        if ends_at <= starts_at or not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter a reason and a real interval."]})
        block = VenueBlock.objects.create(
            venue=venue, starts_at=starts_at, ends_at=ends_at, reason=reason.strip()
        )
        audit.record(actor, "venue.block", venue, reason=reason.strip())
        return CommandResult("events.venueblock", block.pk, "created")

    return execute(
        actor=actor,
        action="venue.block",
        operation_key=operation_key,
        payload={"venue": venue_id, "reason": reason},
        handler=handler,
    )


def submit_booking_request(actor, event_id: int, *, venue_id: int, data: dict, operation_key):
    """Lodge a pending booking after the club memo is approved (FR-EVT-05)."""

    def handler():
        event = Event.objects.select_related("club").filter(pk=event_id).first()
        if event is None or not can(actor, Action.EVENTS_EDIT, event.club):
            raise NotFoundError()
        if event.status == Event.Status.CANCELLED:
            raise InvalidTransitionError("A cancelled event cannot request a venue.")
        if event.club_id is not None:
            from apps.memos.models import Memo, MemoStatus

            if not Memo.objects.filter(event=event, status=MemoStatus.APPROVED).exists():
                raise InvalidTransitionError(
                    "Approve the event-permission memo before booking a venue."
                )
        venue = Venue.objects.filter(pk=venue_id).first()
        if venue is None:
            raise ValidationFailed(field_errors={"venue": ["Choose a venue."]})
        errors = _problems(venue, data)
        if errors:
            raise ValidationFailed(field_errors=errors)
        now = clock.now()
        booking = BookingRequest.objects.create(
            event=event,
            venue=venue,
            form_kind=(
                BookingRequest.FormKind.LARGE_VENUE
                if venue.kind == Venue.Kind.LARGE_HALL
                else BookingRequest.FormKind.CLASSROOM
            ),
            route=list(
                policies.confirmation_route(
                    venue.kind, data["first_date"], data["start_time"], data["end_time"]
                )
            ),
            created_by=actor,
            created_at=now,
            updated_at=now,
            **data,
        )
        audit.record(
            actor, "booking.submit", booking, after={"venue": venue.pk, "route": booking.route}
        )
        return CommandResult("events.bookingrequest", booking.pk, "submitted")

    return execute(
        actor=actor,
        action="booking.submit",
        operation_key=operation_key,
        payload={"event": event_id, "venue": venue_id, **{k: str(v) for k, v in data.items()}},
        handler=handler,
    )


def _actor_may(actor, booking: BookingRequest, step: str) -> bool:
    if step == "advisor":
        return is_assigned_advisor(actor, booking.event.club)
    if step == "dosa":
        return actor.access_category == AccessCategory.DOSA_HEAD
    if step == "admin":
        return actor.access_category == AccessCategory.SYSTEM_ADMIN
    return False


def decide_booking(
    actor, booking_id: int, *, decision: str, reason: str, expected_revision: int, operation_key
):
    """Confirm, return, or decline the current route step (FR-EVT-07, FR-EVT-08)."""

    def handler():
        booking = (
            BookingRequest.objects.select_for_update(of=("self",))
            .select_related("event", "event__club", "venue")
            .filter(pk=booking_id)
            .first()
        )
        if booking is None:
            raise NotFoundError()
        if booking.status != BookingRequest.Status.PENDING:
            raise InvalidTransitionError("This booking is no longer awaiting confirmation.")
        if booking.revision != expected_revision:
            raise ConflictError("This booking was updated. Review it again.")
        step = booking.current_step
        if not _actor_may(actor, booking, step):
            raise PermissionDeniedError("This confirmation step is assigned to someone else.")
        if decision in {"return", "decline"} and not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter the reason."]})
        BookingDecision.objects.create(
            booking=booking,
            step=step,
            actor=actor,
            decision=decision,
            reason=reason.strip(),
            decided_at=clock.now(),
        )
        if decision == "confirm":
            if booking.route_index + 1 < len(booking.route):
                booking.route_index += 1
                booking.revision += 1
                booking.updated_at = clock.now()
                booking.save(update_fields=["route_index", "revision", "updated_at"])
                audit.record(
                    actor, "booking.advance", booking, after={"step": booking.current_step}
                )
                return CommandResult("events.bookingrequest", booking.pk, "advanced")
            _reserve(booking)
            booking.status = BookingRequest.Status.CONFIRMED
        else:
            booking.status = (
                BookingRequest.Status.RETURNED
                if decision == "return"
                else BookingRequest.Status.DECLINED
            )
        booking.revision += 1
        booking.updated_at = clock.now()
        booking.save(update_fields=["status", "revision", "updated_at"])
        if booking.status == BookingRequest.Status.CONFIRMED:
            refresh_event_status(booking.event)
        audit.record(actor, f"booking.{decision}", booking, reason=reason.strip())
        return CommandResult("events.bookingrequest", booking.pk, booking.status)

    return execute(
        actor=actor,
        action="booking.decide",
        operation_key=operation_key,
        payload={
            "booking": booking_id,
            "decision": decision,
            "reason": reason,
            "rev": expected_revision,
        },
        handler=handler,
    )


def _reserve(booking: BookingRequest) -> None:
    venue = Venue.objects.select_for_update().get(pk=booking.venue_id)
    errors = _problems(
        venue,
        {
            "headcount": booking.headcount,
            "first_date": booking.first_date,
            "last_date": booking.last_date,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "setup_minutes": booking.setup_minutes,
            "cleanup_minutes": booking.cleanup_minutes,
        },
    )
    if errors:
        raise ConflictError(
            "The venue rules or another confirmation changed. Review the booking again."
        )
    try:
        with transaction.atomic():
            for start_at, end_at in _bounds(booking):
                Reservation.objects.create(
                    booking=booking,
                    venue=venue,
                    occupied=DateTimeTZRange(start_at, end_at, "[)"),
                    active=True,
                )
    except IntegrityError as exc:
        raise ConflictError("That time was just confirmed for this venue.") from exc


def cancel_event(actor, event_id: int, *, reason: str, operation_key):
    """Cancel an event, close its open bookings, and release occupancy (FR-EVT-10)."""

    def handler():
        event = Event.objects.select_related("club").filter(pk=event_id).first()
        if event is None or not can(actor, Action.EVENTS_EDIT, event.club):
            raise NotFoundError()
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter the reason for cancellation."]})
        if event.status == Event.Status.CANCELLED:
            raise InvalidTransitionError("This event is already cancelled.")
        event.status = Event.Status.CANCELLED
        event.updated_at = clock.now()
        event.revision += 1
        event.save(update_fields=["status", "updated_at", "revision"])
        BookingRequest.objects.filter(event=event, status=BookingRequest.Status.PENDING).update(
            status=BookingRequest.Status.CANCELLED, updated_at=clock.now()
        )
        Reservation.objects.filter(booking__event=event, active=True).update(active=False)
        from apps.publishing.models import Publication

        Publication.objects.filter(event=event, status=Publication.Status.PUBLISHED).update(
            status=Publication.Status.WITHDRAWN, detail="Event cancelled"
        )
        audit.record(actor, "event.cancel", event, reason=reason.strip())
        return CommandResult("events.event", event.pk, "cancelled")

    return execute(
        actor=actor,
        action="event.cancel",
        operation_key=operation_key,
        payload={"event": event_id, "reason": reason},
        handler=handler,
    )


def reschedule_booking(
    actor, booking_id: int, *, venue_id: int, data: dict, expected_revision: int, operation_key
):
    """Move a confirmed booking. A failed new slot leaves the original reservation (FR-EVT-09)."""

    def handler():
        booking = (
            BookingRequest.objects.select_for_update(of=("self",))
            .select_related("event", "venue")
            .filter(pk=booking_id)
            .first()
        )
        if booking is None or not can(actor, Action.EVENTS_EDIT, booking.event.club):
            raise NotFoundError()
        if booking.status != BookingRequest.Status.CONFIRMED:
            raise InvalidTransitionError("Only a confirmed booking can be moved.")
        if booking.revision != expected_revision:
            raise ConflictError("This booking was updated. Review it again.")
        venue = Venue.objects.filter(pk=venue_id).first()
        if venue is None:
            raise ValidationFailed(field_errors={"venue": ["Choose a venue."]})
        for venue_pk in sorted({booking.venue_id, venue.pk}):
            Venue.objects.select_for_update().get(pk=venue_pk)
        errors = _problems(venue, data, ignore=booking)
        if errors:
            raise ConflictError("The new time is not free. The original reservation is unchanged.")
        Reservation.objects.filter(booking=booking, active=True).update(active=False)
        booking.venue = venue
        for field, value in data.items():
            setattr(booking, field, value)
        booking.revision += 1
        booking.updated_at = clock.now()
        booking.save()
        _reserve(booking)
        audit.record(actor, "booking.reschedule", booking, after={"venue": venue.pk})
        return CommandResult("events.bookingrequest", booking.pk, "rescheduled")

    return execute(
        actor=actor,
        action="booking.reschedule",
        operation_key=operation_key,
        payload={"booking": booking_id, "venue": venue_id},
        handler=handler,
    )


def complete_event(actor, event_id: int, *, operation_key):
    """Mark an approved event completed (FR-EVT-11)."""

    def handler():
        event = Event.objects.select_related("club").filter(pk=event_id).first()
        if event is None or not can(actor, Action.EVENTS_EDIT, event.club):
            raise NotFoundError()
        if event.status != Event.Status.APPROVED:
            raise InvalidTransitionError("Only an approved event can be marked completed.")
        event.status = Event.Status.COMPLETED
        event.updated_at = clock.now()
        event.save(update_fields=["status", "updated_at"])
        audit.record(actor, "event.complete", event)
        return CommandResult("events.event", event.pk, "completed")

    return execute(
        actor=actor,
        action="event.complete",
        operation_key=operation_key,
        payload={"event": event_id},
        handler=handler,
    )


def add_restriction(
    actor,
    *,
    venue_id,
    weekday,
    local_start,
    local_end,
    reason,
    operation_key,
    effective_from=None,
    effective_until=None,
):
    """Record a restricted hour. A null venue applies to every venue (FR-EVT-03)."""

    def handler():
        if actor.access_category != AccessCategory.DOSA_HEAD:
            raise PermissionDeniedError()
        venue = Venue.objects.filter(pk=venue_id).first() if venue_id else None
        if venue_id and venue is None:
            raise NotFoundError()
        if local_end <= local_start or not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter a reason and a real interval."]})
        row = VenueRestriction.objects.create(
            venue=venue,
            weekday=weekday,
            local_start=local_start,
            local_end=local_end,
            effective_from=effective_from,
            effective_until=effective_until,
            reason=reason.strip(),
        )
        audit.record(actor, "venue.restrict", row, reason=reason.strip())
        return CommandResult("events.venuerestriction", row.pk, "created")

    return execute(
        actor=actor,
        action="venue.restrict",
        operation_key=operation_key,
        payload={"venue": venue_id, "reason": reason},
        handler=handler,
    )


def record_outcome(
    actor, event_id: int, *, attendance, note: str, reach: str, successful: bool, operation_key
):
    """Record attendance and the Advisor's outcome (FR-ANL-04, FR-ANL-05)."""

    def handler():
        event = Event.objects.select_related("club").filter(pk=event_id).first()
        if event is None:
            raise NotFoundError()
        advisor = is_assigned_advisor(actor, event.club)
        head = actor.access_category == AccessCategory.DOSA_HEAD
        if not advisor and not head and not can(actor, Action.EVENTS_EDIT, event.club):
            raise NotFoundError()
        if attendance is not None and attendance < 0:
            raise ValidationFailed(field_errors={"attendance": ["Attendance cannot be negative."]})
        if reach not in {"unknown", "campus", "national", "international"}:
            raise ValidationFailed(field_errors={"reach": ["Choose a reach."]})
        event.attendance_count = attendance
        event.attendance_note = note.strip()
        event.reach = reach
        if successful:
            if (
                not is_assigned_advisor(actor, event.club)
                and actor.access_category != AccessCategory.DOSA_HEAD
            ):
                raise PermissionDeniedError("The Faculty Advisor confirms a successful outcome.")
            event.outcome = "successful"
        event.updated_at = clock.now()
        event.save(
            update_fields=["attendance_count", "attendance_note", "reach", "outcome", "updated_at"]
        )
        audit.record(
            actor, "event.outcome", event, after={"reach": reach, "outcome": event.outcome}
        )
        return CommandResult("events.event", event.pk, "recorded")

    return execute(
        actor=actor,
        action="event.outcome",
        operation_key=operation_key,
        payload={
            "event": event_id,
            "attendance": attendance,
            "reach": reach,
            "successful": successful,
        },
        handler=handler,
    )


def availability(venue: Venue, day: date, start: time, end: time) -> str:
    """A label for search: free, pending, confirmed, or unavailable. No other club's title."""
    if not venue.is_active or not policies.within_hours(
        start, end, venue.opens_at, venue.closes_at
    ):
        return "unavailable"
    if _restricted(venue, day, start, end):
        return "unavailable"
    start_at, end_at = policies.occupied_bounds(day, start, end, 0, 0)
    if _blocked(venue, start_at, end_at) or _reserved(venue, start_at, end_at):
        return "confirmed"
    pending = BookingRequest.objects.filter(
        venue=venue,
        status=BookingRequest.Status.PENDING,
        first_date__lte=day,
        last_date__gte=day,
        start_time__lt=end,
        end_time__gt=start,
    ).exists()
    return "pending" if pending else "free"

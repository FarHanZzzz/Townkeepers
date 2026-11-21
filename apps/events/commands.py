"""Event commands for Increment 2 (FR-EVT-01, FR-EVT-02 draft path, UC-27)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, time

from apps.platform_core import audit, clock
from apps.platform_core.access import Action, can
from apps.platform_core.exceptions import (
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    StaleRevisionError,
    ValidationFailed,
)
from apps.platform_core.protocol import CommandResult, execute

from .models import Event, EventType, EventVersion
from .selectors import is_draft_editable

SNAPSHOT_FIELDS = (
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


@dataclass(frozen=True)
class EventInput:
    """Event fields collected by the event form; dates and times are campus-local."""

    title: str
    event_type: str
    first_date: date
    last_date: date
    start_time: time
    end_time: time
    is_big: bool = False
    description: str = ""
    contact: str = ""
    proposed_venue: str = ""
    expected_headcount: int | None = None


def validate_event(data: EventInput) -> dict[str, list[str]]:
    """Field errors for invalid titles, types, date order, time order or headcount (FR-EVT-01)."""
    errors: dict[str, list[str]] = {}
    if not data.title.strip():
        errors["title"] = ["Enter the event title."]
    if data.event_type not in EventType.values:
        errors["event_type"] = ["Choose an event type."]
    if data.last_date < data.first_date:
        errors["last_date"] = ["The last date cannot be before the first date."]
    if data.end_time <= data.start_time:
        errors["end_time"] = ["The end time must be after the start time."]
    if data.expected_headcount is not None and data.expected_headcount < 1:
        errors["expected_headcount"] = ["Enter a headcount of at least 1."]
    return errors


def _authorize_owner(actor, club) -> None:
    if club is None:
        if not can(actor, Action.EVENTS_CREATE_CENTRAL):
            raise PermissionDeniedError()
        return
    if not can(actor, Action.EVENTS_EDIT, club):
        raise (
            NotFoundError() if not can(actor, Action.EVENTS_VIEW, club) else PermissionDeniedError()
        )
    if club.is_archived:
        raise InvalidTransitionError("This club is archived and cannot start new requests.")


def create_event(
    actor, *, club_id: int | None, data: EventInput, operation_key: str | None
) -> CommandResult:
    """Create an event draft for the actor's club, or a central DoSA event (FR-EVT-01).

    Actor scope: ``events.edit`` on an active assignment for the club, or ``events.create_central``.
    The actor is recorded as organizer. Invalid dates or times block creation.
    """
    from apps.clubs.models import Club

    def handler():
        club = Club.objects.filter(pk=club_id).first() if club_id else None
        if club_id and club is None:
            raise NotFoundError()
        _authorize_owner(actor, club)
        errors = validate_event(data)
        if errors:
            raise ValidationFailed(field_errors=errors)
        now = clock.now()
        event = Event.objects.create(
            club=club,
            organizer=actor,
            created_by=actor,
            created_at=now,
            updated_at=now,
            **{**asdict(data), "title": data.title.strip()},
        )
        audit.record(actor, "event.create", event, after=asdict(data))
        return CommandResult("events.event", event.pk, "created")

    return execute(
        actor=actor,
        action="event.create",
        operation_key=operation_key,
        payload={"club": club_id, **asdict(data)},
        handler=handler,
    )


def save_event_draft(
    actor, event_id: int, *, data: EventInput, expected_revision: int, operation_key: str | None
) -> CommandResult:
    """Save edits to a draft event (FR-EVT-02, FR-COM-08).

    A newer saved revision raises StaleRevisionError so the editor can compare and reload; events
    in review or approved cannot be edited directly.
    """

    def handler():
        try:
            event = (
                Event.objects.select_for_update(of=("self",))
                .select_related("club")
                .get(pk=event_id)
            )
        except Event.DoesNotExist as exc:
            raise NotFoundError() from exc
        _authorize_owner(actor, event.club)
        if event.revision != expected_revision:
            raise StaleRevisionError(current_state={"revision": event.revision})
        if not is_draft_editable(event):
            raise InvalidTransitionError(
                "This event is in review or approved. Approved changes need an amendment."
            )
        errors = validate_event(data)
        if errors:
            raise ValidationFailed(field_errors=errors)
        before = {f: getattr(event, f) for f in SNAPSHOT_FIELDS}
        for field, value in asdict(data).items():
            setattr(event, field, value.strip() if field == "title" else value)
        event.revision += 1
        event.updated_at = clock.now()
        event.save()
        audit.record(
            actor,
            "event.save_draft",
            event,
            before=before,
            after=asdict(data),
            revision=event.revision,
        )
        return CommandResult("events.event", event.pk, "saved")

    return execute(
        actor=actor,
        action="event.save_draft",
        operation_key=operation_key,
        payload={"event": event_id, "rev": expected_revision, **asdict(data)},
        handler=handler,
    )


def snapshot_event(event: Event, actor) -> EventVersion:
    """Freeze the event's current details as the next EventVersion (called inside a command)."""
    number = (event.versions.order_by("-number").values_list("number", flat=True).first() or 0) + 1
    snapshot = {f: getattr(event, f) for f in SNAPSHOT_FIELDS}
    snapshot = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in snapshot.items()}
    snapshot["club"] = event.club.name if event.club_id else "DoSA"
    return EventVersion.objects.create(
        event=event, number=number, snapshot=snapshot, created_by=actor, created_at=clock.now()
    )

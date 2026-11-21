"""Publish or withdraw an internal notice from the approved event version (FR-PUB-01, FR-PUB-06).

An external destination is recorded as failed until a connector is configured (PRD C.2). A pending
amendment does not replace the published version. The president may publish only their own club.
"""

from __future__ import annotations

from apps.platform_core import audit, clock
from apps.platform_core.access import AccessCategory, Action, can
from apps.platform_core.exceptions import (
    InvalidTransitionError,
    NotFoundError,
)
from apps.platform_core.protocol import CommandResult, execute

from .models import Publication


def _deliver_external(payload: dict) -> tuple[str, str]:
    """Send only the public notice fields. No destination records a failure and changes nothing else."""
    from django.conf import settings

    sender = getattr(settings, "EXTERNAL_PUBLISH_SENDER", None)
    if sender is None and not getattr(settings, "EXTERNAL_PUBLISH_URL", ""):
        return Publication.Status.FAILED, "No external website is configured."
    try:
        if sender is not None:
            sender(payload)
        return Publication.Status.PUBLISHED, ""
    except TimeoutError:
        return Publication.Status.FAILED, "The external website timed out."


def _may_publish(actor, event) -> bool:
    if actor.access_category in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
        return True
    return can(actor, Action.EVENTS_EDIT, event.club)


def publish_notice(actor, event_id: int, *, destination: str, operation_key):
    def handler():
        from apps.events.models import BookingRequest, Event

        event = (
            Event.objects.select_related("club", "memo_approved_version")
            .filter(pk=event_id)
            .first()
        )
        if event is None or not _may_publish(actor, event):
            raise NotFoundError()
        if event.status != Event.Status.APPROVED or event.memo_approved_version_id is None:
            raise InvalidTransitionError("Publish only an approved event version.")
        needs_room = event.club_id is not None
        if (
            needs_room
            and not event.bookings.filter(status=BookingRequest.Status.CONFIRMED).exists()
        ):
            raise InvalidTransitionError("Confirm the venue before publishing this event.")
        if destination == Publication.Destination.EXTERNAL:
            confirmed = (
                event.bookings.filter(status=BookingRequest.Status.CONFIRMED)
                .select_related("venue")
                .first()
            )
            payload = {
                "title": event.title,
                "schedule": (f"{event.first_date} {event.start_time:%H:%M}-{event.end_time:%H:%M}"),
                "venue": confirmed.venue.name if confirmed else "",
                "description": event.description,
            }
            status, detail = _deliver_external(payload)
            row, _created = Publication.objects.update_or_create(
                event=event,
                destination=destination,
                defaults={
                    "event_version": event.memo_approved_version,
                    "status": status,
                    "publisher": actor,
                    "published_at": clock.now(),
                    "detail": detail,
                },
            )
            audit.record(actor, "publication.external", row, after={"status": status})
            return CommandResult("publishing.publication", row.pk, status)
        row, _created = Publication.objects.update_or_create(
            event=event,
            destination=Publication.Destination.INTERNAL,
            defaults={
                "event_version": event.memo_approved_version,
                "status": Publication.Status.PUBLISHED,
                "publisher": actor,
                "published_at": clock.now(),
                "detail": "",
            },
        )
        audit.record(actor, "publication.publish", row, after={"version": row.event_version_id})
        return CommandResult("publishing.publication", row.pk, "published")

    return execute(
        actor=actor,
        action="publication.publish",
        operation_key=operation_key,
        payload={"event": event_id, "destination": destination},
        handler=handler,
    )


def withdraw_notice(actor, event_id: int, *, operation_key):
    def handler():
        row = (
            Publication.objects.select_related("event", "event__club")
            .filter(event_id=event_id, destination=Publication.Destination.INTERNAL)
            .first()
        )
        if row is None or not _may_publish(actor, row.event):
            raise NotFoundError()
        row.status = Publication.Status.WITHDRAWN
        row.detail = "Withdrawn"
        row.save(update_fields=["status", "detail"])
        audit.record(actor, "publication.withdraw", row)
        return CommandResult("publishing.publication", row.pk, "withdrawn")

    return execute(
        actor=actor,
        action="publication.withdraw",
        operation_key=operation_key,
        payload={"event": event_id},
        handler=handler,
    )

"""In-app notices and IUB email intents (FR-COM-02)."""

from __future__ import annotations

from collections.abc import Iterable

from . import clock
from .jobs import enqueue
from .models import Notification

EMAIL_JOB = "notification.email"


def notify(
    recipients: Iterable,
    *,
    event_key: str,
    event_type: str,
    object_type: str,
    object_id,
    subject: str,
    message: str,
    link: str = "",
    email: bool = False,
) -> list[Notification]:
    """Create one notice per recipient for a business event, plus an email job when required.

    Call inside the business transaction. Repeating the same ``event_key`` returns the existing
    notices, so a retried command cannot notify twice. Email goes only to the recipient's IUB
    address recorded on the profile.
    """
    created: list[Notification] = []
    seen: set[int] = set()
    for person in recipients:
        if person is None or person.pk in seen:
            continue
        seen.add(person.pk)
        notice, was_created = Notification.objects.get_or_create(
            event_key=event_key,
            recipient=person,
            defaults={
                "event_type": event_type,
                "object_type": object_type,
                "object_id": str(object_id),
                "subject": subject[:200],
                "message": message,
                "link": link,
                "created_at": clock.now(),
                "email_required": email,
                "email_address": person.iub_email if email else "",
            },
        )
        if was_created and email:
            notice.email_job = enqueue(
                EMAIL_JOB,
                {"notification_id": notice.pk},
                dedupe_key=f"email:{event_key}:{person.pk}",
            )
            notice.save(update_fields=["email_job"])
        created.append(notice)
    return created

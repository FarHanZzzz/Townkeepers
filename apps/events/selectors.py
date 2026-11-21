"""Scoped event reads (FR-EVT-10, FR-COM-01). Out-of-scope events are concealed."""

from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.platform_core.access import Action, club_ids_in_scope
from apps.platform_core.exceptions import NotFoundError

from .models import Event


def visible_events(user, action: str = Action.EVENTS_VIEW) -> QuerySet[Event]:
    scope = club_ids_in_scope(user, action)
    qs = Event.objects.select_related("club", "organizer")
    if scope is None:
        return qs
    return qs.filter(Q(club_id__in=scope))


def get_event(user, pk: int, action: str = Action.EVENTS_VIEW) -> Event:
    event = visible_events(user, action).filter(pk=pk).first()
    if event is None:
        raise NotFoundError()
    return event


def memo_in_review(event: Event) -> bool:
    from apps.memos.models import REVIEW_STATUSES

    return event.memos.filter(status__in=REVIEW_STATUSES).exists()


def is_draft_editable(event: Event) -> bool:
    """Drafts, and events whose memo is back in authorship, can be edited directly (FR-EVT-02).

    Approved events change only through an amendment so the approved version stays in effect.
    """
    if event.status == Event.Status.DRAFT:
        return True
    return (
        event.status == Event.Status.AWAITING_APPROVALS
        and not memo_in_review(event)
        and (event.memo_approved_version_id is None)
    )

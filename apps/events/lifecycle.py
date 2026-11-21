"""When an event may become Approved (FR-EVT-12).

A club event needs an approved event-permission memo and a confirmed booking. A central DoSA
event needs the memo only. Cancellation and completion are not reversed here.
"""

from __future__ import annotations

from apps.platform_core import clock

from .models import BookingRequest, Event


def refresh_event_status(event: Event) -> None:
    """Move a waiting event to Approved once its memo and required booking are both done."""
    if event.status in (Event.Status.CANCELLED, Event.Status.COMPLETED, Event.Status.DRAFT):
        return
    from apps.memos.models import Memo, MemoStatus

    memo_approved = (
        event.memo_approved_version_id is not None
        or Memo.objects.filter(event=event, status=MemoStatus.APPROVED).exists()
    )
    booking_ok = (
        event.club_id is None
        or event.bookings.filter(status=BookingRequest.Status.CONFIRMED).exists()
    )
    if memo_approved and booking_ok and event.status != Event.Status.APPROVED:
        event.status = Event.Status.APPROVED
        event.updated_at = clock.now()
        event.save(update_fields=["status", "updated_at"])

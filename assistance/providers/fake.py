"""Deterministic provider used in development and tests. No network, no external data flow."""

from __future__ import annotations

from datetime import datetime, timedelta

from assistance.contracts import OcrRequest, PriorityRequest, SchedulingRequest


class FakeProvider:
    version = "fake-1"

    def rank_slots(self, request: SchedulingRequest) -> list[dict]:
        prefs = request.preferences

        def score(c):
            preferred = c.venue_id in prefs.preferred_venue_ids
            hour_gap = (
                abs(c.starts_at.hour - prefs.preferred_start_hour)
                if prefs.preferred_start_hour is not None
                else 0
            )
            spare = c.capacity - request.expected_attendance
            return (not preferred, hour_gap, spare, c.starts_at, c.candidate_id)

        ordered = sorted(request.candidates, key=score)
        return [
            {
                "candidate_id": c.candidate_id,
                "rank": i,
                "reason": ("Preferred venue; " if c.venue_id in prefs.preferred_venue_ids else "")
                + f"capacity {c.capacity} for {request.expected_attendance} expected",
            }
            for i, c in enumerate(ordered, start=1)
        ]

    def prioritize(self, request: PriorityRequest) -> list[dict]:
        return deadline_order(request)

    def extract(self, request: OcrRequest, content: bytes) -> dict:
        amount = None
        text = content.decode("latin-1", errors="ignore")
        marker = "amount:"
        if marker in text:
            raw = text.split(marker, 1)[1].split()[0].strip()
            amount = raw or None
        return {
            "fields": {
                "vendor": {"value": None, "confidence": None},
                "amount": {"value": amount, "confidence": None},
            },
            "line_items": [],
        }


def deadline_order(request: PriorityRequest) -> list[dict]:
    """Earliest-deadline-first with event start, queue entry and ID as tie-breakers (FR-AIP-06).

    Items without a deadline stay visible at the end with a missing-deadline flag; the event date is
    never substituted for the approval deadline (FR-AIP-01).
    """
    far = datetime.max.replace(tzinfo=request.now.tzinfo)

    def key(item):
        return (
            item.approval_deadline is None,
            item.approval_deadline or datetime.max.date(),
            item.event_start or far,
            item.queue_entered_at,
            item.queue_id,
        )

    rows = []
    for rank, item in enumerate(sorted(request.items, key=key), start=1):
        flags = []
        if item.approval_deadline is None:
            flags.append("missing_deadline")
            explanation = "No approval deadline recorded; listed after dated requests."
        else:
            remaining = item.approval_deadline - request.now.date()
            explanation = f"Approval deadline {item.approval_deadline.isoformat()} ({remaining.days} days remaining)."
            if remaining.days < 0:
                flags.append("overdue")
            elif remaining < timedelta(hours=item.review_window_hours):
                flags.append("insufficient_time")
        if item.event_start is not None and item.event_start < request.now:
            flags.append("event_passed")
        rows.append(
            {"queue_id": item.queue_id, "rank": rank, "explanation": explanation, "flags": flags}
        )
    return rows

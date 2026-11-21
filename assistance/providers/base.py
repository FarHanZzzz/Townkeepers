"""Provider protocol. Implementations return plain dicts; the app validates them into contracts."""

from __future__ import annotations

from typing import Protocol

from assistance.contracts import OcrRequest, PriorityRequest, SchedulingRequest


class Provider(Protocol):
    version: str

    def rank_slots(self, request: SchedulingRequest) -> list[dict]:
        """Return [{candidate_id, rank, reason}] drawn from request.candidates."""

    def prioritize(self, request: PriorityRequest) -> list[dict]:
        """Return [{queue_id, rank, explanation, flags}] for request.items."""

    def extract(self, request: OcrRequest, content: bytes) -> dict:
        """Return {fields: {...}, line_items: [...]} for the receipt bytes."""

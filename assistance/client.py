"""Django-side client for the assistance service with documented fallbacks (TR section 6).

Every call has a finite timeout. Any transport error, non-200 status or contract violation raises
``AssistanceUnavailable`` so callers keep the manual workflow. Returned IDs are filtered again to
the request's own candidates (defence in depth against stale or invalid suggestions).
"""

from __future__ import annotations

import contextlib

import httpx
from pydantic import ValidationError

from .contracts import PriorityRequest, PriorityResponse, SchedulingRequest, SchedulingResponse
from .providers.fake import deadline_order


class AssistanceUnavailable(Exception):
    """Timeout, outage, rejection or malformed response; the manual path stays available."""


class AssistanceClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"Authorization": f"Bearer {token}"},
        )

    def close(self) -> None:
        self._client.close()

    def _post(self, path: str, payload: dict, model):
        try:
            response = self._client.post(path, json=payload)
        except httpx.HTTPError as exc:
            raise AssistanceUnavailable(f"transport: {type(exc).__name__}") from exc
        if response.status_code != 200:
            code = ""
            with contextlib.suppress(ValueError, KeyError, TypeError):
                code = response.json()["error"]["code"]
            raise AssistanceUnavailable(f"status {response.status_code} {code}".strip())
        try:
            return model.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise AssistanceUnavailable("malformed response") from exc

    def suggest_slots(self, request: SchedulingRequest) -> SchedulingResponse:
        result = self._post(
            "/internal/v1/scheduling/suggest", request.model_dump(mode="json"), SchedulingResponse
        )
        allowed = {c.candidate_id for c in request.candidates}
        result.ranked = [r for r in result.ranked if r.candidate_id in allowed]
        return result

    def prioritize(self, request: PriorityRequest) -> PriorityResponse:
        result = self._post(
            "/internal/v1/priority/suggest", request.model_dump(mode="json"), PriorityResponse
        )
        allowed = {i.queue_id for i in request.items}
        result.ordered = [r for r in result.ordered if r.queue_id in allowed]
        return result


def prioritize_with_fallback(
    client: AssistanceClient | None, request: PriorityRequest
) -> tuple[list[dict], bool]:
    """Return (rows, used_fallback). Falls back to local earliest-deadline-first order (FR-AIP-06)."""
    if client is not None:
        try:
            return [r.model_dump() for r in client.prioritize(request).ordered], False
        except AssistanceUnavailable:
            pass
    return deadline_order(request), True

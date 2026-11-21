"""Audit helper. Call inside the command transaction so the entry commits with the change."""

from __future__ import annotations

from typing import Any

from . import clock
from .logging import correlation_id
from .models import AuditEntry


def record(
    actor,
    action: str,
    obj: Any | None = None,
    *,
    object_type: str | None = None,
    object_id: Any | None = None,
    before: dict | None = None,
    after: dict | None = None,
    reason: str = "",
    revision: int | None = None,
) -> AuditEntry:
    """Append one audit entry for a material action (FR-COM-03).

    If this insert fails, the surrounding transaction rolls back and the action stays uncommitted.
    """
    if obj is not None:
        object_type = object_type or obj._meta.label_lower
        object_id = obj.pk if object_id is None else object_id
    return AuditEntry.objects.create(
        occurred_at=clock.now(),
        actor=actor if getattr(actor, "pk", None) else None,
        effective_role=getattr(actor, "access_category", "") or "",
        action=action,
        object_type=object_type or "",
        object_id=str(object_id if object_id is not None else ""),
        revision=revision,
        before=_jsonable(before or {}),
        after=_jsonable(after or {}),
        reason=reason,
        correlation_id=correlation_id.get(),
    )


def _jsonable(data: dict) -> dict:
    out = {}
    for key, value in data.items():
        if isinstance(value, dict):
            out[key] = _jsonable(value)
        elif isinstance(value, (list, tuple, set)):
            out[key] = [
                v if isinstance(v, (int, float, bool, type(None))) else str(v) for v in value
            ]
        elif isinstance(value, (int, float, bool, type(None), str)):
            out[key] = value
        else:
            out[key] = str(value)
    return out


def history_for(object_type: str, object_id: Any):
    """Entries for one record, oldest first. Callers must apply the viewer's scope first."""
    return AuditEntry.objects.filter(
        object_type=object_type, object_id=str(object_id)
    ).select_related("actor")

"""Command protocol (TECHNICAL_REQUIREMENTS.md section 5).

``execute`` wraps a command handler in one atomic transaction. With an operation key it first
claims ``(actor, action, key)`` in ``CommandReceipt`` inside a savepoint:

* first attempt: the receipt is inserted, the handler runs, and the receipt stores the result;
* replay with the same payload: the unique constraint fires, and the stored result is returned
  without running the handler again;
* reuse with different payload: ``OperationKeyConflict`` (HTTP 409).

Two concurrent attempts with one key serialize on the unique index: the second insert waits for
the first transaction, then either sees its receipt (commit) or proceeds (rollback). Any domain
error raised by the handler rolls back the receipt too, so the operation can be retried.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from django.db import IntegrityError, transaction

from .exceptions import DomainError, OperationKeyConflict
from .models import CommandReceipt

logger = logging.getLogger("townhall.commands")


@dataclass(frozen=True)
class CommandResult:
    """Outcome of a committed command. ``replayed`` is True when returned from a receipt."""

    object_type: str
    object_id: int | str | None
    outcome: str
    data: dict = field(default_factory=dict)
    replayed: bool = False


def payload_hash(payload: dict[str, Any]) -> str:
    """Stable SHA-256 of the semantic payload."""
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def execute(
    *,
    actor,
    action: str,
    operation_key: str | None,
    payload: dict[str, Any],
    handler: Callable[[], CommandResult],
) -> CommandResult:
    """Run ``handler`` once per operation key inside one transaction and log the outcome."""
    started = time.monotonic()
    outcome = "error"
    try:
        result = _execute(actor, action, operation_key, payload, handler)
        outcome = "replayed" if result.replayed else result.outcome
        return result
    except DomainError as exc:
        outcome = exc.code
        raise
    finally:
        logger.info(
            "command=%s actor=%s outcome=%s elapsed_ms=%d",
            action,
            getattr(actor, "pk", None),
            outcome,
            (time.monotonic() - started) * 1000,
        )


def _execute(actor, action, operation_key, payload, handler) -> CommandResult:
    if not operation_key:
        with transaction.atomic():
            return handler()
    digest = payload_hash(payload)
    with transaction.atomic():
        try:
            with transaction.atomic():
                receipt = CommandReceipt.objects.create(
                    actor=actor, action=action, key=str(operation_key)[:64], payload_hash=digest
                )
        except IntegrityError:
            existing = CommandReceipt.objects.get(
                actor=actor, action=action, key=str(operation_key)[:64]
            )
            if existing.payload_hash != digest:
                raise OperationKeyConflict() from None
            stored = dict(existing.result)
            stored.pop("replayed", None)
            return CommandResult(**stored, replayed=True)
        result = handler()
        receipt.result = asdict(result)
        receipt.save(update_fields=["result"])
        return result

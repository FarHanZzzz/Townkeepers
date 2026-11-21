"""Durable PostgreSQL jobs and the worker loop (TECHNICAL_REQUIREMENTS.md sections 1 and 6).

Lock discipline: ``claim_batch`` leases rows with ``SELECT ... FOR UPDATE SKIP LOCKED`` in a short
transaction and commits before any handler performs network I/O. Completion updates are guarded by
``leased_by`` so a worker whose lease expired cannot overwrite the outcome recorded by another.

Delivery guarantee: one business decision and one durable intent per side effect. A worker that
dies after a provider accepted the message but before recording success can cause one repeated
delivery when the lease is recovered; exactly-once email is not promised.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from . import clock
from .exceptions import InvalidTransitionError
from .models import Job, WorkerHeartbeat

logger = logging.getLogger("townhall.worker")

JobHandler = Callable[[Job], str]
HANDLERS: dict[str, JobHandler] = {}


class PermanentJobError(Exception):
    """The job can never succeed (for example, its record no longer exists)."""


class UncertainOutcome(Exception):
    """The provider may have acted (timeout after a remote write). Needs operator reconciliation."""


def job_handler(kind: str) -> Callable[[JobHandler], JobHandler]:
    """Register a handler. It returns a provider reference string on success."""

    def register(fn: JobHandler) -> JobHandler:
        HANDLERS[kind] = fn
        return fn

    return register


def enqueue(kind: str, payload: dict, *, dedupe_key: str) -> Job:
    """Record one intended side effect inside the caller's transaction (idempotent by key)."""
    now = clock.now()
    job, _ = Job.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "kind": kind,
            "payload": payload,
            "next_attempt_at": now,
            "created_at": now,
            "updated_at": now,
            "max_attempts": settings.WORKER_MAX_ATTEMPTS,
        },
    )
    return job


def backoff(attempts: int) -> timedelta:
    """Bounded exponential backoff: 30 s, 60 s, 120 s ... capped at one hour."""
    return timedelta(seconds=min(30 * (2 ** max(attempts - 1, 0)), 3600))


@dataclass
class BatchReport:
    claimed: int = 0
    succeeded: int = 0
    retryable: int = 0
    failed: int = 0
    uncertain: int = 0


def claim_batch(worker_id: str, *, limit: int = 10, lease_seconds: int | None = None) -> list[Job]:
    """Lease runnable jobs, including jobs whose previous lease expired, and commit the lease."""
    lease = timedelta(seconds=lease_seconds or settings.WORKER_LEASE_SECONDS)
    now = clock.now()
    with transaction.atomic():
        jobs = list(
            Job.objects.select_for_update(skip_locked=True)
            .filter(
                Q(state__in=[Job.State.QUEUED, Job.State.RETRYABLE], next_attempt_at__lte=now)
                | Q(state=Job.State.LEASED, lease_expires_at__lt=now)
            )
            .order_by("next_attempt_at", "id")[:limit]
        )
        for job in jobs:
            job.state = Job.State.LEASED
            job.leased_by = worker_id
            job.lease_expires_at = now + lease
            job.attempts += 1
            job.updated_at = now
            job.save(
                update_fields=["state", "leased_by", "lease_expires_at", "attempts", "updated_at"]
            )
    return jobs


def _finish(job: Job, worker_id: str, **fields) -> bool:
    fields["updated_at"] = clock.now()
    return bool(
        Job.objects.filter(pk=job.pk, state=Job.State.LEASED, leased_by=worker_id).update(**fields)
    )


def process(job: Job, worker_id: str, report: BatchReport) -> None:
    """Run one leased job's handler outside any transaction and record the outcome."""
    handler = HANDLERS.get(job.kind)
    now = clock.now()
    try:
        if handler is None:
            raise PermanentJobError(f"No handler registered for {job.kind}")
        reference = handler(job)
    except UncertainOutcome as exc:
        _finish(job, worker_id, state=Job.State.UNCERTAIN, last_error=str(exc)[:2000])
        report.uncertain += 1
    except PermanentJobError as exc:
        _finish(job, worker_id, state=Job.State.FAILED, last_error=str(exc)[:2000])
        report.failed += 1
    except Exception as exc:  # noqa: BLE001  (any provider failure becomes a visible retry)
        logger.warning("job=%s kind=%s attempt=%s failed: %s", job.pk, job.kind, job.attempts, exc)
        if job.attempts >= job.max_attempts:
            _finish(job, worker_id, state=Job.State.FAILED, last_error=str(exc)[:2000])
            report.failed += 1
        else:
            _finish(
                job,
                worker_id,
                state=Job.State.RETRYABLE,
                last_error=str(exc)[:2000],
                next_attempt_at=now + backoff(job.attempts),
            )
            report.retryable += 1
    else:
        _finish(
            job,
            worker_id,
            state=Job.State.SUCCEEDED,
            provider_reference=(reference or "")[:200],
            completed_at=clock.now(),
            last_error="",
        )
        report.succeeded += 1


def run_once(worker_id: str, *, limit: int = 10) -> BatchReport:
    """Claim and process one batch, then record the worker heartbeat."""
    report = BatchReport()
    jobs = claim_batch(worker_id, limit=limit)
    report.claimed = len(jobs)
    for job in jobs:
        process(job, worker_id, report)
    WorkerHeartbeat.objects.update_or_create(
        worker_id=worker_id, defaults={"last_seen": clock.now()}
    )
    return report


def retry_job(actor, job_id: int) -> Job:
    """Re-queue a failed or uncertain job for another attempt (FR-COM-02, FR-PUB-07).

    The job keeps its payload and dedupe key, so the retry targets the original notification and
    recipient and never repeats the underlying business action.
    """
    from . import audit

    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=job_id)
        if job.state not in (Job.State.FAILED, Job.State.UNCERTAIN, Job.State.RETRYABLE):
            raise InvalidTransitionError(
                "Only failed, uncertain or retryable deliveries can be retried."
            )
        before = {"state": job.state, "attempts": job.attempts}
        job.state = Job.State.QUEUED
        job.next_attempt_at = clock.now()
        job.max_attempts = max(job.max_attempts, job.attempts + 1)
        job.updated_at = clock.now()
        job.save(update_fields=["state", "next_attempt_at", "max_attempts", "updated_at"])
        audit.record(actor, "job.retry", job, before=before, after={"state": job.state})
    return job

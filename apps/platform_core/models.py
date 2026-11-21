"""Shared platform records: audit, command receipts, durable jobs, notifications, files, policy."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class AuditEntry(models.Model):
    """Append-only business history (FR-COM-03, NFR-SEC-04).

    A database trigger (migration 0002) rejects UPDATE and DELETE, so entries cannot be edited.
    """

    occurred_at = models.DateTimeField(db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    effective_role = models.CharField(max_length=40, blank=True)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64)
    revision = models.IntegerField(null=True, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True)
    correlation_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [models.Index(fields=["object_type", "object_id"])]

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}:{self.object_id}"


class CommandReceipt(models.Model):
    """Links a retried operation key to the outcome it already produced (BR-10, FR-COM-04)."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    action = models.CharField(max_length=80)
    key = models.CharField(max_length=64)
    payload_hash = models.CharField(max_length=64)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["actor", "action", "key"], name="command_receipt_unique_key"
            )
        ]

    def __str__(self) -> str:
        return f"{self.action}:{self.key}"


class Job(models.Model):
    """One durable intended side effect (email, OCR, publication sync, export).

    States follow TECHNICAL_REQUIREMENTS.md section 6. A business command enqueues inside its own
    transaction; the worker performs network I/O only after leasing, outside any row lock.
    """

    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        LEASED = "leased", "Leased"
        SUCCEEDED = "succeeded", "Succeeded"
        RETRYABLE = "retryable", "Retryable"
        FAILED = "failed", "Failed"
        UNCERTAIN = "uncertain", "Uncertain"

    kind = models.CharField(max_length=60)
    payload = models.JSONField(default=dict)
    dedupe_key = models.CharField(max_length=200, unique=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.QUEUED)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    next_attempt_at = models.DateTimeField()
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    leased_by = models.CharField(max_length=80, blank=True)
    last_error = models.TextField(blank=True)
    provider_reference = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["state", "next_attempt_at"]),
            models.Index(fields=["state", "lease_expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} #{self.pk} ({self.state})"


class WorkerHeartbeat(models.Model):
    worker_id = models.CharField(max_length=80, unique=True)
    last_seen = models.DateTimeField()

    def __str__(self) -> str:
        return self.worker_id


class Notification(models.Model):
    """In-app notice plus the intent to send its IUB email (FR-COM-02).

    One row per business event and recipient; the email job retries this same row and intended
    IUB address, so a retry never repeats the business action.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications"
    )
    event_key = models.CharField(max_length=160)
    event_type = models.CharField(max_length=60)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField()
    read_at = models.DateTimeField(null=True, blank=True)
    email_required = models.BooleanField(default=False)
    email_address = models.EmailField(blank=True)
    email_job = models.ForeignKey(
        Job, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["event_key", "recipient"], name="notification_one_per_event_recipient"
            )
        ]

    def __str__(self) -> str:
        return f"{self.event_type} -> {self.recipient_id}"

    @property
    def email_status(self) -> str:
        if not self.email_required:
            return "Not required"
        if self.email_job is None:
            return "Not queued"
        return self.email_job.get_state_display()


class StoredFile(models.Model):
    """Private file metadata. Bytes live under PRIVATE_MEDIA_ROOT by generated key (FR-COM-06)."""

    class State(models.TextChoices):
        STAGED = "staged", "Staged"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    state = models.CharField(max_length=10, choices=State.choices, default=State.STAGED)
    purpose = models.CharField(max_length=40)
    owner_type = models.CharField(max_length=60, blank=True)
    owner_id = models.CharField(max_length=64, blank=True)
    club = models.ForeignKey(
        "clubs.Club", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["owner_type", "owner_id"])]

    def __str__(self) -> str:
        return f"{self.original_name} ({self.state})"


class Export(models.Model):
    """A completed generated document. Retrieval rechecks permission (TR section 2)."""

    kind = models.CharField(max_length=40)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    file = models.ForeignKey(StoredFile, on_delete=models.PROTECT, related_name="+")
    scope = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.kind} export #{self.pk}"


class PolicyVersion(models.Model):
    """DoSA workflow rules with an effective date (FR-IAM-08).

    A memo records the version in force at submission and keeps it while in review.
    """

    effective_from = models.DateField()
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()
    standard_lead_days = models.PositiveSmallIntegerField(
        default=7, help_text="Workshop/classroom submission lead time in calendar days (PRD 2.6)."
    )
    big_event_lead_months = models.PositiveSmallIntegerField(
        default=1, help_text="Big event submission lead time in calendar months (PRD 2.6)."
    )
    approval_buffer_days = models.PositiveSmallIntegerField(
        default=2,
        help_text="Days before the first event date used as the default approval deadline.",
    )
    review_window_days = models.PositiveSmallIntegerField(
        default=3, help_text="Configured review window shown with priority estimates."
    )
    working_days = models.JSONField(
        default=list, help_text="ISO weekday numbers (1=Mon ... 7=Sun) that count as working days."
    )
    email_on_submission = models.BooleanField(default=True)
    is_synthetic = models.BooleanField(
        default=True, help_text="True until DoSA confirms the values (PRD Appendix C.2)."
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-effective_from", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(standard_lead_days__lte=365) & Q(big_event_lead_months__lte=12),
                name="policy_lead_times_bounded",
            )
        ]

    def __str__(self) -> str:
        label = "synthetic" if self.is_synthetic else "confirmed"
        return f"Policy from {self.effective_from:%d %b %Y} ({label})"

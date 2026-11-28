"""Memo templates, memos, frozen versions, signatures and decisions (FR-MEM-01 to FR-MEM-13).

Invariants enforced in PostgreSQL:

* one final decision per (version, stage) for the Advisor and DoSA stages;
* one decision per (version, stage, actor) for additional signers;
* one signature per (version, stage, signer);
* version numbers are unique per memo, and a submitted version is never updated after freezing
  except for its stage bookkeeping (stage, queue entry, deadline changes with audit).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q


class MemoTemplate(models.Model):
    """A DoSA-labelled template family. Each change creates a TemplateVersion (FR-MEM-01)."""

    label = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=False)
    dosa_only = models.BooleanField(
        default=False,
        help_text="When true, only DoSA personas can see and use this template.",
    )
    current_version = models.ForeignKey(
        "TemplateVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["label"]

    def __str__(self) -> str:
        return self.label


class TemplateVersion(models.Model):
    """Immutable template definition. Memos keep the version they started with (AC-13)."""

    template = models.ForeignKey(MemoTemplate, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField()
    label = models.CharField(max_length=120)
    instructions = models.TextField(blank=True)
    required_fields = models.JSONField(default=list)
    required_attachments = models.JSONField(
        default=list, help_text="List of {key, label, required}."
    )
    signature_areas = models.JSONField(default=list, help_text="Stages with signature blocks.")
    requires_budget = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["template", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "number"], name="template_version_unique_number"
            )
        ]

    def __str__(self) -> str:
        return f"{self.label} v{self.number}"


class MemoStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_ADVISOR = "pending_advisor", "Pending Advisor Confirmation"
    PENDING_ADDITIONAL = "pending_additional", "Pending Additional Signatures"
    PENDING_DOSA = "pending_dosa", "Pending DoSA Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


REVIEW_STATUSES = (
    MemoStatus.PENDING_ADVISOR,
    MemoStatus.PENDING_ADDITIONAL,
    MemoStatus.PENDING_DOSA,
)


class Stage(models.TextChoices):
    ADVISOR = "advisor", "Faculty Advisor Confirmation"
    ADDITIONAL = "additional", "Additional signatures"
    DOSA = "dosa", "DoSA Head Approval"


class Memo(models.Model):
    """One event-permission request. The typed fields are the editable working draft.

    Each send freezes a new MemoVersion; a rejected memo returns to Draft as a linked revision
    with the next version number. An amendment is a separate Memo linked through ``amends``.
    """

    class Kind(models.TextChoices):
        ORIGINAL = "original", "Event permission"
        AMENDMENT = "amendment", "Amendment"

    club = models.ForeignKey("clubs.Club", on_delete=models.PROTECT, related_name="memos")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="memos")
    template_version = models.ForeignKey(
        TemplateVersion, on_delete=models.PROTECT, related_name="memos"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.ORIGINAL)
    amends = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="amendments"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    author_term = models.ForeignKey(
        "clubs.Term",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="EB term of the author when the memo was created (original attribution).",
    )
    status = models.CharField(max_length=20, choices=MemoStatus.choices, default=MemoStatus.DRAFT)
    current_version = models.ForeignKey(
        "MemoVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    budget_version = models.ForeignKey(
        "finance.BudgetVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    school = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=150, blank=True)
    to_line = models.CharField("To", max_length=300, blank=True)
    through_line = models.CharField("Through", max_length=300, blank=True)
    from_line = models.CharField("From", max_length=300, blank=True)
    memo_date = models.DateField(null=True, blank=True)
    subject = models.CharField(max_length=300, blank=True)
    body = models.TextField(blank=True)
    contact = models.CharField(max_length=300, blank=True)
    withdrawn_reason = models.TextField(blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["club", "status"]), models.Index(fields=["status"])]

    def __str__(self) -> str:
        return f"M-{self.pk:03d} {self.subject or self.event.title}"

    @property
    def reference(self) -> str:
        return f"M-{self.pk:03d}"

    @property
    def next_version_number(self) -> int:
        return (self.versions.aggregate(models.Max("number"))["number__max"] or 0) + 1


class MemoVersion(models.Model):
    """A frozen submission. Signatures and decisions always reference one of these (BR-02)."""

    memo = models.ForeignKey(Memo, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField()
    snapshot = models.JSONField()
    content_sha256 = models.CharField(max_length=64)
    template_version = models.ForeignKey(
        TemplateVersion, on_delete=models.PROTECT, related_name="+"
    )
    event_version = models.ForeignKey(
        "events.EventVersion", on_delete=models.PROTECT, related_name="+"
    )
    budget_version = models.ForeignKey(
        "finance.BudgetVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    policy_version = models.ForeignKey(
        "platform_core.PolicyVersion", on_delete=models.PROTECT, related_name="+"
    )
    stage = models.CharField(max_length=20, choices=MemoStatus.choices)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    submitted_at = models.DateTimeField(
        help_text="EB handoff to the Faculty Advisor (server time)."
    )
    dosa_queue_entered_at = models.DateTimeField(null=True, blank=True)
    approval_deadline = models.DateField(null=True, blank=True)
    event_starts_at = models.DateTimeField()
    submission_target = models.DateField()
    is_late = models.BooleanField(default=False)
    concluded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["memo", "number"]
        constraints = [
            models.UniqueConstraint(fields=["memo", "number"], name="memo_version_unique_number")
        ]
        indexes = [models.Index(fields=["stage", "approval_deadline"])]

    def __str__(self) -> str:
        return f"{self.memo.reference} v{self.number}"


class MemoAttachment(models.Model):
    memo = models.ForeignKey(Memo, on_delete=models.PROTECT, related_name="attachments")
    key = models.CharField(max_length=40)
    file = models.ForeignKey("platform_core.StoredFile", on_delete=models.PROTECT, related_name="+")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    uploaded_at = models.DateTimeField()
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["memo", "key", "uploaded_at"]

    def __str__(self) -> str:
        return f"{self.memo_id}:{self.key}"


class SignatureTask(models.Model):
    """An extra signer (for example a Department Head) named by the Advisor for one version."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ENDORSED = "endorsed", "Endorsed"
        RETURNED = "returned", "Returned"

    version = models.ForeignKey(
        MemoVersion, on_delete=models.PROTECT, related_name="signature_tasks"
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="signature_tasks"
    )
    role_label = models.CharField(max_length=120)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    assigned_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["version", "signer"], name="signature_task_unique_signer"
            )
        ]

    def __str__(self) -> str:
        return f"{self.version} {self.role_label} ({self.status})"


class Signature(models.Model):
    """An authenticated signer's e-signature on one exact version and stage (FR-MEM-04)."""

    version = models.ForeignKey(MemoVersion, on_delete=models.PROTECT, related_name="signatures")
    stage = models.CharField(max_length=12, choices=Stage.choices)
    signer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    designation = models.CharField(max_length=150)
    image = models.ForeignKey(
        "platform_core.StoredFile", on_delete=models.PROTECT, related_name="+"
    )
    image_sha256 = models.CharField(max_length=64)
    method = models.CharField(max_length=10, choices=[("drawn", "Drawn"), ("typed", "Typed name")])
    attestation = models.TextField()
    content_sha256 = models.CharField(
        max_length=64, help_text="Hash of the signed version content."
    )
    signed_at = models.DateTimeField()

    class Meta:
        ordering = ["signed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["version", "stage", "signer"], name="signature_one_per_signer_stage"
            )
        ]

    def __str__(self) -> str:
        return f"{self.version} {self.stage} signature"


class MemoDecision(models.Model):
    class Decision(models.TextChoices):
        CONFIRM = "confirm", "Confirmed"
        ENDORSE = "endorse", "Endorsed"
        APPROVE = "approve", "Approved"
        REJECT = "reject", "Rejected"
        RETURN = "return", "Returned"

    version = models.ForeignKey(MemoVersion, on_delete=models.PROTECT, related_name="decisions")
    stage = models.CharField(max_length=12, choices=Stage.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    decision = models.CharField(max_length=10, choices=Decision.choices)
    reason = models.TextField(blank=True)
    signature = models.ForeignKey(
        Signature, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    decided_at = models.DateTimeField()

    class Meta:
        ordering = ["decided_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["version", "stage"],
                condition=Q(stage__in=["advisor", "dosa"]),
                name="memo_decision_one_final_per_stage",
            ),
            models.UniqueConstraint(
                fields=["version", "stage", "actor"], name="memo_decision_one_per_actor"
            ),
            models.CheckConstraint(
                condition=~Q(decision__in=["reject", "return"]) | ~Q(reason=""),
                name="memo_decision_rejection_has_reason",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.version} {self.stage} {self.decision}"


class QueueOverride(models.Model):
    """A reasoned, expiring change to one memo's place in the DoSA queue (FR-AIP-05)."""

    memo = models.ForeignKey("Memo", on_delete=models.CASCADE, related_name="queue_overrides")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    reason = models.TextField()
    prior_order = models.PositiveIntegerField()
    position = models.IntegerField()
    expires_on = models.DateField()
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.memo_id} -> {self.position}"

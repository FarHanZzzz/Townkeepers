"""Club register, EB terms, dated assignments and archive corrections (FR-CLB-01 to FR-CLB-07)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Club(models.Model):
    """Official club identity. The ID stays stable across renames and EB terms (FR-CLB-01)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=150, unique=True)
    short_code = models.CharField(max_length=20, unique=True)
    institutional_profile = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    description = models.TextField(blank=True, help_text="Internal club description (EB editable).")
    internal_contacts = models.TextField(blank=True)
    created_at = models.DateTimeField()
    archived_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_archived(self) -> bool:
        return self.status == self.Status.ARCHIVED


class Term(models.Model):
    """An EB leadership period for one club (FR-CLB-02)."""

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="terms")
    label = models.CharField(max_length=60)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UPCOMING)
    transition_approved = models.BooleanField(
        default=False, help_text="Approved overlap with the adjacent term (FR-CLB-02)."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")), name="term_end_not_before_start"
            ),
            models.UniqueConstraint(
                fields=["club"], condition=Q(status="active"), name="term_one_active_per_club"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.club} {self.label}"


class Assignment(models.Model):
    """A dated link between a person and a club (FR-IAM-04, FR-CLB-03).

    EB assignments belong to a term and carry the typed position title; Faculty Advisor
    assignments name the advised club. Access follows the dates and the grants, never the title.
    """

    class Kind(models.TextChoices):
        EB_MEMBER = "eb_member", "EB appointment"
        FACULTY_ADVISOR = "faculty_advisor", "Faculty Advisor assignment"

    profile = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assignments"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="assignments")
    term = models.ForeignKey(
        Term, null=True, blank=True, on_delete=models.PROTECT, related_name="assignments"
    )
    designation = models.CharField(max_length=120, blank=True)
    responsibilities = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    end_reason = models.TextField(blank=True)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["club", "start_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="assignment_end_not_before_start",
            ),
            models.CheckConstraint(
                condition=Q(kind="faculty_advisor") | Q(term__isnull=False),
                name="assignment_eb_requires_term",
            ),
        ]
        indexes = [models.Index(fields=["club", "term"]), models.Index(fields=["profile", "kind"])]

    def __str__(self) -> str:
        return f"{self.profile} - {self.designation or self.get_kind_display()} ({self.club})"


class ArchiveCorrection(models.Model):
    """An authorized correction to a historical term or appointment (FR-CLB-05).

    The previous value is kept here; the corrected record's revision guards against stale edits.
    """

    object_type = models.CharField(max_length=40)
    object_id = models.PositiveBigIntegerField()
    field = models.CharField(max_length=40)
    previous_value = models.TextField(blank=True)
    new_value = models.TextField()
    reason = models.TextField()
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    corrected_at = models.DateTimeField()
    based_on_revision = models.PositiveIntegerField()

    class Meta:
        ordering = ["-corrected_at"]

    def __str__(self) -> str:
        return f"{self.object_type}:{self.object_id} {self.field}"

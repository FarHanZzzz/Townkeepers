"""Budgets, allocations, releases, expenses and adjustments (FR-FIN-01 to FR-FIN-10)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q


class Currency(models.TextChoices):
    BDT = "BDT", "BDT (Bangladeshi Taka)"
    USD = "USD", "USD (US Dollar)"
    EUR = "EUR", "EUR (Euro)"
    GBP = "GBP", "GBP (Pound Sterling)"
    INR = "INR", "INR (Indian Rupee)"


class Budget(models.Model):
    event = models.OneToOneField("events.Event", on_delete=models.PROTECT, related_name="budget")
    club = models.ForeignKey(
        "clubs.Club", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"Budget for {self.event}"

    @property
    def latest(self):
        return self.versions.order_by("-number").first()


class BudgetVersion(models.Model):
    """Immutable budget revision. A later save creates a new number; earlier ones stay (FR-FIN-04).

    The requested amount is an EB request for review; it is neither an allocation nor a release
    (BR-05, AC-03).
    """

    budget = models.ForeignKey(Budget, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField()
    requested_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    requested_currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.BDT
    )
    purpose = models.TextField(blank=True)
    changed_lines = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["budget", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["budget", "number"], name="budget_version_unique_number"
            ),
            models.CheckConstraint(
                condition=Q(requested_amount__isnull=True) | Q(requested_amount__gt=0),
                name="budget_requested_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.budget.event} budget v{self.number}"

    def totals_by_currency(self) -> dict[str, object]:
        totals: dict[str, object] = {}
        for line in self.lines.all():
            totals[line.currency] = totals.get(line.currency, 0) + line.planned_amount
        return totals


class BudgetLine(models.Model):
    version = models.ForeignKey(BudgetVersion, on_delete=models.PROTECT, related_name="lines")
    position = models.PositiveSmallIntegerField()
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=30, blank=True)
    planned_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.BDT)

    class Meta:
        ordering = ["version", "position"]
        constraints = [
            models.CheckConstraint(
                condition=Q(planned_amount__gte=0), name="budget_line_amount_not_negative"
            ),
            models.CheckConstraint(
                condition=Q(quantity__isnull=True) | Q(quantity__gt=0),
                name="budget_line_quantity_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} {self.currency} {self.planned_amount}"


class BudgetRequestReview(models.Model):
    """The Faculty Advisor's single decision on a budget version's requested amount."""

    class Decision(models.TextChoices):
        ENDORSED = "endorsed", "Endorsed"
        RETURNED = "returned", "Returned with feedback"

    version = models.OneToOneField(BudgetVersion, on_delete=models.PROTECT, related_name="review")
    decision = models.CharField(max_length=10, choices=Decision.choices)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.version} {self.decision}"


class FundingPeriod(models.Model):
    """A reporting period. Amounts in different periods are never added together (FR-FIN-03)."""

    label = models.CharField(max_length=40, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self) -> str:
        return self.label


class Allocation(models.Model):
    """Funding assigned to a club for a period. A later change keeps the previous row (FR-FIN-01)."""

    club = models.ForeignKey("clubs.Club", on_delete=models.PROTECT, related_name="allocations")
    period = models.ForeignKey(FundingPeriod, on_delete=models.PROTECT, related_name="allocations")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.BDT)
    source = models.CharField(max_length=120)
    allocated_on = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name="allocation_not_negative")
        ]

    def __str__(self) -> str:
        return f"{self.club} {self.currency} {self.amount}"


class FundRelease(models.Model):
    """A scheduled, released, or cancelled release. Released is not the same as scheduled (BR-05)."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        RELEASED = "released", "Released"
        CANCELLED = "cancelled", "Cancelled"

    club = models.ForeignKey("clubs.Club", on_delete=models.PROTECT, related_name="releases")
    period = models.ForeignKey(FundingPeriod, on_delete=models.PROTECT, related_name="releases")
    scheduled_amount = models.DecimalField(max_digits=14, decimal_places=2)
    released_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.BDT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    reference = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.club} {self.status} {self.scheduled_amount}"


class EventInflow(models.Model):
    """Part of a confirmed release attributed to one event (BR-11)."""

    release = models.ForeignKey(FundRelease, on_delete=models.PROTECT, related_name="attributions")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="inflows")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.BDT)

    def __str__(self) -> str:
        return f"{self.event_id} {self.currency} {self.amount}"


class Expense(models.Model):
    """A claimed cost. Only a verified expense reduces the balance (FR-FIN-06, FR-FIN-10)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        VERIFIED = "verified", "Verified"
        RETURNED = "returned", "Returned"
        REJECTED = "rejected", "Rejected"

    club = models.ForeignKey("clubs.Club", on_delete=models.PROTECT, related_name="expenses")
    event = models.ForeignKey(
        "events.Event", null=True, blank=True, on_delete=models.PROTECT, related_name="expenses"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.BDT)
    description = models.CharField(max_length=200)
    incurred_on = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    evidence_note = models.CharField(max_length=200, blank=True)
    evidence_key = models.CharField(max_length=64, blank=True)
    extraction_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    extraction_state = models.CharField(max_length=20, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="expense_amount_positive")
        ]

    def __str__(self) -> str:
        return f"{self.description} {self.status}"


class Adjustment(models.Model):
    """A linked correction. The source row is not edited, and the key can be applied once (BR-05)."""

    class Direction(models.TextChoices):
        REDUCE_EXPENSE = "reduce_expense", "Reduce verified expense"
        REDUCE_RELEASE = "reduce_release", "Reduce confirmed release"

    club = models.ForeignKey("clubs.Club", on_delete=models.PROTECT, related_name="adjustments")
    event = models.ForeignKey(
        "events.Event", null=True, blank=True, on_delete=models.PROTECT, related_name="adjustments"
    )
    direction = models.CharField(max_length=20, choices=Direction.choices)
    source_type = models.CharField(max_length=40)
    source_id = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.BDT)
    reason = models.TextField()
    operation_key = models.CharField(max_length=80, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="adjustment_amount_positive")
        ]

    def __str__(self) -> str:
        return f"{self.direction} {self.amount}"


class ConversionRecord(models.Model):
    """The only way two currencies may be combined (FR-FIN-03)."""

    from_currency = models.CharField(max_length=3, choices=Currency.choices)
    to_currency = models.CharField(max_length=3, choices=Currency.choices)
    rate = models.DecimalField(max_digits=14, decimal_places=6)
    recorded_on = models.DateField()
    note = models.CharField(max_length=200)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.from_currency}/{self.to_currency} {self.rate}"

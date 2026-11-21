"""Profiles, grants and profile change requests (FR-IAM-01 to FR-IAM-05)."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.platform_core.access import AccessCategory, Action


class Department(models.TextChoices):
    NA = "na", "N/A"
    CSE = "cse", "Computer Science and Engineering"
    EEE = "eee", "Electrical and Electronic Engineering"
    BBA = "bba", "Business Administration"
    ENV = "env", "Environmental Science"
    ENG = "eng", "English"


class Major(models.TextChoices):
    NA = "na", "N/A"
    CS = "cs", "Computer Science"
    SE = "se", "Software Engineering"
    EEE = "eee", "Electrical and Electronic Engineering"
    FIN = "fin", "Finance"
    MKT = "mkt", "Marketing"


class ProfileManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(iub_email__iexact=username)


class Profile(AbstractBaseUser):
    """One individually signed-in person. Passwords are unusable; sign-in is IUB Google only."""

    iub_email = models.EmailField(
        "IUB email",
        max_length=254,
        unique=True,
        help_text="Stored lower-case; also unique case-insensitively.",
    )
    full_name = models.CharField(max_length=150)
    access_category = models.CharField(max_length=20, choices=AccessCategory.choices)
    designation = models.CharField(
        max_length=120, blank=True, help_text="Typed appointment, for example Club Treasurer."
    )
    department = models.CharField(max_length=10, choices=Department.choices, default=Department.NA)
    major = models.CharField(max_length=10, choices=Major.choices, default=Major.NA)
    personal_email = models.EmailField(blank=True)
    personal_phone = models.CharField(max_length=20, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    permanent_address = models.TextField(blank=True)
    temporary_address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(
        default=False, help_text="Synthetic demonstration identity; usable only with DEMO_AUTH."
    )
    oidc_issuer = models.CharField(max_length=200, blank=True)
    oidc_subject = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField()
    deactivated_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)

    USERNAME_FIELD = "iub_email"
    EMAIL_FIELD = "iub_email"
    REQUIRED_FIELDS = ["full_name"]

    objects = ProfileManager()

    class Meta:
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(Lower("iub_email"), name="profile_unique_iub_email"),
            models.UniqueConstraint(
                fields=["oidc_issuer", "oidc_subject"],
                condition=~Q(oidc_subject=""),
                name="profile_unique_oidc_binding",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_access_category_display()})"

    @property
    def designation_display(self) -> str:
        return self.designation or self.get_access_category_display()


class Grant(models.Model):
    """A checked module/action permission (FR-IAM-02). Revocation keeps the row for history."""

    profile = models.ForeignKey(Profile, on_delete=models.PROTECT, related_name="grants")
    action = models.CharField(max_length=60, choices=Action.choices)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    granted_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "action"],
                condition=Q(revoked_at__isnull=True),
                name="grant_one_active_per_action",
            )
        ]

    def __str__(self) -> str:
        return f"{self.profile_id}:{self.action}"


class ProfileChangeRequest(models.Model):
    """A proposed profile correction (FR-IAM-05). The saved value stays in force while pending."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"

    class Route(models.TextChoices):
        ORDINARY = "ordinary", "Ordinary correction (DoSA)"
        PROTECTED = "protected", "Protected field (account administrator)"

    profile = models.ForeignKey(Profile, on_delete=models.PROTECT, related_name="change_requests")
    field = models.CharField(max_length=40)
    original_value = models.TextField(blank=True)
    proposed_value = models.TextField()
    route = models.CharField(max_length=10, choices=Route.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField()
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at", "-id"]

    def __str__(self) -> str:
        return f"{self.profile_id}:{self.field} ({self.status})"

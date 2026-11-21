"""Internal and external event notices (FR-PUB-01 to FR-PUB-06)."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Publication(models.Model):
    """One notice per event and destination, pinned to an approved event version."""

    class Destination(models.TextChoices):
        INTERNAL = "internal", "Internal club page"
        EXTERNAL = "external", "External club website"

    class Status(models.TextChoices):
        PUBLISHED = "published", "Published"
        WITHDRAWN = "withdrawn", "Withdrawn"
        FAILED = "failed", "Failed"

    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="publications")
    destination = models.CharField(max_length=20, choices=Destination.choices)
    event_version = models.ForeignKey(
        "events.EventVersion", on_delete=models.PROTECT, related_name="+"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    published_at = models.DateTimeField()
    detail = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "destination"], name="publication_one_per_destination"
            )
        ]

    def __str__(self) -> str:
        return f"{self.event} {self.destination} {self.status}"

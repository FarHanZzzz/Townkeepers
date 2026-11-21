"""Imported historical rows keep their source (FR-COM-07)."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class HistoricalImport(models.Model):
    """One imported record and where it came from. The source text is not treated as live workflow."""

    label = models.CharField(max_length=120)
    source = models.CharField(max_length=200)
    row_count = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    imported_at = models.DateTimeField()

    def __str__(self) -> str:
        return self.label

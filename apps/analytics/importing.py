"""Import historical events from a CSV and keep the file name as the source (FR-COM-07).

A bad date or an unknown club rejects the whole file. Nothing is saved in that case.
"""

from __future__ import annotations

import csv
import io
from datetime import date, time

from django.db import transaction

from apps.events.models import Event
from apps.platform_core import audit, clock
from apps.platform_core.access import AccessCategory
from apps.platform_core.exceptions import PermissionDeniedError, ValidationFailed

from .models import HistoricalImport

COLUMNS = ("club_code", "title", "first_date", "status")


def import_events_csv(actor, *, filename: str, text: str):
    if actor.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
        raise PermissionDeniedError()
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or any(column not in reader.fieldnames for column in COLUMNS):
        raise ValidationFailed(
            field_errors={
                "file": ["The file needs columns club_code, title, first_date, and status."]
            }
        )
    from apps.clubs.models import Club

    parsed = []
    for index, row in enumerate(reader, start=2):
        club = Club.objects.filter(short_code=(row.get("club_code") or "").strip()).first()
        if club is None:
            raise ValidationFailed(
                field_errors={"file": [f"Row {index}: unknown club {row.get('club_code')}."]}
            )
        title = (row.get("title") or "").strip()
        if not title:
            raise ValidationFailed(field_errors={"file": [f"Row {index}: enter a title."]})
        try:
            first = date.fromisoformat((row.get("first_date") or "").strip())
        except ValueError as exc:
            raise ValidationFailed(
                field_errors={"file": [f"Row {index}: the date is not YYYY-MM-DD."]}
            ) from exc
        status = (row.get("status") or "").strip()
        if status not in Event.Status.values:
            raise ValidationFailed(
                field_errors={"file": [f"Row {index}: unknown status {status}."]}
            )
        parsed.append((club, title, first, status))
    if not parsed:
        raise ValidationFailed(field_errors={"file": ["The file has no rows."]})
    with transaction.atomic():
        for club, title, first, status in parsed:
            now = clock.now()
            Event.objects.create(
                club=club,
                title=title,
                event_type="other",
                description="Imported historical row.",
                organizer=actor,
                first_date=first,
                last_date=first,
                start_time=time(10, 0),
                end_time=time(12, 0),
                status=status,
                created_by=actor,
                created_at=now,
                updated_at=now,
            )
        record = HistoricalImport.objects.create(
            label=filename,
            source=filename,
            row_count=len(parsed),
            note="CSV import. Drafts and cancellations stay out of completed counts.",
            imported_by=actor,
            imported_at=clock.now(),
        )
        audit.record(
            actor, "history.import", record, after={"source": filename, "rows": len(parsed)}
        )
    return record

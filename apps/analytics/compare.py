"""Term comparison from source events (FR-ANL-05).

Drafts and cancellations are excluded. A missing outcome or reach stays unknown and is not
counted as successful or as national. Each total is the list of event ids a screen can open.
"""

from __future__ import annotations

from apps.events.models import Event


def term_measures(club_id: int, term_start, term_end) -> dict:
    events = Event.objects.filter(
        club_id=club_id,
        status=Event.Status.COMPLETED,
        first_date__gte=term_start,
        first_date__lte=term_end,
    )
    completed = list(events.values_list("pk", flat=True))
    successful = list(events.filter(outcome="successful").values_list("pk", flat=True))
    beyond = list(
        events.filter(reach__in=["national", "international"]).values_list("pk", flat=True)
    )
    return {
        "completed": completed,
        "successful": successful,
        "national_or_international": beyond,
    }

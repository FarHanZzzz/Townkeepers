"""Term comparison (FR-ANL-05)."""

from __future__ import annotations

from django.shortcuts import redirect, render

from apps.clubs.models import Term
from apps.clubs.selectors import visible_clubs
from apps.platform_core.access import Action, require

from .compare import term_measures


def terms(request):
    require(request.user, Action.CLUBS_VIEW)
    club_id = request.GET.get("club")
    clubs = visible_clubs(request.user)
    selected = clubs.filter(pk=club_id).first() if club_id and club_id.isdigit() else clubs.first()
    rows = []
    if selected is not None:
        for term in Term.objects.filter(club=selected).order_by("-start_date"):
            measures = term_measures(selected.pk, term.start_date, term.end_date)
            rows.append(
                {
                    "term": term,
                    "completed": len(measures["completed"]),
                    "successful": len(measures["successful"]),
                    "beyond": len(measures["national_or_international"]),
                }
            )
    return render(
        request,
        "analytics/terms.html",
        {
            "clubs": clubs,
            "selected": selected,
            "rows": rows,
            "opened": _opened(selected, request.GET.get("show")),
        },
    )


def _opened(club, show):
    from apps.events.models import Event

    if club is None or show not in {"completed", "successful", "beyond"}:
        return []
    qs = Event.objects.filter(club=club, status=Event.Status.COMPLETED)
    if show == "successful":
        qs = qs.filter(outcome="successful")
    if show == "beyond":
        qs = qs.filter(reach__in=["national", "international"])
    return list(qs.order_by("first_date"))


def import_history(request):
    from django.contrib import messages

    from apps.platform_core.access import AccessCategory
    from apps.platform_core.exceptions import DomainError, PermissionDeniedError

    from .importing import import_events_csv

    if request.user.access_category not in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN}:
        raise PermissionDeniedError()
    upload = request.FILES.get("file")
    if request.method == "POST" and upload is not None:
        try:
            import_events_csv(
                request.user,
                filename=upload.name,
                text=upload.read().decode("utf-8"),
            )
            messages.success(request, "Import saved. The file name is the source.")
        except DomainError as exc:
            messages.error(request, exc.message)
        except UnicodeDecodeError:
            messages.error(request, "The file must be UTF-8 text.")
    else:
        messages.error(request, "Choose a CSV file.")
    return redirect("analytics:terms")

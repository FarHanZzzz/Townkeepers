from apps.accounts.dashboard import DashItem, Section
from apps.platform_core.access import Action, club_ids_in_scope, effective_actions

from .models import BudgetVersion


def sections(user):
    if Action.FINANCE_ENDORSE_BUDGET not in effective_actions(user):
        return []
    clubs = club_ids_in_scope(user, Action.FINANCE_ENDORSE_BUDGET)
    pending_qs = BudgetVersion.objects.filter(
        requested_amount__isnull=False, review__isnull=True
    ).select_related("budget__event")
    if clubs is not None:
        pending_qs = pending_qs.filter(budget__club_id__in=clubs)
    pending = [v for v in pending_qs if not v.budget.versions.filter(number__gt=v.number).exists()]
    items = [
        DashItem(
            f"{v.budget.event.title}: {v.requested_currency} {v.requested_amount:,.2f}",
            "Awaiting your review",
            v.created_at,
            f"/finance/events/{v.budget.event_id}/budget/",
        )
        for v in pending[:10]
    ]
    return [
        Section("Budget requests awaiting your review", items, "No budget requests are waiting.")
    ]

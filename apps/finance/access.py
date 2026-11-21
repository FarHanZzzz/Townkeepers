"""Receipt downloads recheck finance visibility (FR-FIN-07)."""

from apps.platform_core.access import Action, can
from apps.platform_core.files import register_file_access

from .models import Expense


@register_file_access("expense_evidence")
def expense_evidence_access(user, stored) -> bool:
    expense = Expense.objects.select_related("club").filter(pk=stored.owner_id).first()
    return expense is not None and can(user, Action.FINANCE_VIEW, expense.club)

"""Club dashboard section: the viewer's clubs and their current term."""

from apps.accounts.dashboard import DashItem, Section
from apps.platform_core.access import Action, can

from . import selectors


def sections(user):
    if not can(user, Action.CLUBS_VIEW):
        return []
    items = []
    for club in selectors.visible_clubs(user)[:12]:
        term = selectors.current_term(club)
        status = (
            club.get_status_display()
            if club.is_archived
            else (f"Current term {term.label}" if term else "No current term recorded")
        )
        items.append(
            DashItem(club.name, status, club.archived_at or club.created_at, f"/clubs/{club.pk}/")
        )
    return [Section("Clubs", items, "You have no active club assignment.", "/clubs/")]

from apps.accounts.dashboard import DashItem, Section
from apps.platform_core.access import AccessCategory, Action, can

from . import selectors
from .models import Event


def sections(user):
    if user.access_category != AccessCategory.EB_MEMBER or not can(user, Action.EVENTS_VIEW):
        return []
    events = selectors.visible_events(user).filter(
        status__in=[Event.Status.DRAFT, Event.Status.AWAITING_APPROVALS]
    )[:10]
    items = [
        DashItem(
            f"{e.title} ({e.first_date:%d %b %Y})",
            e.get_status_display(),
            e.updated_at,
            f"/events/{e.pk}/",
        )
        for e in events
    ]
    return [
        Section("Club events in preparation", items, "No events are in preparation.", "/events/")
    ]

"""Navigation shows only modules the signed-in user may use (FR-IAM-06, TR 4.3)."""

from .access import AccessCategory, Action, effective_actions


def navigation(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    actions = effective_actions(user)
    items = [("Dashboard", "dashboard")]
    if Action.MEMOS_VIEW in actions or user.access_category == AccessCategory.SIGNER:
        items.append(("Memo Management", "memos:list"))
    if Action.EVENTS_VIEW in actions:
        items.append(("Events", "events:list"))
        items.append(("Venues", "events:venues"))
    if Action.FINANCE_VIEW in actions:
        items.append(("Finance", "finance:overview"))
    if Action.CLUBS_VIEW in actions:
        items.append(("Reports", "analytics:terms"))
    if Action.CLUBS_VIEW in actions or Action.CLUBS_MANAGE in actions:
        items.append(("Clubs", "clubs:list"))
    if Action.MEMOS_MANAGE_TEMPLATES in actions:
        items.append(("Memo templates", "memos:templates"))
    if Action.ACCOUNTS_VIEW in actions:
        items.append(("Accounts", "accounts:directory"))
    if Action.PROFILE_REVIEW in actions or Action.ACCOUNTS_MANAGE_GRANTS in actions:
        items.append(("Profile requests", "accounts:profile_requests"))
    if Action.NOTIFICATIONS_RETRY in actions:
        items.append(("Deliveries", "platform_core:deliveries"))
    if Action.SETTINGS_MANAGE in actions:
        items.append(("Workflow settings", "platform_core:policy"))
    items.append(("Notifications", "platform_core:notifications"))
    items.append(("My Profile", "accounts:profile"))
    unread = user.notifications.filter(read_at__isnull=True).count()
    return {"nav_items": items, "nav_actions": actions, "unread_notifications": unread}

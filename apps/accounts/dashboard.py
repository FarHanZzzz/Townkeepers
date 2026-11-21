"""Role dashboard composition (FR-IAM-06, UC-04).

Each module contributes sections built from scoped selectors, so the dashboard only lists records
the viewer may open. Links still go through the record's own access check when opened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from importlib import import_module

from apps.platform_core.access import Action, effective_actions
from apps.platform_core.models import Job

from .models import ProfileChangeRequest


@dataclass
class DashItem:
    label: str
    status: str
    updated_at: datetime | None
    url: str
    note: str = ""


@dataclass
class Section:
    title: str
    items: list[DashItem] = field(default_factory=list)
    empty_text: str = "Nothing needs your attention here."
    more_url: str = ""


PROVIDERS = (
    "apps.memos.dashboard",
    "apps.events.dashboard",
    "apps.finance.dashboard",
    "apps.clubs.dashboard",
)


def _account_sections(user) -> list[Section]:
    acts = effective_actions(user)
    sections = []
    routes = []
    if Action.PROFILE_REVIEW in acts:
        routes.append(ProfileChangeRequest.Route.ORDINARY)
    if Action.ACCOUNTS_MANAGE_GRANTS in acts:
        routes.append(ProfileChangeRequest.Route.PROTECTED)
    if routes:
        pending = ProfileChangeRequest.objects.filter(
            route__in=routes, status=ProfileChangeRequest.Status.PENDING
        ).select_related("profile")[:10]
        sections.append(
            Section(
                "Profile correction requests",
                [
                    DashItem(
                        f"#{r.pk} {r.profile.full_name}: {r.field.replace('_', ' ')}",
                        "Pending",
                        r.requested_at,
                        f"/accounts/profile-requests/{r.pk}/",
                    )
                    for r in pending
                ],
                "No profile corrections are waiting.",
                "/accounts/profile-requests/",
            )
        )
    if Action.NOTIFICATIONS_RETRY in acts:
        failing = Job.objects.filter(state__in=[Job.State.FAILED, Job.State.UNCERTAIN]).order_by(
            "-updated_at"
        )[:5]
        sections.append(
            Section(
                "Failed deliveries",
                [
                    DashItem(
                        f"Job #{j.pk} {j.kind}", j.get_state_display(), j.updated_at, "/deliveries/"
                    )
                    for j in failing
                ],
                "No failed or uncertain deliveries.",
                "/deliveries/",
            )
        )
    return sections


def build_dashboard(user) -> list[Section]:
    sections: list[Section] = []
    for module_path in PROVIDERS:
        sections.extend(import_module(module_path).sections(user))
    sections.extend(_account_sections(user))
    unread = user.notifications.filter(read_at__isnull=True)[:5]
    sections.append(
        Section(
            "Unread notifications",
            [DashItem(n.subject, "Unread", n.created_at, "/notifications/") for n in unread],
            "You have no unread notifications.",
            "/notifications/",
        )
    )
    return sections

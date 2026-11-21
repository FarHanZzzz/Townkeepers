"""Access engine: named actions, per-category ceilings, grants and dated club assignments.

Rules (FR-IAM-02, FR-IAM-04, BR-01, NFR-SEC-01):

* A profile may perform an action only when the profile is active, the action is inside its access
  category's ceiling, and it holds an unrevoked grant for that action. A System Admin implicitly
  holds its whole ceiling because it is bootstrapped without a grantor.
* Club-scoped actions additionally need an assignment for that club that is effective today
  (inclusive start and end dates) and, for EB members, belongs to an ACTIVE term. DoSA Head and
  System Admin act across clubs.
* A typed designation never grants anything.

Every call re-reads the database, so a grant or assignment change applies to the next protected
request, including one made from an already-open page.
"""

from __future__ import annotations

from datetime import date

from django.db import models
from django.db.models import Q

from . import clock
from .exceptions import PermissionDeniedError


class AccessCategory(models.TextChoices):
    SYSTEM_ADMIN = "system_admin", "System Admin"
    DOSA_HEAD = "dosa_head", "DoSA Head"
    SIGNER = "signer", "Designated signer"
    EB_MEMBER = "eb_member", "Club EB member"
    FACULTY_ADVISOR = "faculty_advisor", "Faculty Advisor"


class Action(models.TextChoices):
    ACCOUNTS_VIEW = "accounts.view", "View the account directory"
    ACCOUNTS_PROVISION = "accounts.provision", "Provision, deactivate and reactivate profiles"
    ACCOUNTS_MANAGE_GRANTS = "accounts.manage_grants", "Change grants and protected profile fields"
    PROFILE_REVIEW = "accounts.review_profile_change", "Decide ordinary profile corrections"
    NOTIFICATIONS_RETRY = "notifications.retry", "Inspect and retry failed deliveries"
    SETTINGS_MANAGE = "settings.manage", "Configure workflow rules"
    AUDIT_VIEW = "audit.view", "Inspect audit history"
    CLUBS_VIEW = "clubs.view", "View club pages and organogram"
    CLUBS_MANAGE = "clubs.manage", "Maintain the club register, terms and appointments"
    CLUBS_CORRECT_ARCHIVE = "clubs.correct_archive", "Correct EB archive records"
    CLUBS_EDIT_PROFILE = "clubs.edit_internal_profile", "Edit the internal club profile"
    EVENTS_VIEW = "events.view", "View events"
    EVENTS_EDIT = "events.edit", "Create and edit club events"
    EVENTS_CREATE_CENTRAL = "events.create_central", "Create central DoSA events"
    FINANCE_VIEW = "finance.view", "View club finance"
    FINANCE_EDIT_BUDGET = "finance.edit_budget", "Prepare event budgets"
    FINANCE_ENDORSE_BUDGET = "finance.endorse_budget", "Endorse or return budget requests"
    MEMOS_VIEW = "memos.view", "View memos"
    MEMOS_AUTHOR = "memos.author", "Draft, send, revise and withdraw memos"
    MEMOS_MANAGE_TEMPLATES = "memos.manage_templates", "Manage memo templates"
    MEMOS_ADVISOR_CONFIRM = "memos.advisor_confirm", "Confirm or reject memos as Faculty Advisor"
    MEMOS_HEAD_APPROVE = "memos.head_approve", "Approve or reject memos as DoSA Head"
    QUEUE_MANAGE = "queue.manage", "Reorder the approval queue"


A = Action

CLUB_SCOPED: frozenset[str] = frozenset(
    {
        A.CLUBS_VIEW,
        A.CLUBS_MANAGE,
        A.CLUBS_CORRECT_ARCHIVE,
        A.CLUBS_EDIT_PROFILE,
        A.EVENTS_VIEW,
        A.EVENTS_EDIT,
        A.FINANCE_VIEW,
        A.FINANCE_EDIT_BUDGET,
        A.FINANCE_ENDORSE_BUDGET,
        A.MEMOS_VIEW,
        A.MEMOS_AUTHOR,
        A.MEMOS_ADVISOR_CONFIRM,
    }
)

CEILING: dict[str, frozenset[str]] = {
    AccessCategory.SYSTEM_ADMIN: frozenset(
        {
            A.ACCOUNTS_VIEW,
            A.ACCOUNTS_PROVISION,
            A.ACCOUNTS_MANAGE_GRANTS,
            A.PROFILE_REVIEW,
            A.NOTIFICATIONS_RETRY,
            A.AUDIT_VIEW,
            A.QUEUE_MANAGE,
            A.CLUBS_VIEW,
            A.EVENTS_VIEW,
            A.MEMOS_VIEW,
        }
    ),
    AccessCategory.DOSA_HEAD: frozenset(
        {
            A.ACCOUNTS_VIEW,
            A.ACCOUNTS_PROVISION,
            A.ACCOUNTS_MANAGE_GRANTS,
            A.PROFILE_REVIEW,
            A.NOTIFICATIONS_RETRY,
            A.SETTINGS_MANAGE,
            A.AUDIT_VIEW,
            A.CLUBS_VIEW,
            A.CLUBS_MANAGE,
            A.CLUBS_CORRECT_ARCHIVE,
            A.EVENTS_VIEW,
            A.EVENTS_CREATE_CENTRAL,
            A.FINANCE_VIEW,
            A.MEMOS_VIEW,
            A.MEMOS_MANAGE_TEMPLATES,
            A.MEMOS_HEAD_APPROVE,
            A.QUEUE_MANAGE,
        }
    ),
    AccessCategory.FACULTY_ADVISOR: frozenset(
        {
            A.CLUBS_VIEW,
            A.EVENTS_VIEW,
            A.FINANCE_VIEW,
            A.FINANCE_ENDORSE_BUDGET,
            A.MEMOS_VIEW,
            A.MEMOS_ADVISOR_CONFIRM,
        }
    ),
    AccessCategory.EB_MEMBER: frozenset(
        {
            A.CLUBS_VIEW,
            A.CLUBS_EDIT_PROFILE,
            A.EVENTS_VIEW,
            A.EVENTS_EDIT,
            A.FINANCE_VIEW,
            A.FINANCE_EDIT_BUDGET,
            A.MEMOS_VIEW,
            A.MEMOS_AUTHOR,
        }
    ),
    # A designated signer acts only on signature tasks assigned to its own identity.
    AccessCategory.SIGNER: frozenset(),
}

# Account-administration grants only a System Admin may hand out (delegation limit, FR-IAM-03).
ADMIN_ONLY_GRANTS: frozenset[str] = frozenset({A.ACCOUNTS_PROVISION, A.ACCOUNTS_MANAGE_GRANTS})
GLOBAL_SCOPE_CATEGORIES = frozenset({AccessCategory.SYSTEM_ADMIN, AccessCategory.DOSA_HEAD})


def _granted(profile) -> set[str]:
    from apps.accounts.models import Grant

    return set(
        Grant.objects.filter(profile_id=profile.pk, revoked_at__isnull=True).values_list(
            "action", flat=True
        )
    )


# Demonstration personas only (seed_demo, is_demo). Real profiles stay on CEILING.
# Admin may use every action. DoSA and the Faculty Advisor share permission-giving.
# A club president may manage the club they are appointed to.
DEMO_PERMISSION = frozenset(
    {
        A.CLUBS_VIEW,
        A.EVENTS_VIEW,
        A.FINANCE_VIEW,
        A.FINANCE_ENDORSE_BUDGET,
        A.MEMOS_VIEW,
        A.MEMOS_ADVISOR_CONFIRM,
        A.MEMOS_HEAD_APPROVE,
        A.QUEUE_MANAGE,
        A.PROFILE_REVIEW,
    }
)
DEMO_CLUB_MANAGEMENT = frozenset(
    {
        A.CLUBS_VIEW,
        A.CLUBS_MANAGE,
        A.CLUBS_CORRECT_ARCHIVE,
        A.CLUBS_EDIT_PROFILE,
        A.EVENTS_VIEW,
        A.EVENTS_EDIT,
        A.FINANCE_VIEW,
        A.FINANCE_EDIT_BUDGET,
        A.MEMOS_VIEW,
        A.MEMOS_AUTHOR,
    }
)


def effective_actions(profile) -> set[str]:
    """Return the actions the profile may use somewhere (ignoring club scope)."""
    if profile is None or not getattr(profile, "is_authenticated", False) or not profile.is_active:
        return set()
    ceiling = CEILING.get(profile.access_category, frozenset())
    if profile.access_category == AccessCategory.SYSTEM_ADMIN:
        actions = set(ceiling)
    else:
        actions = _granted(profile) & set(ceiling)
    if not getattr(profile, "is_demo", False):
        return actions
    if profile.access_category == AccessCategory.SYSTEM_ADMIN:
        return {action.value for action in Action}
    if profile.access_category in {AccessCategory.DOSA_HEAD, AccessCategory.FACULTY_ADVISOR}:
        actions |= set(DEMO_PERMISSION)
    elif profile.access_category == AccessCategory.EB_MEMBER:
        actions |= set(DEMO_CLUB_MANAGEMENT)
    return actions


def active_assignment_filter(on: date) -> Q:
    """Q for assignments effective on a campus-local date (inclusive bounds, open end allowed)."""
    return (
        Q(start_date__lte=on)
        & (Q(end_date__isnull=True) | Q(end_date__gte=on))
        & (Q(term__isnull=True) | Q(term__status="active"))
    )


def assigned_club_ids(profile, on: date | None = None) -> set[int]:
    """Clubs where the profile holds an assignment effective on the given local date."""
    from apps.clubs.models import Assignment

    on = on or clock.local_today()
    kinds = {
        AccessCategory.EB_MEMBER: Assignment.Kind.EB_MEMBER,
        AccessCategory.FACULTY_ADVISOR: Assignment.Kind.FACULTY_ADVISOR,
    }
    kind = kinds.get(profile.access_category)
    if kind is None:
        return set()
    return set(
        Assignment.objects.filter(active_assignment_filter(on), profile_id=profile.pk, kind=kind)
        .filter(Q(kind=Assignment.Kind.FACULTY_ADVISOR) | Q(term__isnull=False))
        .values_list("club_id", flat=True)
    )


def club_ids_in_scope(profile, action: str) -> set[int] | None:
    """Clubs where the action is permitted. ``None`` means every club (global scope)."""
    if action not in effective_actions(profile):
        return set()
    if profile.access_category in GLOBAL_SCOPE_CATEGORIES:
        return None
    if action not in CLUB_SCOPED:
        return set()
    return assigned_club_ids(profile)


def can(profile, action: str, club=None) -> bool:
    """Return True when the profile may perform ``action`` (on ``club`` for club-scoped actions)."""
    if action not in effective_actions(profile):
        return False
    if action not in CLUB_SCOPED or profile.access_category in GLOBAL_SCOPE_CATEGORIES:
        return True
    if club is None:
        return bool(assigned_club_ids(profile))
    club_id = getattr(club, "pk", club)
    return club_id in assigned_club_ids(profile)


def require(profile, action: str, club=None) -> None:
    """Raise PermissionDeniedError unless ``can`` allows the action."""
    if not can(profile, action, club):
        raise PermissionDeniedError()


def is_assigned_advisor(profile, club) -> bool:
    """True when the profile may confirm memos for this club (FR-MEM-04, FR-MEM-07).

    Club scope still applies. A DoSA Head reaches a club only when that action is in their
    effective set and their category is global, which the demonstration seed grants so DoSA and
    the Faculty Advisor share permission-giving.
    """
    return can(profile, A.MEMOS_ADVISOR_CONFIRM, club)

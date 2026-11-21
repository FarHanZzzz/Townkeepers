"""Synthetic identities and records for tests. No real institutional data (AGENTS.md section 3)."""

from __future__ import annotations

import itertools
import uuid
from datetime import date

from apps.accounts.models import Grant, Profile
from apps.clubs.models import Assignment, Club, Term
from apps.platform_core import clock
from apps.platform_core.access import CEILING, AccessCategory

DOMAIN = "iub-synthetic.test"
_seq = itertools.count(1)


def key() -> str:
    """A fresh operation key."""
    return uuid.uuid4().hex


def make_profile(
    category: str,
    *,
    name: str | None = None,
    email: str | None = None,
    grants: set[str] | None = None,
    is_demo: bool = False,
    created_by: Profile | None = None,
) -> Profile:
    """Create a profile directly with its full ceiling granted unless ``grants`` is given."""
    n = next(_seq)
    profile = Profile.objects.create(
        iub_email=email or f"user{n}@{DOMAIN}",
        full_name=name or f"Synthetic User {n}",
        access_category=category,
        created_at=clock.now(),
        is_demo=is_demo,
        created_by=created_by,
    )
    profile.set_unusable_password()
    profile.save(update_fields=["password"])
    actions = CEILING[category] if grants is None else grants
    if category != AccessCategory.SYSTEM_ADMIN:
        for action in actions:
            Grant.objects.create(profile=profile, action=action, granted_at=clock.now())
    return profile


def make_club(name: str, code: str) -> Club:
    return Club.objects.create(name=name, short_code=code, created_at=clock.now())


def make_term(
    club: Club,
    created_by: Profile,
    *,
    status: str = Term.Status.ACTIVE,
    label="2026-27",
    start=date(2026, 1, 1),
    end=date(2027, 12, 31),
) -> Term:
    return Term.objects.create(
        club=club,
        label=label,
        start_date=start,
        end_date=end,
        status=status,
        created_by=created_by,
        created_at=clock.now(),
    )


def assign_eb(
    profile: Profile,
    term: Term,
    granted_by: Profile,
    designation: str = "",
    start=date(2026, 1, 1),
    end=None,
) -> Assignment:
    return Assignment.objects.create(
        profile=profile,
        kind=Assignment.Kind.EB_MEMBER,
        club=term.club,
        term=term,
        designation=designation,
        start_date=start,
        end_date=end,
        granted_by=granted_by,
        created_at=clock.now(),
    )


def assign_advisor(
    profile: Profile, club: Club, granted_by: Profile, start=date(2026, 1, 1), end=None
) -> Assignment:
    return Assignment.objects.create(
        profile=profile,
        kind=Assignment.Kind.FACULTY_ADVISOR,
        club=club,
        start_date=start,
        end_date=end,
        granted_by=granted_by,
        created_at=clock.now(),
    )

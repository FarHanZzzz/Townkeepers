"""Scoped club reads. Out-of-scope records raise NotFoundError so their existence is concealed."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.platform_core.access import Action, club_ids_in_scope
from apps.platform_core.exceptions import NotFoundError

from .models import Assignment, Club, Term


def visible_clubs(user, action: str = Action.CLUBS_VIEW) -> QuerySet[Club]:
    scope = club_ids_in_scope(user, action)
    if scope is None:
        return Club.objects.all()
    return Club.objects.filter(pk__in=scope)


def get_club(user, pk: int, action: str = Action.CLUBS_VIEW) -> Club:
    club = visible_clubs(user, action).filter(pk=pk).first()
    if club is None:
        raise NotFoundError()
    return club


def current_term(club: Club) -> Term | None:
    return club.terms.filter(status=Term.Status.ACTIVE).first()


def term_members(term: Term):
    return (
        Assignment.objects.filter(term=term, kind=Assignment.Kind.EB_MEMBER)
        .select_related("profile")
        .order_by("start_date", "designation")
    )


def club_advisors(club: Club):
    return Assignment.objects.filter(
        club=club, kind=Assignment.Kind.FACULTY_ADVISOR
    ).select_related("profile")

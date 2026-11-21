"""Hand unfinished work to the next president without rewriting who wrote the memo (FR-CLB-06)."""

from __future__ import annotations

from apps.platform_core import audit, clock
from apps.platform_core.access import Action, require
from apps.platform_core.exceptions import InvalidTransitionError, NotFoundError, ValidationFailed
from apps.platform_core.protocol import CommandResult, execute

from .models import Assignment, Term


def handover_term(actor, term_id: int, *, successor_id: int, reason: str, operation_key):
    """End the current president's appointment and move unfinished memos and events.

    ``Memo.author_term`` stays on the term that drafted the memo.
    """

    def handler():
        from apps.accounts.models import Profile
        from apps.events.models import Event
        from apps.memos.models import Memo, MemoStatus

        term = Term.objects.select_related("club").filter(pk=term_id).first()
        if term is None:
            raise NotFoundError()
        require(actor, Action.CLUBS_MANAGE, term.club)
        if term.status != Term.Status.ACTIVE:
            raise InvalidTransitionError("Only the active term can be handed over.")
        successor = Profile.objects.filter(pk=successor_id, is_active=True).first()
        if successor is None or not reason.strip():
            raise ValidationFailed(
                field_errors={"successor": ["Choose an active successor and a reason."]}
            )
        today = clock.local_today()
        now = clock.now()
        outgoing = list(
            term.assignments.filter(
                kind=Assignment.Kind.EB_MEMBER, ended_at__isnull=True
            ).select_related("profile")
        )
        outgoing_ids = [row.profile_id for row in outgoing]
        for row in outgoing:
            if row.profile_id == successor.pk:
                continue
            row.end_date = today
            row.ended_at = now
            row.save(update_fields=["end_date", "ended_at"])
        if not term.assignments.filter(
            profile=successor, kind=Assignment.Kind.EB_MEMBER, ended_at__isnull=True
        ).exists():
            Assignment.objects.create(
                profile=successor,
                term=term,
                club=term.club,
                kind=Assignment.Kind.EB_MEMBER,
                designation="President",
                start_date=today,
                granted_by=actor,
                created_at=now,
            )
        open_statuses = [
            MemoStatus.DRAFT,
            MemoStatus.PENDING_ADVISOR,
            MemoStatus.PENDING_ADDITIONAL,
            MemoStatus.PENDING_DOSA,
            MemoStatus.REJECTED,
        ]
        memos = Memo.objects.filter(
            club=term.club, author_id__in=outgoing_ids, status__in=open_statuses
        )
        moved_memos = memos.update(author=successor, updated_at=now)
        moved_events = (
            Event.objects.filter(club=term.club, organizer_id__in=outgoing_ids)
            .exclude(status__in=[Event.Status.COMPLETED, Event.Status.CANCELLED])
            .update(organizer=successor, updated_at=now)
        )
        audit.record(
            actor,
            "term.handover",
            term,
            reason=reason.strip(),
            after={"successor": successor.pk, "memos": moved_memos, "events": moved_events},
        )
        return CommandResult(
            "clubs.term", term.pk, "handed_over", {"memos": moved_memos, "events": moved_events}
        )

    return execute(
        actor=actor,
        action="term.handover",
        operation_key=operation_key,
        payload={"term": term_id, "successor": successor_id, "reason": reason},
        handler=handler,
    )

"""Scoped memo reads, next-actor description and the DoSA queue order (FR-MEM-10, FR-AIP-02)."""

from __future__ import annotations

from django.db.models import F, Q, QuerySet

from apps.platform_core.access import Action, can, club_ids_in_scope
from apps.platform_core.exceptions import NotFoundError

from .models import Memo, MemoStatus, MemoVersion, SignatureTask


def visible_memos(user) -> QuerySet[Memo]:
    """Memos in the user's club scope, plus memos where the user holds a signature task."""
    qs = Memo.objects.select_related(
        "club", "event", "template_version", "current_version", "author"
    )
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return qs.none()
    scope = club_ids_in_scope(user, Action.MEMOS_VIEW)
    if scope is None:
        return qs
    tasks = Q(versions__signature_tasks__signer=user)
    return qs.filter(Q(club_id__in=scope) | tasks).distinct()


def can_view_memo(user, memo: Memo) -> bool:
    return visible_memos(user).filter(pk=memo.pk).exists()


def get_memo(user, pk: int) -> Memo:
    memo = visible_memos(user).filter(pk=pk).first()
    if memo is None:
        raise NotFoundError()
    return memo


def pending_task_for(user, memo: Memo) -> SignatureTask | None:
    if not memo.current_version_id:
        return None
    return memo.current_version.signature_tasks.filter(
        signer=user, status=SignatureTask.Status.PENDING
    ).first()


def next_actor(memo: Memo) -> str:
    """Human description of who must act next (FR-MEM-07)."""
    if memo.status == MemoStatus.DRAFT:
        return "EB author (authorship)"
    if memo.status == MemoStatus.PENDING_ADVISOR:
        return "Assigned Faculty Advisor"
    if memo.status == MemoStatus.PENDING_ADDITIONAL:
        names = [
            t.signer.full_name
            for t in memo.current_version.signature_tasks.filter(
                status=SignatureTask.Status.PENDING
            ).select_related("signer")
        ]
        return "Additional signer: " + ", ".join(names) if names else "Additional signers"
    if memo.status == MemoStatus.PENDING_DOSA:
        return "DoSA Head"
    if memo.status == MemoStatus.REJECTED:
        return "EB author (may start a revision)"
    return "No further action"


def user_can_review(user, memo: Memo) -> bool:
    from apps.platform_core.access import is_assigned_advisor

    if memo.status == MemoStatus.PENDING_ADVISOR:
        return is_assigned_advisor(user, memo.club)
    if memo.status == MemoStatus.PENDING_ADDITIONAL:
        return pending_task_for(user, memo) is not None
    if memo.status == MemoStatus.PENDING_DOSA:
        return can(user, Action.MEMOS_HEAD_APPROVE)
    return False


def dosa_queue() -> QuerySet[MemoVersion]:
    """Actionable versions awaiting the Head, ordered by approval deadline, then event start,
    then queue entry and stable memo ID (FR-AIP-02 deterministic base order and fallback)."""
    return (
        MemoVersion.objects.filter(
            stage=MemoStatus.PENDING_DOSA, memo__status=MemoStatus.PENDING_DOSA
        )
        .select_related("memo", "memo__club", "memo__event")
        .order_by(
            F("approval_deadline").asc(nulls_last=True),
            "event_starts_at",
            "dosa_queue_entered_at",
            "memo_id",
        )
    )

"""Memo dashboard sections per role (FR-IAM-06, FR-MEM-10)."""

from apps.accounts.dashboard import DashItem, Section
from apps.platform_core import clock
from apps.platform_core.access import AccessCategory, Action, can, club_ids_in_scope

from . import selectors
from .models import MemoStatus, SignatureTask


def _row(memo, note=""):
    return DashItem(
        f"{memo.reference} {memo.subject or memo.event.title}",
        memo.get_status_display(),
        memo.updated_at,
        f"/memos/{memo.pk}/",
        note,
    )


def sections(user):
    out = []
    today = clock.local_today()
    if can(user, Action.MEMOS_HEAD_APPROVE):
        items = []
        for v in selectors.dosa_queue()[:10]:
            flags = []
            if v.approval_deadline is None:
                flags.append("Missing approval deadline")
            elif v.approval_deadline < today:
                flags.append(f"Overdue since {v.approval_deadline:%d %b %Y}")
            else:
                flags.append(f"Deadline {v.approval_deadline:%d %b %Y}")
            if v.is_late:
                flags.append("Submitted late")
            items.append(
                DashItem(
                    f"{v.memo.reference} {v.memo.subject} ({v.memo.club.short_code})",
                    "Pending DoSA Approval",
                    v.dosa_queue_entered_at,
                    f"/memos/{v.memo_id}/review/",
                    " · ".join(flags),
                )
            )
        out.append(
            Section(
                "Memos awaiting your approval (deadline order)",
                items,
                "No memos are waiting for DoSA approval.",
                "/memos/?status=pending_dosa",
            )
        )
    if can(user, Action.MEMOS_ADVISOR_CONFIRM):
        memos = selectors.visible_memos(user).filter(status=MemoStatus.PENDING_ADVISOR)
        out.append(
            Section(
                "Memos awaiting your confirmation",
                [_row(m) for m in memos[:10]],
                "No memos are waiting for your confirmation.",
                "/memos/?status=pending_advisor",
            )
        )
    if user.access_category == AccessCategory.SIGNER:
        tasks = SignatureTask.objects.filter(
            signer=user,
            status=SignatureTask.Status.PENDING,
            version__memo__status=MemoStatus.PENDING_ADDITIONAL,
        ).select_related("version__memo__event")
        out.append(
            Section(
                "Signature tasks",
                [_row(t.version.memo, f"Requested as {t.role_label}") for t in tasks],
                "No signature tasks are assigned to you.",
                "/memos/",
            )
        )
    if user.access_category == AccessCategory.EB_MEMBER and club_ids_in_scope(
        user, Action.MEMOS_VIEW
    ):
        memos = selectors.visible_memos(user).exclude(
            status__in=[MemoStatus.APPROVED, MemoStatus.WITHDRAWN]
        )
        out.append(
            Section(
                "Club memos in progress",
                [_row(m, selectors.next_actor(m)) for m in memos[:10]],
                "No memos are in progress. Start one from Memo Management.",
                "/memos/",
            )
        )
    return out

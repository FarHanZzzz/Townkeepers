"""AC-16 Advisor rejection and conflicting decisions (PRD Appendix B).

The race half of this scenario lives in tests/race/test_memo_races.py (two real connections).
"""

import pytest
from django.core import mail

from apps.memos.models import MemoDecision, MemoStatus
from apps.platform_core.exceptions import StaleRevisionError
from apps.platform_core.jobs import run_once
from apps.platform_core.models import Notification
from tests import memo_helpers as h


@pytest.mark.req("AC-16", "FR-MEM-08", "FR-COM-02", "UC-22", "UC-24")
@pytest.mark.django_db
def test_ac16_advisor_rejection_notifies_eb_not_head_and_blocks_later_confirmation(
    world, head, client, frozen_clock
):
    memo = h.ready_memo(world, head)
    h.send(world, memo)

    # The assigned Advisor rejects with a reason.
    h.decide(
        world.advisor_a,
        memo,
        "reject",
        reason="The proposed date clashes with exams.",
        confirm_reject=True,
    )
    run_once("ac16")

    # The EB receives the notice and IUB email.
    assert Notification.objects.filter(
        recipient=world.president_a, event_type="memo.rejected"
    ).exists()
    rejection_mail = [m for m in mail.outbox if "rejected" in m.subject]
    assert world.president_a.iub_email in {m.to[0] for m in rejection_mail}

    # The Head receives no rejection notice or email but sees the rejection in tracking.
    assert not Notification.objects.filter(recipient=head, event_type="memo.rejected").exists()
    assert head.iub_email not in {m.to[0] for m in rejection_mail}
    client.force_login(head)
    detail = client.get(f"/memos/{memo.pk}/").content.decode()
    assert "Rejected" in detail and "The proposed date clashes with exams." in detail

    # A later attempt to confirm the rejected version is denied.
    with pytest.raises(StaleRevisionError):
        from apps.memos import commands as mc
        from tests import factories as f

        mc.decide_memo(
            world.advisor_a,
            memo.pk,
            expected_version=1,
            expected_stage="advisor",
            decision="confirm",
            signature=h.signed(),
            operation_key=f.key(),
        )
    memo.refresh_from_db()
    assert memo.status == MemoStatus.REJECTED
    assert MemoDecision.objects.filter(version=memo.current_version).count() == 1

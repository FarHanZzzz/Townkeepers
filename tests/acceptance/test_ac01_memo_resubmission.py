"""AC-01 Digital memo and resubmission (PRD Appendix B)."""

import pytest
from django.core import mail

from apps.memos import commands as mc
from apps.memos.models import MemoStatus, MemoVersion
from apps.memos.selectors import dosa_queue
from apps.platform_core.jobs import run_once
from apps.platform_core.models import Notification
from tests import factories as f
from tests import memo_helpers as h


@pytest.mark.req(
    "AC-01",
    "FR-MEM-01",
    "FR-MEM-04",
    "FR-MEM-06",
    "FR-MEM-08",
    "FR-MEM-09",
    "UC-19",
    "UC-21",
    "UC-22",
    "UC-23",
)
@pytest.mark.django_db
def test_ac01_reject_with_email_then_signed_resubmission_keeps_both_versions(
    world, head, frozen_clock
):
    # An EB author opens an active template and sends an eligible memo with a proposed room, no booking.
    memo = h.ready_memo(world, head)
    assert memo.event.proposed_venue == "Department classroom"
    h.send(world, memo)
    memo.refresh_from_db()
    v1 = memo.current_version
    assert (
        v1.stage == MemoStatus.PENDING_ADVISOR and v1.snapshot["fields"]["subject"] == memo.subject
    )

    # The Advisor confirms with an e-signature; the Head rejects with a reason.
    h.decide(world.advisor_a, memo, "confirm")
    h.decide(head, memo, "reject", reason="State the expected headcount.", confirm_reject=True)
    rejected = Notification.objects.filter(event_type="memo.rejected")
    assert {n.recipient_id for n in rejected} >= {world.president_a.pk, world.advisor_a.pk}
    run_once("acceptance-worker")
    assert {m.to[0] for m in mail.outbox if "rejected" in m.subject} >= {
        world.president_a.iub_email,
        world.advisor_a.iub_email,
    }

    # The EB starts a linked revision; Advisor and Head sign the new version.
    mc.start_memo_revision(world.president_a, memo.pk, operation_key=f.key())
    h.fill(memo, world.president_a, body="Revised: 40 expected participants.")
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    h.decide(head, memo, "approve")
    memo.refresh_from_db()
    v2 = memo.current_version
    assert memo.status == MemoStatus.APPROVED and v2.number == 2

    # Both versions and their decisions remain traceable; signatures bind to their own version.
    v1 = MemoVersion.objects.get(pk=v1.pk)
    assert v1.stage == MemoStatus.REJECTED
    assert [d.decision for d in v1.decisions.all()] == ["confirm", "reject"]
    assert [d.decision for d in v2.decisions.all()] == ["confirm", "approve"]
    assert {s.version_id for s in v2.signatures.all()} == {v2.pk}
    assert all(s.content_sha256 == v2.content_sha256 for s in v2.signatures.all())


@pytest.mark.req("AC-01", "FR-MEM-07")
@pytest.mark.django_db
def test_ac01_with_department_head_the_head_queue_stays_empty_until_endorsed(
    world, head, frozen_clock
):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm", signers=[world.dept_head.pk])
    assert not dosa_queue().exists()
    h.decide(world.dept_head, memo, "endorse")
    assert dosa_queue().count() == 1

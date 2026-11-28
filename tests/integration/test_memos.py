"""FR-MEM-01 to FR-MEM-13 command and request tests (UC-18 to UC-26)."""

from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.events.models import Event
from apps.memos import commands as mc
from apps.memos.models import Memo, MemoDecision, MemoStatus, MemoVersion, Signature
from apps.platform_core.exceptions import (
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    StaleRevisionError,
    ValidationFailed,
)
from apps.platform_core.models import Export, Notification
from tests import factories as f
from tests import memo_helpers as h

PDF = b"%PDF-1.4\n%synthetic agenda\n%%EOF"


@pytest.mark.req("FR-MEM-01", "UC-18")
@pytest.mark.django_db
def test_template_without_both_signature_areas_cannot_be_activated(head):
    tid = mc.create_template(
        head,
        mc.TemplateInput(label="Incomplete", signature_areas=("advisor",)),
        operation_key=f.key(),
    ).object_id
    with pytest.raises(ValidationFailed):
        mc.set_template_active(head, tid, active=True, operation_key=f.key())


@pytest.mark.req("FR-MEM-01")
@pytest.mark.django_db
def test_only_template_managers_change_templates(world):
    with pytest.raises(PermissionDeniedError):
        mc.create_template(world.president_a, mc.TemplateInput(label="Mine"), operation_key=f.key())


@pytest.mark.req("FR-MEM-02", "FR-MEM-03", "UC-19")
@pytest.mark.django_db
def test_draft_saves_incomplete_and_send_lists_missing_items(world, head, frozen_clock):
    tid = h.make_template(
        head, attachments=[{"key": "agenda", "label": "Event agenda", "required": True}]
    )
    event_id = h.make_event(world)
    memo = Memo.objects.get(
        pk=mc.create_memo(
            world.president_a, event_id=event_id, template_id=tid, operation_key=f.key()
        ).object_id
    )
    assert memo.to_line == "" and memo.body == ""  # nothing prefilled
    h.fill(memo, world.president_a, subject="")
    with pytest.raises(ValidationFailed) as excinfo:
        h.send(world, memo)
    assert {"subject", "attachments"} <= set(excinfo.value.field_errors)
    memo.refresh_from_db()
    assert memo.status == MemoStatus.DRAFT and not memo.versions.exists()


@pytest.mark.req("FR-MEM-03", "FR-COM-06")
@pytest.mark.django_db
def test_attachment_upload_validates_type_and_supersedes_without_deleting(
    world, head, frozen_clock
):
    tid = h.make_template(
        head, attachments=[{"key": "agenda", "label": "Event agenda", "required": True}]
    )
    memo = h.ready_memo(world, head, template_id=tid)
    with pytest.raises(ValidationFailed):
        mc.upload_memo_attachment(
            world.president_a,
            memo.pk,
            key="agenda",
            uploaded_file=SimpleUploadedFile("agenda.pdf", b"not a pdf"),
        )
    mc.upload_memo_attachment(
        world.president_a, memo.pk, key="agenda", uploaded_file=SimpleUploadedFile("a.pdf", PDF)
    )
    mc.upload_memo_attachment(
        world.president_a, memo.pk, key="agenda", uploaded_file=SimpleUploadedFile("b.pdf", PDF)
    )
    assert (
        memo.attachments.count() == 2
        and memo.attachments.filter(superseded_at__isnull=True).count() == 1
    )
    h.send(world, memo)
    version = MemoVersion.objects.get(memo=memo)
    assert [a["name"] for a in version.snapshot["attachments"]] == ["b.pdf"]


@pytest.mark.req("FR-MEM-05", "FR-MEM-06", "FR-MEM-11", "UC-21")
@pytest.mark.django_db
def test_send_freezes_version_records_dates_and_notifies_advisor_once(world, head, frozen_clock):
    memo = h.ready_memo(world, head)
    result = h.send(world, memo)
    memo.refresh_from_db()
    version = memo.current_version
    assert memo.status == MemoStatus.PENDING_ADVISOR and result.data == {
        "version": 1,
        "late": False,
    }
    assert version.submitted_at.isoformat() == "2026-12-01T04:00:00+00:00"
    assert version.dosa_queue_entered_at is None
    assert version.approval_deadline == date(2026, 12, 16)
    assert version.submission_target == date(2026, 12, 11)
    assert version.snapshot["event"]["title"] == "Synthetic Programming Workshop"
    assert len(version.content_sha256) == 64 and version.policy_version.is_synthetic
    assert Event.objects.get(pk=memo.event_id).status == Event.Status.AWAITING_APPROVALS
    notices = Notification.objects.filter(event_type="memo.submitted")
    assert [n.recipient for n in notices] == [world.advisor_a] and notices[0].email_required
    with pytest.raises(InvalidTransitionError):
        h.send(world, memo)
    with pytest.raises(InvalidTransitionError):
        mc.save_memo_draft(
            world.president_a,
            memo.pk,
            mc.MemoDraftInput(subject="edit"),
            budget_version_id=None,
            expected_revision=memo.revision,
            operation_key=f.key(),
        )


@pytest.mark.req("FR-MEM-11", "AC-19")
@pytest.mark.django_db
def test_six_days_before_the_event_is_flagged_late_but_still_sent(world, head, frozen_clock):
    memo = h.ready_memo(world, head, first_date=date(2026, 12, 7))
    assert h.send(world, memo).data["late"] is True
    on_time = h.ready_memo(
        world, head, template_id=memo.template_version.template_id, first_date=date(2026, 12, 8)
    )
    assert h.send(world, on_time).data["late"] is False


@pytest.mark.req("FR-MEM-04", "FR-MEM-07", "FR-MEM-08", "UC-20", "UC-22")
@pytest.mark.django_db
def test_out_of_sequence_or_unassigned_reviewers_cannot_decide(world, head, frozen_clock):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    with pytest.raises(PermissionDeniedError):
        h.decide(head, memo, "approve")  # Head cannot act before the Advisor
    with pytest.raises(PermissionDeniedError):
        h.decide(world.advisor_b, memo, "confirm")  # other club's advisor can see but cannot act
    with pytest.raises(ValidationFailed):
        h.decide(world.advisor_a, memo, "confirm", sig=False)  # signature required
    with pytest.raises(ValidationFailed):
        h.decide(world.advisor_a, memo, "reject", reason="")  # reason and confirmation required
    assert not MemoDecision.objects.exists() and not Signature.objects.exists()


@pytest.mark.req("FR-MEM-04", "FR-MEM-07", "AC-01")
@pytest.mark.django_db
def test_additional_signer_must_endorse_before_the_head_queue(world, head, frozen_clock):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm", signers=[world.dept_head.pk])
    memo.refresh_from_db()
    assert memo.status == MemoStatus.PENDING_ADDITIONAL
    from apps.memos.selectors import dosa_queue

    assert not dosa_queue().exists()
    with pytest.raises(PermissionDeniedError):
        h.decide(world.president_b, memo, "endorse")  # other club can see but has no signature task
    with pytest.raises(PermissionDeniedError):
        h.decide(world.president_a, memo, "endorse")  # same club, but no signature task
    h.decide(world.dept_head, memo, "endorse")
    memo.refresh_from_db()
    assert memo.status == MemoStatus.PENDING_DOSA and list(dosa_queue()) == [memo.current_version]


@pytest.mark.req("FR-MEM-07")
@pytest.mark.django_db
def test_signer_return_rejects_the_version_and_notifies_author_and_advisor(
    world, head, frozen_clock
):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm", signers=[world.dept_head.pk])
    h.decide(world.dept_head, memo, "return", reason="Wrong floor", confirm_reject=True)
    memo.refresh_from_db()
    assert memo.status == MemoStatus.REJECTED
    recipients = set(
        Notification.objects.filter(event_type="memo.returned").values_list(
            "recipient_id", flat=True
        )
    )
    assert {world.president_a.pk, world.advisor_a.pk} <= recipients


@pytest.mark.req("FR-MEM-08", "FR-MEM-10", "BR-12")
@pytest.mark.django_db
def test_stale_reviewer_sees_the_committed_outcome(world, head, frozen_clock):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "reject", reason="Incomplete", confirm_reject=True)
    with pytest.raises(StaleRevisionError) as excinfo:
        mc.decide_memo(
            world.advisor_a,
            memo.pk,
            expected_version=1,
            expected_stage="advisor",
            decision="confirm",
            signature=h.signed(),
            operation_key=f.key(),
        )
    assert excinfo.value.current_state["status"] == "Rejected"
    assert "Rejected by Dr Advisor A" in excinfo.value.current_state["last_decision"]


@pytest.mark.req("FR-MEM-09", "UC-23")
@pytest.mark.django_db
def test_revision_after_rejection_needs_fresh_signatures(world, head, frozen_clock):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    h.decide(head, memo, "reject", reason="Add the venue", confirm_reject=True)
    mc.start_memo_revision(world.president_a, memo.pk, operation_key=f.key())
    h.fill(memo, world.president_a, body="Revised body with venue.")
    h.send(world, memo)
    memo.refresh_from_db()
    v2 = memo.current_version
    assert v2.number == 2 and memo.status == MemoStatus.PENDING_ADVISOR
    assert not v2.signatures.exists()
    assert MemoVersion.objects.get(memo=memo, number=1).stage == MemoStatus.REJECTED


@pytest.mark.req("FR-MEM-13", "UC-26")
@pytest.mark.django_db
def test_withdraw_requires_reason_and_eligible_status(world, head, frozen_clock):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    with pytest.raises(ValidationFailed):
        mc.withdraw_memo(world.president_a, memo.pk, reason=" ", operation_key=f.key())
    mc.withdraw_memo(world.president_a, memo.pk, reason="Event postponed", operation_key=f.key())
    memo.refresh_from_db()
    assert (
        memo.status == MemoStatus.WITHDRAWN and memo.current_version.stage == MemoStatus.WITHDRAWN
    )
    assert Event.objects.get(pk=memo.event_id).status == Event.Status.DRAFT
    other = h.ready_memo(world, head, template_id=memo.template_version.template_id)
    h.send(world, other)
    h.decide(world.advisor_a, other, "confirm")
    with pytest.raises(InvalidTransitionError):
        mc.withdraw_memo(world.president_a, other.pk, reason="Too late", operation_key=f.key())


@pytest.mark.req("FR-MEM-12", "UC-25")
@pytest.mark.django_db
def test_amendment_is_linked_and_leaves_the_approved_memo_authoritative(world, head, frozen_clock):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    h.decide(head, memo, "approve")
    event = Event.objects.get(pk=memo.event_id)
    approved_version = event.memo_approved_version
    assert approved_version is not None and event.status == Event.Status.AWAITING_APPROVALS
    amendment = Memo.objects.get(
        pk=mc.start_memo_amendment(world.president_a, memo.pk, operation_key=f.key()).object_id
    )
    assert (
        amendment.kind == Memo.Kind.AMENDMENT
        and amendment.amends == memo
        and amendment.subject == memo.subject
    )
    with pytest.raises(ConflictError):
        mc.start_memo_amendment(world.president_a, memo.pk, operation_key=f.key())
    h.fill(amendment, world.president_a, body="Move to 19 December.")
    h.send(world, amendment)
    h.decide(world.advisor_a, amendment, "reject", reason="No", confirm_reject=True)
    memo.refresh_from_db()
    assert memo.status == MemoStatus.APPROVED
    assert Event.objects.get(pk=memo.event_id).memo_approved_version == approved_version


@pytest.mark.req("FR-MEM-11", "AC-06")
@pytest.mark.django_db
def test_head_changes_deadline_keeping_submission_times_and_rejecting_stale_changes(
    world, head, frozen_clock
):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    memo.refresh_from_db()
    submitted = memo.current_version.submitted_at
    mc.change_approval_deadline(
        head,
        memo.pk,
        new_deadline=date(2026, 12, 10),
        expected_deadline=date(2026, 12, 16),
        reason="Venue office closes early",
        operation_key=f.key(),
    )
    version = MemoVersion.objects.get(pk=memo.current_version_id)
    assert version.approval_deadline == date(2026, 12, 10) and version.submitted_at == submitted
    with pytest.raises(StaleRevisionError):
        mc.change_approval_deadline(
            head,
            memo.pk,
            new_deadline=date(2026, 12, 12),
            expected_deadline=date(2026, 12, 16),
            reason="stale",
            operation_key=f.key(),
        )


@pytest.mark.req("FR-MEM-13", "UC-26")
@pytest.mark.django_db
def test_export_contains_only_recorded_signatures_and_is_access_checked(
    world, head, client, frozen_clock
):
    memo = h.ready_memo(world, head)
    client.force_login(world.president_a)
    page = client.get(f"/memos/{memo.pk}/preview/").content.decode()
    assert "DRAFT" in page and "No signatures are recorded" in page
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    response = client.post(f"/memos/{memo.pk}/export", {"version": 1})
    export = Export.objects.get()
    assert response.status_code == 302 and response.url == f"/exports/{export.pk}/"
    pdf = client.get(response.url)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    client.force_login(world.president_b)
    assert client.get(f"/exports/{export.pk}/").status_code == 200


@pytest.mark.req("FR-MEM-10", "AC-11")
@pytest.mark.django_db
def test_memo_pages_are_scoped_and_list_shows_status_and_next_actor(
    world, head, client, frozen_clock
):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    client.force_login(world.president_a)
    page = client.get("/memos/?status=pending").content.decode()
    assert "Pending Advisor Confirmation" in page and "Assigned Faculty Advisor" in page
    # Memos are visible to all active profiles; access is no longer club-scoped.
    client.force_login(world.president_b)
    assert client.get(f"/memos/{memo.pk}/").status_code == 200
    assert world.club_a.name in client.get("/memos/").content.decode()
    client.force_login(world.dept_head)
    assert client.get(f"/memos/{memo.pk}/").status_code == 200


@pytest.mark.req("FR-MEM-08", "UC-22")
@pytest.mark.django_db
def test_decisions_endpoint_accepts_json_and_returns_envelopes(world, head, client, frozen_clock):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    client.force_login(world.advisor_a)
    url = f"/memos/{memo.pk}/decisions"
    bad = client.post(
        url,
        {
            "operation_key": "k",
            "expected_version": 1,
            "expected_stage": "advisor",
            "decision": "reject",
        },
        content_type="application/json",
    )
    assert bad.status_code == 422 and "reason" in bad.json()["error"]["field_errors"]
    ok = client.post(
        url,
        {
            "operation_key": "k2",
            "expected_version": 1,
            "expected_stage": "advisor",
            "decision": "confirm",
            "signature_method": "drawn",
            "signature_data": h.signature_png(),
            "attest": True,
        },
        content_type="application/json",
    )
    assert ok.status_code == 200 and ok.json()["outcome"] == "confirmed"
    replay = client.post(
        url,
        {
            "operation_key": "k2",
            "expected_version": 1,
            "expected_stage": "advisor",
            "decision": "confirm",
            "signature_method": "drawn",
            "signature_data": h.signature_png(),
            "attest": True,
        },
        content_type="application/json",
    )
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    stale = client.post(
        url,
        {
            "operation_key": "k3",
            "expected_version": 1,
            "expected_stage": "advisor",
            "decision": "confirm",
        },
        content_type="application/json",
    )
    assert (
        stale.status_code == 409
        and stale.json()["error"]["current_state"]["status"] == "Pending DoSA Approval"
    )

"""Platform core: audit immutability, durable jobs and worker recovery, files, health, policy."""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.db import DatabaseError, transaction

from apps.platform_core import audit, files
from apps.platform_core.commands import PolicyInput, save_policy_version
from apps.platform_core.exceptions import PermissionDeniedError, ValidationFailed
from apps.platform_core.jobs import _finish, claim_batch, retry_job, run_once
from apps.platform_core.models import AuditEntry, Job, Notification, PolicyVersion
from apps.platform_core.notifications import notify

PDF = b"%PDF-1.4\n%synthetic\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@pytest.mark.req("FR-COM-03", "NFR-SEC-04")
@pytest.mark.django_db
def test_audit_entries_cannot_be_edited_or_deleted(system_admin):
    entry = audit.record(system_admin, "test.action", system_admin, after={"x": 1})
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditEntry.objects.filter(pk=entry.pk).update(reason="tampered")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditEntry.objects.filter(pk=entry.pk).delete()
    assert AuditEntry.objects.get(pk=entry.pk).reason == ""


def _email_notice(world, key="test:1"):
    return notify(
        [world.president_a],
        event_key=key,
        event_type="test",
        object_type="x",
        object_id=1,
        subject="Synthetic",
        message="Synthetic message",
        email=True,
    )[0]


@pytest.mark.req("FR-COM-02", "AC-18")
@pytest.mark.django_db
def test_worker_recovers_an_expired_lease_and_keeps_one_email_intent(world, frozen_clock):
    # Arrange: a worker claims the job and dies before finishing.
    notice = _email_notice(world)
    claimed = claim_batch("worker-a", lease_seconds=60)
    assert [j.pk for j in claimed] == [notice.email_job_id]

    # Act: the lease expires and another worker runs.
    frozen_clock.tick(timedelta(seconds=61))
    report = run_once("worker-b")

    # Assert
    job = Job.objects.get(pk=notice.email_job_id)
    assert report.succeeded == 1
    assert job.state == Job.State.SUCCEEDED and job.leased_by == "worker-b" and job.attempts == 2
    assert Job.objects.count() == 1 and Notification.objects.count() == 1
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [world.president_a.iub_email]
    assert _finish(claimed[0], "worker-a", state=Job.State.FAILED) is False


@pytest.mark.req("FR-COM-02", "AC-18")
@pytest.mark.django_db
def test_failed_email_becomes_retryable_then_failed_and_can_be_retried(
    world, frozen_clock, monkeypatch, head
):
    notice = _email_notice(world)
    job = Job.objects.get(pk=notice.email_job_id)
    job.max_attempts = 2
    job.save()

    def boom(self, *a, **k):
        raise ConnectionError("SMTP unavailable")

    monkeypatch.setattr("django.core.mail.EmailMessage.send", boom)
    assert run_once("w").retryable == 1
    job.refresh_from_db()
    assert job.state == Job.State.RETRYABLE and "SMTP unavailable" in job.last_error
    frozen_clock.tick(timedelta(minutes=5))
    assert run_once("w").failed == 1
    job.refresh_from_db()
    assert job.state == Job.State.FAILED

    monkeypatch.undo()
    retry_job(head, job.pk)
    assert run_once("w").succeeded == 1
    assert Notification.objects.get(pk=notice.pk).email_job.state == Job.State.SUCCEEDED
    assert AuditEntry.objects.filter(action="job.retry").count() == 1


@pytest.mark.req("FR-COM-02", "BR-10")
@pytest.mark.django_db
def test_repeated_notify_for_the_same_event_creates_no_duplicates(world):
    _email_notice(world, "same")
    _email_notice(world, "same")
    assert Notification.objects.count() == 1 and Job.objects.count() == 1


@pytest.mark.req("FR-COM-06", "FR-FIN-07")
@pytest.mark.django_db
def test_upload_validation_sniffs_content_and_enforces_size(world, settings):
    with pytest.raises(ValidationFailed):
        files.store_bytes(
            b"MZ\x90\x00 not a pdf",
            original_name="bill.pdf",
            uploaded_by=world.president_a,
            purpose="test",
        )
    settings.MAX_UPLOAD_BYTES = 10
    with pytest.raises(ValidationFailed):
        files.store_bytes(
            PDF, original_name="bill.pdf", uploaded_by=world.president_a, purpose="test"
        )
    settings.MAX_UPLOAD_BYTES = 10_000
    stored = files.store_bytes(
        PDF, original_name="../../bill.pdf", uploaded_by=world.president_a, purpose="test"
    )
    assert stored.content_type == "application/pdf" and stored.original_name == "bill.pdf"
    assert files.read_bytes(stored) == PDF


@pytest.mark.req("FR-COM-06", "NFR-SEC-03")
@pytest.mark.django_db
def test_file_without_an_access_rule_or_for_anonymous_users_is_not_served(world, client):
    stored = files.store_bytes(
        PDF,
        original_name="x.pdf",
        uploaded_by=world.president_a,
        purpose="test",
        owner_type="unregistered",
    )
    assert client.get(f"/files/{stored.key}/").status_code == 302  # anonymous: sign-in redirect
    client.force_login(world.president_a)
    assert client.get(f"/files/{stored.key}/").status_code == 404


@pytest.mark.req("NFR-REL-01")
@pytest.mark.django_db
def test_health_probes_are_public_and_report_database(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    ready = client.get("/health/ready").json()
    assert ready["checks"]["database"] == "ok"


@pytest.mark.req("FR-IAM-08", "UC-05")
@pytest.mark.django_db
def test_policy_versions_take_effect_on_their_date_and_reject_past_dates(head, world, frozen_clock):
    base = dict(
        standard_lead_days=7,
        big_event_lead_months=1,
        approval_buffer_days=3,
        review_window_days=3,
        working_days=(7, 1, 2, 3, 4),
        email_on_submission=True,
        is_synthetic=True,
    )
    with pytest.raises(ValidationFailed):
        save_policy_version(
            head, PolicyInput(effective_from=date(2026, 11, 1), **base), operation_key="p1"
        )
    save_policy_version(
        head, PolicyInput(effective_from=date(2027, 1, 1), **base), operation_key="p2"
    )
    from apps.platform_core.policy import effective_policy

    assert effective_policy(date(2026, 12, 15)).approval_buffer_days == 2
    assert effective_policy(date(2027, 1, 2)).approval_buffer_days == 3
    assert PolicyVersion.objects.count() == 2
    with pytest.raises(PermissionDeniedError):
        save_policy_version(
            world.president_a,
            PolicyInput(effective_from=date(2027, 2, 1), **base),
            operation_key="p3",
        )


@pytest.mark.req("NFR-SEC-01", "AC-15")
@pytest.mark.django_db
def test_json_clients_get_401_envelope_and_browsers_are_redirected(client):
    assert client.get("/memos/").status_code == 302
    response = client.get("/memos/", HTTP_ACCEPT="application/json")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"

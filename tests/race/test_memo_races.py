"""PostgreSQL race tests with independent connections at a controlled barrier (AGENTS.md section 4).

Each worker thread gets its own Django database connection. Both threads wait at a Barrier and
then call the command at the same moment; the committed state must allow exactly one outcome.
"""

from __future__ import annotations

import threading

import pytest
from django.db import connections

from apps.accounts.commands import ProfileInput, provision_profile
from apps.accounts.models import Profile
from apps.memos import commands as mc
from apps.memos.models import MemoDecision, MemoStatus, MemoVersion
from apps.platform_core.access import AccessCategory
from apps.platform_core.exceptions import DomainError
from apps.platform_core.models import CommandReceipt, Notification
from tests import factories as f
from tests import memo_helpers as h

pytestmark = [pytest.mark.race, pytest.mark.django_db(transaction=True)]


@pytest.fixture(autouse=True)
def _policy(initial_policy):
    """Transactional tests truncate tables, removing the migration-seeded synthetic policy."""


def race(*calls):
    """Run callables concurrently from a shared barrier; return (results, errors)."""
    barrier = threading.Barrier(len(calls))
    results, errors = [], []
    lock = threading.Lock()

    def run(fn):
        try:
            barrier.wait(timeout=10)
            value = fn()
            with lock:
                results.append(value)
        except DomainError as exc:
            with lock:
                errors.append(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=run, args=(fn,)) for fn in calls]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results, errors


@pytest.mark.req("AC-16", "FR-MEM-08", "FR-COM-04", "NFR-REL-03")
def test_simultaneous_head_approve_and_reject_commit_exactly_one_decision(world, head):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    memo.refresh_from_db()
    version = memo.current_version.number
    approve_sig = h.signed()

    def approve():
        return mc.decide_memo(
            head,
            memo.pk,
            expected_version=version,
            expected_stage="dosa",
            decision="approve",
            signature=approve_sig,
            operation_key=f.key(),
        )

    def reject():
        return mc.decide_memo(
            head,
            memo.pk,
            expected_version=version,
            expected_stage="dosa",
            decision="reject",
            reason="Conflicting tab",
            confirm_reject=True,
            operation_key=f.key(),
        )

    results, errors = race(approve, reject)
    assert len(results) == 1 and len(errors) == 1
    assert errors[0].code == "stale_revision"
    memo.refresh_from_db()
    assert memo.status in {MemoStatus.APPROVED, MemoStatus.REJECTED}
    assert MemoDecision.objects.filter(version__memo=memo, stage="dosa").count() == 1


@pytest.mark.req("FR-MEM-06", "AC-18", "BR-10")
def test_double_send_from_two_tabs_records_one_version_and_one_notice(world, head):
    memo = h.ready_memo(world, head)
    memo.refresh_from_db()
    rev = memo.revision

    def send():
        return mc.send_memo_to_advisor(
            world.president_a, memo.pk, expected_revision=rev, operation_key=f.key()
        )

    results, errors = race(send, send)
    assert len(results) == 1 and len(errors) == 1
    assert MemoVersion.objects.filter(memo=memo).count() == 1
    assert Notification.objects.filter(event_type="memo.submitted").count() == 1


@pytest.mark.req("FR-COM-04", "BR-10", "AC-18")
def test_same_operation_key_retried_concurrently_replays_one_outcome(world, head):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    memo.refresh_from_db()
    key = f.key()
    sig = h.signed()

    def confirm():
        return mc.decide_memo(
            world.advisor_a,
            memo.pk,
            expected_version=1,
            expected_stage="advisor",
            decision="confirm",
            signature=sig,
            operation_key=key,
        )

    results, errors = race(confirm, confirm)
    assert not errors and len(results) == 2
    assert sorted(r.replayed for r in results) == [False, True]
    assert MemoDecision.objects.filter(version__memo=memo).count() == 1
    assert CommandReceipt.objects.filter(key=key).count() == 1


@pytest.mark.req("FR-IAM-03", "BR-10")
def test_concurrent_provisioning_of_one_address_creates_one_profile(system_admin):
    def provision():
        return provision_profile(
            system_admin,
            ProfileInput("race@iub-synthetic.test", "Race Person", AccessCategory.EB_MEMBER),
            grants=None,
            operation_key=f.key(),
        )

    results, errors = race(provision, provision)
    assert len(results) == 1 and len(errors) == 1
    assert Profile.objects.filter(iub_email="race@iub-synthetic.test").count() == 1

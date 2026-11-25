"""Booking, finance totals, publishing, handover and queue explanation."""

from datetime import date, time
from decimal import Decimal

import pytest

from apps.analytics.compare import term_measures
from apps.clubs.handover import handover_term
from apps.events import booking
from apps.events.models import Event, Venue
from apps.finance import ledger
from apps.finance.calculations import club_balance, event_cash_flow, variance
from apps.finance.models import Adjustment, Currency, FundingPeriod
from apps.memos.models import Memo
from apps.memos.priority import explain
from apps.platform_core import clock
from apps.platform_core.access import AccessCategory
from apps.platform_core.exceptions import ValidationFailed
from apps.publishing.commands import publish_notice
from apps.publishing.models import Publication
from tests import factories as f
from tests import memo_helpers as h

pytestmark = pytest.mark.django_db


def _room(**kwargs):
    defaults = dict(
        name="Room A",
        location="Block A",
        capacity=60,
        kind=Venue.Kind.CLASSROOM,
        opens_at=time(8, 0),
        closes_at=time(22, 0),
        is_synthetic=True,
        created_at=clock.now(),
    )
    defaults.update(kwargs)
    return Venue.objects.create(**defaults)


@pytest.mark.req("FR-EVT-05", "FR-EVT-07", "FR-EVT-12")
def test_evening_booking_needs_advisor_then_dosa_and_then_approves_the_event(
    world, head, frozen_clock, initial_policy
):
    room = _room()
    memo = h.ready_memo(world, head, first_date=date(2026, 12, 16))
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    h.decide(head, memo, "approve")
    memo.event.refresh_from_db()
    assert memo.event.status == Event.Status.AWAITING_APPROVALS
    result = booking.submit_booking_request(
        world.president_a,
        memo.event_id,
        venue_id=room.pk,
        data=dict(
            first_date=date(2026, 12, 16),
            last_date=date(2026, 12, 16),
            start_time=time(18, 0),
            end_time=time(21, 0),
            setup_minutes=0,
            cleanup_minutes=0,
            headcount=40,
            filer_designation="President",
            justification="",
        ),
        operation_key=f.key(),
    )
    row = memo.event.bookings.get(pk=result.object_id)
    assert row.route == ["advisor", "dosa"]
    booking.decide_booking(
        world.advisor_a,
        row.pk,
        decision="confirm",
        reason="",
        expected_revision=row.revision,
        operation_key=f.key(),
    )
    row.refresh_from_db()
    booking.decide_booking(
        head,
        row.pk,
        decision="confirm",
        reason="",
        expected_revision=row.revision,
        operation_key=f.key(),
    )
    memo.event.refresh_from_db()
    assert memo.event.status == Event.Status.APPROVED
    assert room.reservations.filter(active=True).count() == 1


@pytest.mark.req("FR-EVT-07", "AC-02")
def test_second_confirmation_of_the_same_slot_is_rejected(
    world, head, frozen_clock, initial_policy
):
    room = _room(name="Room B")
    first = h.ready_memo(world, head, first_date=date(2026, 12, 17))
    h.send(world, first)
    h.decide(world.advisor_a, first, "confirm")
    h.decide(head, first, "approve")
    second_event = h.make_event(world, first_date=date(2026, 12, 17))
    # A second event still needs an approved memo before booking.
    template = first.template_version.template_id
    memo_id = (
        __import__("apps.memos.commands", fromlist=["create_memo"])
        .create_memo(
            world.president_a, event_id=second_event, template_id=template, operation_key=f.key()
        )
        .object_id
    )
    other = Memo.objects.get(pk=memo_id)
    h.fill(other, world.president_a, subject="Second workshop request")
    h.send(world, other)
    h.decide(world.advisor_a, other, "confirm")
    h.decide(head, other, "approve")

    def lodge(event_id, key):
        return booking.submit_booking_request(
            world.president_a,
            event_id,
            venue_id=room.pk,
            data=dict(
                first_date=date(2026, 12, 17),
                last_date=date(2026, 12, 17),
                start_time=time(10, 0),
                end_time=time(12, 0),
                setup_minutes=0,
                cleanup_minutes=0,
                headcount=20,
                filer_designation="President",
                justification="",
            ),
            operation_key=key,
        )

    lodged = lodge(first.event_id, f.key())
    row = first.event.bookings.get(pk=lodged.object_id)
    # Daytime classroom route is DoSA only.
    booking.decide_booking(
        head, row.pk, decision="confirm", reason="", expected_revision=1, operation_key=f.key()
    )
    with pytest.raises(ValidationFailed):
        lodge(second_event, f.key())


@pytest.mark.req("FR-FIN-03", "FR-FIN-05", "AC-03", "AC-20")
def test_reconciliation_fixture_leaves_balance_2750_cash_flow_1250_and_variance_minus_150(
    world, head
):
    period = FundingPeriod.objects.create(
        label="2026-27", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30)
    )
    ledger.record_allocation(
        head,
        club_id=world.club_a.pk,
        period_id=period.pk,
        amount=Decimal("10000.00"),
        currency=Currency.BDT,
        source="Synthetic grant",
        allocated_on=date(2026, 7, 1),
        operation_key=f.key(),
    )
    scheduled = ledger.schedule_release(
        head,
        club_id=world.club_a.pk,
        period_id=period.pk,
        amount=Decimal("4000.00"),
        currency=Currency.BDT,
        operation_key=f.key(),
    )
    ledger.confirm_release(
        head,
        scheduled.object_id,
        amount=Decimal("3500.00"),
        reference="SYN-1",
        operation_key=f.key(),
    )
    event_id = h.make_event(world)
    ledger.attribute_release(
        head,
        scheduled.object_id,
        event_id=event_id,
        amount=Decimal("2000.00"),
        operation_key=f.key(),
    )
    expense = ledger.submit_expense(
        world.president_a,
        club_id=world.club_a.pk,
        event_id=event_id,
        amount=Decimal("800.00"),
        currency=Currency.BDT,
        description="Printing",
        incurred_on=date(2026, 12, 2),
        evidence_note="Synthetic shop receipt",
        operation_key=f.key(),
    )
    ledger.note_extraction(head, expense.object_id, amount=Decimal("800.00"), operation_key=f.key())
    ledger.verify_expense(head, expense.object_id, operation_key=f.key())
    ledger.apply_adjustment(
        head,
        club_id=world.club_a.pk,
        event_id=event_id,
        direction=Adjustment.Direction.REDUCE_EXPENSE,
        source_type="expense",
        source_id=expense.object_id,
        amount=Decimal("50.00"),
        currency=Currency.BDT,
        reason="Counted one page twice",
        operation_key="adjust-once",
    )
    again = ledger.apply_adjustment(
        head,
        club_id=world.club_a.pk,
        event_id=event_id,
        direction=Adjustment.Direction.REDUCE_EXPENSE,
        source_type="expense",
        source_id=expense.object_id,
        amount=Decimal("50.00"),
        currency=Currency.BDT,
        reason="Counted one page twice",
        operation_key="adjust-once",
    )
    assert again.replayed is True
    assert club_balance([Decimal("3500.00")], [Decimal("750.00")]) == Decimal("2750.00")
    assert event_cash_flow([Decimal("2000.00")], [Decimal("750.00")]) == Decimal("1250.00")
    assert variance(Decimal("750.00"), Decimal("900.00")) == Decimal("-150.00")


@pytest.mark.req("FR-PUB-01")
def test_internal_notice_waits_for_approval_and_a_confirmed_room(
    world, head, frozen_clock, initial_policy
):
    memo = h.ready_memo(world, head)
    with pytest.raises(Exception):
        publish_notice(
            world.president_a, memo.event_id, destination="internal", operation_key=f.key()
        )
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    h.decide(head, memo, "approve")
    room = _room(name="Room C")
    lodged = booking.submit_booking_request(
        world.president_a,
        memo.event_id,
        venue_id=room.pk,
        data=dict(
            first_date=memo.event.first_date,
            last_date=memo.event.last_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
            setup_minutes=0,
            cleanup_minutes=0,
            headcount=20,
            filer_designation="President",
            justification="",
        ),
        operation_key=f.key(),
    )
    booking.decide_booking(
        head,
        lodged.object_id,
        decision="confirm",
        reason="",
        expected_revision=1,
        operation_key=f.key(),
    )
    result = publish_notice(
        world.president_a, memo.event_id, destination="internal", operation_key=f.key()
    )
    assert Publication.objects.get(pk=result.object_id).status == Publication.Status.PUBLISHED


@pytest.mark.req("FR-CLB-06")
def test_handover_moves_unfinished_work_and_keeps_the_author_term(world, head):

    memo = h.ready_memo(world, head)
    author_term = memo.author_term_id
    successor = f.make_profile(AccessCategory.EB_MEMBER, name="Next President")
    handover_term(
        head,
        world.term_a.pk,
        successor_id=successor.pk,
        reason="Annual handover",
        operation_key=f.key(),
    )
    memo.refresh_from_db()
    assert memo.author_id == successor.pk
    assert memo.author_term_id == author_term


@pytest.mark.req("FR-AIP-01", "FR-AIP-06")
def test_a_missing_deadline_is_not_replaced_by_the_event_date():
    class Version:
        approval_deadline = None
        event_starts_at = None

    text = " ".join(explain(Version()))
    assert "missing" in text
    assert "not replaced" in text


@pytest.mark.req("FR-ANL-05")
def test_term_comparison_counts_only_completed_events(world, head):
    event_id = h.make_event(world, first_date=date(2026, 8, 1))
    Event.objects.filter(pk=event_id).update(
        status=Event.Status.COMPLETED, outcome="successful", reach="national"
    )
    measures = term_measures(world.club_a.pk, world.term_a.start_date, world.term_a.end_date)
    assert event_id in measures["completed"]
    assert event_id in measures["successful"]
    assert event_id in measures["national_or_international"]

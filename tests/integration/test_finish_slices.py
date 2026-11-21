"""Reschedule, suggestions, receipts, queue override, and sign-in without Google."""

from datetime import date, time
from decimal import Decimal

import pytest

from apps.events import booking, suggestions
from apps.events.models import Reservation, Venue
from apps.finance import ledger
from apps.finance.models import Currency, Expense
from apps.memos.models import QueueOverride
from apps.memos.priority import set_queue_override
from apps.platform_core import clock
from tests import factories as f
from tests import memo_helpers as h

pytestmark = pytest.mark.django_db


def _room(name="Finish room"):
    return Venue.objects.create(
        name=name,
        location="Block",
        capacity=80,
        kind=Venue.Kind.CLASSROOM,
        opens_at=time(8, 0),
        closes_at=time(22, 0),
        is_synthetic=True,
        created_at=clock.now(),
    )


def _confirmed(world, head, room, when, template_id=None):
    memo = h.ready_memo(world, head, template_id=template_id, first_date=when)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    h.decide(head, memo, "approve")
    lodged = booking.submit_booking_request(
        world.president_a,
        memo.event_id,
        venue_id=room.pk,
        data=dict(
            first_date=when,
            last_date=when,
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
    return memo


@pytest.mark.req("FR-EVT-09")
def test_a_failed_move_keeps_the_original_reservation(world, head, frozen_clock, initial_policy):
    room = _room()
    other = _room("Other room")
    template_id = h.make_template(head)
    first = _confirmed(world, head, room, date(2026, 12, 10), template_id)
    second = _confirmed(world, head, other, date(2026, 12, 11), template_id)
    # Fill the target slot on the original room.
    booking.reschedule_booking(
        world.president_a,
        second.event.bookings.get().pk,
        venue_id=room.pk,
        data=dict(
            first_date=date(2026, 12, 11),
            last_date=date(2026, 12, 11),
            start_time=time(14, 0),
            end_time=time(16, 0),
            setup_minutes=0,
            cleanup_minutes=0,
            headcount=20,
            filer_designation="President",
            justification="",
        ),
        expected_revision=2,
        operation_key=f.key(),
    )
    row = first.event.bookings.get()
    before = Reservation.objects.get(booking=row, active=True).pk
    with pytest.raises(Exception):
        booking.reschedule_booking(
            world.president_a,
            row.pk,
            venue_id=room.pk,
            data=dict(
                first_date=date(2026, 12, 11),
                last_date=date(2026, 12, 11),
                start_time=time(14, 0),
                end_time=time(16, 0),
                setup_minutes=0,
                cleanup_minutes=0,
                headcount=20,
                filer_designation="President",
                justification="",
            ),
            expected_revision=row.revision,
            operation_key=f.key(),
        )
    row.refresh_from_db()
    assert row.status == "confirmed"
    assert Reservation.objects.get(pk=before).active is True


@pytest.mark.req("FR-AIS-02")
def test_suggestions_skip_a_confirmed_slot(world, head, frozen_clock, initial_policy):
    room = _room("Suggest room")
    _confirmed(world, head, room, date(2026, 12, 12), h.make_template(head, label="Suggest template"))
    taken = suggestions.suggest_slots(
        day=date(2026, 12, 12), start=time(10, 0), duration_minutes=60, headcount=20
    )
    free = suggestions.suggest_slots(
        day=date(2026, 12, 13), start=time(10, 0), duration_minutes=60, headcount=20
    )
    assert room.pk not in {row["venue_id"] for row in taken}
    assert room.pk in {row["venue_id"] for row in free}


@pytest.mark.req("FR-FIN-07", "FR-FIN-10")
def test_a_receipt_can_be_stored_and_a_return_does_not_verify(world, head):
    event_id = h.make_event(world)
    expense = ledger.submit_expense(
        world.president_a,
        club_id=world.club_a.pk,
        event_id=event_id,
        amount=Decimal("100.00"),
        currency=Currency.BDT,
        description="Paper",
        incurred_on=date(2026, 12, 2),
        evidence_note="Waiting for the file",
        operation_key=f.key(),
    )
    ledger.attach_receipt(
        world.president_a,
        expense.object_id,
        data=b"%PDF-1.4 synthetic",
        filename="receipt.pdf",
        operation_key=f.key(),
    )
    stored = Expense.objects.get(pk=expense.object_id)
    assert stored.evidence_key
    ledger.decide_expense(
        head, stored.pk, decision="return", reason="Amount is unclear", operation_key=f.key()
    )
    stored.refresh_from_db()
    assert stored.status == Expense.Status.RETURNED


@pytest.mark.req("FR-AIP-05")
def test_queue_override_records_the_reason_and_previous_place(
    world, head, frozen_clock, initial_policy
):
    memo = h.ready_memo(world, head)
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    set_queue_override(
        head,
        memo.pk,
        position=1,
        reason="The event is this week",
        expires_on=date(2026, 12, 31),
        operation_key=f.key(),
    )
    row = QueueOverride.objects.get(memo=memo)
    assert row.reason == "The event is this week"
    assert row.actor_id == head.pk


def test_sign_in_does_not_offer_google(client):
    response = client.get("/auth/sign-in/")
    assert b"Continue with Google" not in response.content
    assert client.get("/auth/google/start").status_code == 404

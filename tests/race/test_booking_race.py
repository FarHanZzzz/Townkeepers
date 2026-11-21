"""Two confirmations of one room at one time leave a single reservation (AC-02, FR-EVT-07)."""

import pytest

from apps.events.models import Reservation
from apps.platform_core.exceptions import DomainError
from tests.race.test_memo_races import race

pytestmark = [pytest.mark.race, pytest.mark.django_db(transaction=True)]


@pytest.fixture(autouse=True)
def _policy(initial_policy):
    """Transactional tests drop the migration-seeded policy."""


@pytest.mark.req("AC-02", "FR-EVT-07")
def test_two_confirmations_of_one_slot_leave_one_reservation(world, head, frozen_clock):
    from datetime import date, time

    from apps.events import booking
    from apps.events.models import Venue
    from apps.platform_core import clock
    from tests import factories as f
    from tests import memo_helpers as h

    room = Venue.objects.create(
        name="Race room",
        location="Block",
        capacity=80,
        kind=Venue.Kind.CLASSROOM,
        opens_at=time(8, 0),
        closes_at=time(22, 0),
        is_synthetic=True,
        created_at=clock.now(),
    )
    template_id = h.make_template(head, label="Race template")
    bookings = []
    for day in (date(2026, 12, 14), date(2026, 12, 15)):
        memo = h.ready_memo(world, head, template_id=template_id, first_date=day)
        h.send(world, memo)
        h.decide(world.advisor_a, memo, "confirm")
        h.decide(head, memo, "approve")
        lodged = booking.submit_booking_request(
            world.president_a,
            memo.event_id,
            venue_id=room.pk,
            data=dict(
                first_date=date(2026, 12, 14),
                last_date=date(2026, 12, 14),
                start_time=time(15, 0),
                end_time=time(17, 0),
                setup_minutes=0,
                cleanup_minutes=0,
                headcount=20,
                filer_designation="President",
                justification="",
            ),
            operation_key=f.key(),
        )
        bookings.append(lodged.object_id)

    def confirm(booking_id):
        return booking.decide_booking(
            head, booking_id, decision="confirm", reason="", expected_revision=1, operation_key=f.key()
        )

    results, errors = race(lambda: confirm(bookings[0]), lambda: confirm(bookings[1]))
    assert len(results) + len(errors) == 2
    assert Reservation.objects.filter(venue=room, active=True).count() == 1
    assert any(isinstance(error, DomainError) for error in errors) or len(results) == 1

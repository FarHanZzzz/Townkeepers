"""FR-EVT-01/02 (draft path) and FR-FIN-04 (budget versions, Advisor review)."""

from datetime import date, time
from decimal import Decimal

import pytest

from apps.events.commands import EventInput, create_event, save_event_draft
from apps.events.models import Event
from apps.finance.commands import BudgetLineInput, review_budget_request, save_budget_version
from apps.finance.models import BudgetRequestReview, BudgetVersion
from apps.platform_core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    StaleRevisionError,
    ValidationFailed,
)
from apps.platform_core.models import Notification
from tests import factories as f


def workshop(**overrides) -> EventInput:
    data = dict(
        title="Synthetic Programming Workshop",
        event_type="workshop",
        first_date=date(2026, 12, 18),
        last_date=date(2026, 12, 18),
        start_time=time(18),
        end_time=time(21),
        proposed_venue="Department classroom",
        expected_headcount=40,
    )
    data.update(overrides)
    return EventInput(**data)


@pytest.mark.req("FR-EVT-01", "UC-27")
@pytest.mark.django_db
def test_eb_creates_a_draft_event_for_own_club_only(world, frozen_clock):
    result = create_event(
        world.president_a, club_id=world.club_a.pk, data=workshop(), operation_key=f.key()
    )
    event = Event.objects.get(pk=result.object_id)
    assert event.status == Event.Status.DRAFT and event.organizer == world.president_a
    assert event.starts_at.isoformat() == "2026-12-18T18:00:00+06:00"
    with pytest.raises(NotFoundError):
        create_event(
            world.president_a, club_id=world.club_b.pk, data=workshop(), operation_key=f.key()
        )


@pytest.mark.req("FR-EVT-01")
@pytest.mark.django_db
def test_invalid_times_and_dates_block_creation(world):
    with pytest.raises(ValidationFailed) as excinfo:
        create_event(
            world.president_a,
            club_id=world.club_a.pk,
            data=workshop(end_time=time(18), last_date=date(2026, 12, 17)),
            operation_key=f.key(),
        )
    assert {"end_time", "last_date"} <= set(excinfo.value.field_errors)


@pytest.mark.req("FR-EVT-01")
@pytest.mark.django_db
def test_only_the_head_creates_central_events(world, head):
    create_event(
        head, club_id=None, data=workshop(title="Central orientation"), operation_key=f.key()
    )
    with pytest.raises(PermissionDeniedError):
        create_event(world.president_a, club_id=None, data=workshop(), operation_key=f.key())


@pytest.mark.req("FR-EVT-02", "FR-COM-08")
@pytest.mark.django_db
def test_stale_draft_save_keeps_the_newer_version(world):
    event_id = create_event(
        world.president_a, club_id=world.club_a.pk, data=workshop(), operation_key=f.key()
    ).object_id
    save_event_draft(
        world.treasurer_a,
        event_id,
        data=workshop(title="Newer"),
        expected_revision=1,
        operation_key=f.key(),
    )
    with pytest.raises(StaleRevisionError):
        save_event_draft(
            world.president_a,
            event_id,
            data=workshop(title="Older"),
            expected_revision=1,
            operation_key=f.key(),
        )
    assert Event.objects.get(pk=event_id).title == "Newer"


def _lines():
    return [
        BudgetLineInput("Refreshments", Decimal("3000.00")),
        BudgetLineInput("Printing", Decimal("500.50")),
    ]


@pytest.mark.req("FR-FIN-04", "UC-11", "AC-03")
@pytest.mark.django_db
def test_budget_revisions_keep_earlier_versions_and_identify_changed_lines(world):
    event_id = create_event(
        world.president_a, club_id=world.club_a.pk, data=workshop(), operation_key=f.key()
    ).object_id
    save_budget_version(
        world.treasurer_a,
        event_id,
        lines=_lines(),
        requested_amount=Decimal("25000"),
        requested_currency="BDT",
        purpose="Workshop costs",
        expected_version_number=0,
        operation_key=f.key(),
    )
    save_budget_version(
        world.treasurer_a,
        event_id,
        lines=[
            BudgetLineInput("Refreshments", Decimal("3500.00")),
            BudgetLineInput("Printing", Decimal("500.50")),
        ],
        requested_amount=Decimal("25000"),
        requested_currency="BDT",
        purpose="Workshop costs",
        expected_version_number=1,
        operation_key=f.key(),
    )
    v1, v2 = BudgetVersion.objects.order_by("number")
    assert v1.lines.get(description="Refreshments").planned_amount == Decimal("3000.00")
    assert v2.changed_lines == ["Refreshments"]
    with pytest.raises(StaleRevisionError):
        save_budget_version(
            world.treasurer_a,
            event_id,
            lines=_lines(),
            requested_amount=None,
            requested_currency="BDT",
            purpose="",
            expected_version_number=1,
            operation_key=f.key(),
        )


@pytest.mark.req("FR-FIN-04")
@pytest.mark.django_db
def test_invalid_amounts_and_other_club_events_are_rejected(world):
    event_id = create_event(
        world.president_b, club_id=world.club_b.pk, data=workshop(), operation_key=f.key()
    ).object_id
    with pytest.raises(NotFoundError):
        save_budget_version(
            world.treasurer_a,
            event_id,
            lines=_lines(),
            requested_amount=None,
            requested_currency="BDT",
            purpose="",
            expected_version_number=0,
            operation_key=f.key(),
        )
    own = create_event(
        world.president_a, club_id=world.club_a.pk, data=workshop(), operation_key=f.key()
    ).object_id
    with pytest.raises(ValidationFailed):
        save_budget_version(
            world.treasurer_a,
            own,
            lines=[BudgetLineInput("Bad", Decimal("-1"))],
            requested_amount=Decimal("0"),
            requested_currency="BDT",
            purpose="x",
            expected_version_number=0,
            operation_key=f.key(),
        )


@pytest.mark.req("FR-FIN-04", "AC-03", "BR-05")
@pytest.mark.django_db
def test_advisor_endorses_requested_amount_without_creating_allocation_or_release(world):
    event_id = create_event(
        world.president_a, club_id=world.club_a.pk, data=workshop(), operation_key=f.key()
    ).object_id
    vid = save_budget_version(
        world.treasurer_a,
        event_id,
        lines=_lines(),
        requested_amount=Decimal("25000"),
        requested_currency="BDT",
        purpose="Workshop",
        expected_version_number=0,
        operation_key=f.key(),
    ).object_id
    with pytest.raises(PermissionDeniedError):
        review_budget_request(world.president_a, vid, endorse=True, operation_key=f.key())
    with pytest.raises(NotFoundError):
        review_budget_request(world.advisor_b, vid, endorse=True, operation_key=f.key())
    review_budget_request(world.advisor_a, vid, endorse=True, operation_key=f.key())
    assert BudgetRequestReview.objects.get(version_id=vid).decision == "endorsed"
    assert Notification.objects.filter(
        recipient=world.treasurer_a, event_type="budget.reviewed"
    ).exists()
    with pytest.raises(ConflictError):
        review_budget_request(
            world.advisor_a, vid, endorse=False, reason="again", operation_key=f.key()
        )
    from apps.finance.models import Allocation, FundRelease

    assert Allocation.objects.count() == 0
    assert FundRelease.objects.count() == 0


@pytest.mark.req("FR-FIN-04")
@pytest.mark.django_db
def test_returning_a_request_requires_feedback(world):
    event_id = create_event(
        world.president_a, club_id=world.club_a.pk, data=workshop(), operation_key=f.key()
    ).object_id
    vid = save_budget_version(
        world.treasurer_a,
        event_id,
        lines=_lines(),
        requested_amount=Decimal("100"),
        requested_currency="USD",
        purpose="Prizes",
        expected_version_number=0,
        operation_key=f.key(),
    ).object_id
    with pytest.raises(ValidationFailed):
        review_budget_request(
            world.advisor_a, vid, endorse=False, reason=" ", operation_key=f.key()
        )

"""Finance forms, booking move, receipt reading, external notice, and CSV import."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.analytics.importing import import_events_csv
from apps.analytics.models import HistoricalImport
from apps.events.models import Event
from apps.finance.calculations import club_balance
from apps.finance.models import Expense, FundRelease
from apps.platform_core.exceptions import ValidationFailed
from apps.publishing.commands import publish_notice
from apps.publishing.models import Publication
from tests import factories as f

pytestmark = pytest.mark.django_db


@pytest.mark.req("FR-FIN-01", "FR-FIN-02", "FR-FIN-03", "AC-03", "AC-20")
def test_finance_forms_keep_the_worked_balance(world, head, client):
    client.force_login(head)
    assert (
        client.post(
            "/finance/record/",
            {
                "action": "period",
                "label": "Form 2026-27",
                "start_date": "2026-07-01",
                "end_date": "2027-06-30",
            },
        ).status_code
        == 302
    )
    period = client.get("/finance/").context["periods"].get(label="Form 2026-27")
    client.post(
        "/finance/record/",
        {
            "action": "allocation",
            "club": world.club_a.pk,
            "period": period.pk,
            "amount": "10000.00",
            "currency": "BDT",
            "source": "Synthetic grant",
            "allocated_on": "2026-07-01",
        },
    )
    client.post(
        "/finance/record/",
        {
            "action": "schedule",
            "club": world.club_a.pk,
            "period": period.pk,
            "amount": "4000.00",
            "currency": "BDT",
        },
    )
    release = FundRelease.objects.get(club=world.club_a, status="scheduled")
    client.post(
        "/finance/record/",
        {
            "action": "confirm",
            "release": release.pk,
            "amount": "3500.00",
            "reference": "SYN-FORM",
        },
    )
    page = client.get("/finance/")
    row = next(item for item in page.context["rows"] if item["club"].pk == world.club_a.pk)
    assert row["balance"] == Decimal("3500.00")
    client.post(
        "/finance/record/",
        {
            "action": "schedule",
            "club": world.club_a.pk,
            "period": period.pk,
            "amount": "100.00",
            "currency": "BDT",
        },
    )
    cancelled = FundRelease.objects.get(club=world.club_a, status="scheduled")
    client.post(
        "/finance/record/",
        {"action": "cancel", "release": cancelled.pk, "reason": "Not required"},
    )
    denied = client.post(
        "/finance/record/",
        {"action": "confirm", "release": cancelled.pk, "amount": "100.00", "reference": "NO"},
        follow=True,
    )
    assert b"cancelled release cannot be marked released" in denied.content
    client.post(
        "/finance/record/",
        {
            "action": "conversion",
            "from_currency": "USD",
            "to_currency": "BDT",
            "rate": "120.00",
            "recorded_on": "2026-12-01",
            "note": "Synthetic rate",
        },
    )
    assert club_balance([Decimal("3500.00")], [Decimal("750.00")]) == Decimal("2750.00")


@pytest.mark.req("FR-EVT-09")
def test_move_form_reports_a_taken_time(world, head, client, frozen_clock, initial_policy):
    from datetime import time

    from apps.events import booking
    from apps.events.models import Venue
    from apps.platform_core import clock
    from tests import memo_helpers as h

    room = Venue.objects.create(
        name="Move room",
        location="Block",
        capacity=80,
        kind=Venue.Kind.CLASSROOM,
        opens_at=time(8, 0),
        closes_at=time(22, 0),
        is_synthetic=True,
        created_at=clock.now(),
    )
    other = Venue.objects.create(
        name="Move other",
        location="Block",
        capacity=80,
        kind=Venue.Kind.CLASSROOM,
        opens_at=time(8, 0),
        closes_at=time(22, 0),
        is_synthetic=True,
        created_at=clock.now(),
    )
    template_id = h.make_template(head, label="Move form template")

    def confirm(when, venue):
        memo = h.ready_memo(world, head, template_id=template_id, first_date=when)
        h.send(world, memo)
        h.decide(world.advisor_a, memo, "confirm")
        h.decide(head, memo, "approve")
        lodged = booking.submit_booking_request(
            world.president_a,
            memo.event_id,
            venue_id=venue.pk,
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
        return memo.event.bookings.get()

    taken = confirm(date(2026, 12, 10), room)
    mover = confirm(date(2026, 12, 11), other)
    client.force_login(world.president_a)
    response = client.post(
        f"/events/bookings/{mover.pk}/move/",
        {
            "venue": room.pk,
            "first_date": "2026-12-10",
            "last_date": "2026-12-10",
            "start_time": "10:00",
            "end_time": "12:00",
            "setup_minutes": "0",
            "cleanup_minutes": "0",
            "headcount": "20",
            "revision": mover.revision,
            "operation_key": f.key(),
        },
        follow=True,
    )
    assert b"original reservation is unchanged" in response.content
    mover.refresh_from_db()
    taken.refresh_from_db()
    assert mover.venue_id == other.pk
    assert taken.venue_id == room.pk


@pytest.mark.req("FR-FIN-07", "FR-FIN-10")
def test_uploaded_receipt_stays_unverified_until_a_person_returns_it(world, head, client):
    from tests import memo_helpers as h

    event_id = h.make_event(world)
    from apps.finance import ledger

    expense = ledger.submit_expense(
        world.president_a,
        club_id=world.club_a.pk,
        event_id=event_id,
        amount=Decimal("100.00"),
        currency="BDT",
        description="Paper",
        incurred_on=date(2026, 12, 2),
        evidence_note="Shop receipt",
        operation_key=f.key(),
    )
    client.force_login(world.president_a)
    upload = SimpleUploadedFile(
        "receipt.pdf", b"%PDF-1.4\namount:100.00\n", content_type="application/pdf"
    )
    client.post(f"/finance/expenses/{expense.object_id}/receipt/", {"receipt": upload})
    stored = Expense.objects.get(pk=expense.object_id)
    assert stored.status == Expense.Status.SUBMITTED
    assert stored.extraction_state == "unverified"
    client.force_login(head)
    client.post(
        f"/finance/expenses/{stored.pk}/decide/",
        {"decision": "return", "reason": "The figure is unclear"},
    )
    stored.refresh_from_db()
    assert stored.status == Expense.Status.RETURNED
    assert club_balance([], [stored.amount]) != club_balance([], [])
    verified = Expense.objects.filter(club=world.club_a, status=Expense.Status.VERIFIED)
    assert stored.pk not in set(verified.values_list("pk", flat=True))


@pytest.mark.req("FR-PUB-04")
def test_external_notice_fails_without_a_site_and_a_timeout_leaves_the_internal_notice(
    world, head, frozen_clock, initial_policy, settings
):
    from datetime import time

    from apps.events import booking
    from apps.events.models import Venue
    from apps.platform_core import clock
    from tests import memo_helpers as h

    room = Venue.objects.create(
        name="Notice room",
        location="Block",
        capacity=80,
        kind=Venue.Kind.CLASSROOM,
        opens_at=time(8, 0),
        closes_at=time(22, 0),
        is_synthetic=True,
        created_at=clock.now(),
    )
    memo = h.ready_memo(world, head, template_id=h.make_template(head, label="Notice template"))
    h.send(world, memo)
    h.decide(world.advisor_a, memo, "confirm")
    h.decide(head, memo, "approve")
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
    internal = publish_notice(
        world.president_a, memo.event_id, destination="internal", operation_key=f.key()
    )
    settings.EXTERNAL_PUBLISH_URL = ""
    settings.EXTERNAL_PUBLISH_SENDER = None
    failed = publish_notice(
        world.president_a, memo.event_id, destination="external", operation_key=f.key()
    )
    assert (
        Publication.objects.get(pk=failed.object_id).detail == "No external website is configured."
    )
    assert Publication.objects.get(pk=internal.object_id).status == Publication.Status.PUBLISHED

    def boom(_payload):
        raise TimeoutError

    settings.EXTERNAL_PUBLISH_SENDER = boom
    timed = publish_notice(head, memo.event_id, destination="external", operation_key=f.key())
    assert Publication.objects.get(pk=timed.object_id).detail == "The external website timed out."
    assert Publication.objects.get(pk=internal.object_id).status == Publication.Status.PUBLISHED

    seen = {}

    def accept(payload):
        seen.update(payload)

    settings.EXTERNAL_PUBLISH_SENDER = accept
    sent = publish_notice(
        head, memo.event_id, destination="external", operation_key=f"ext-{f.key()}"
    )
    assert Publication.objects.get(pk=sent.object_id).status == Publication.Status.PUBLISHED
    assert seen["title"] == memo.event.title
    assert "body" not in seen and "receipt" not in seen


@pytest.mark.req("FR-COM-07", "FR-ANL-05")
def test_a_bad_csv_row_imports_nothing_and_a_draft_is_not_completed(world, head):
    good = (
        "club_code,title,first_date,status\n"
        f"{world.club_a.short_code},Imported fair,2026-08-01,completed\n"
        f"{world.club_a.short_code},Imported draft,2026-08-02,draft\n"
    )
    bad = good + f"{world.club_a.short_code},Broken,not-a-date,completed\n"
    with pytest.raises(ValidationFailed):
        import_events_csv(head, filename="bad.csv", text=bad)
    assert Event.objects.filter(title="Imported fair").count() == 0
    import_events_csv(head, filename="history.csv", text=good)
    assert HistoricalImport.objects.get(source="history.csv").row_count == 2
    assert Event.objects.get(title="Imported fair").status == Event.Status.COMPLETED
    assert Event.objects.get(title="Imported draft").status == Event.Status.DRAFT
    from apps.analytics.compare import term_measures

    measures = term_measures(world.club_a.pk, world.term_a.start_date, world.term_a.end_date)
    titles = set(Event.objects.filter(pk__in=measures["completed"]).values_list("title", flat=True))
    assert "Imported fair" in titles
    assert "Imported draft" not in titles

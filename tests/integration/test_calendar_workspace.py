"""Calendar workspace: shared heat rule, day detail and venue availability (FR-EVT-03, FR-EVT-10)."""

from __future__ import annotations

from datetime import date, time

import pytest

from apps.events import desk_calendar
from apps.events.models import Event, Venue
from apps.platform_core import clock


def _event(actor, club, title, first, last=None, proposed_venue=""):
    """A synthetic event on one or more campus-local days."""
    now = clock.now()
    return Event.objects.create(
        club=club,
        title=title,
        event_type="workshop",
        organizer=actor,
        created_by=actor,
        first_date=first,
        last_date=last or first,
        start_time=time(18, 0),
        end_time=time(21, 0),
        proposed_venue=proposed_venue,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.req("FR-EVT-10")
def test_heat_rule_marks_three_events_busy_and_four_packed():
    """0-2 events are free, exactly 3 is busy, and 4 or more is packed."""
    assert [desk_calendar.heat_level(n) for n in (0, 1, 2, 3, 4, 9)] == [
        "green",
        "green",
        "green",
        "orange",
        "red",
        "red",
    ]


@pytest.mark.req("FR-EVT-10")
@pytest.mark.django_db
def test_month_heatmap_counts_every_day_of_a_multi_day_event(world, head, client):
    """A two-day event appears on both days and a selected day lists its events."""
    client.force_login(head)
    for number in range(3):
        _event(
            head, world.club_a, f"Workshop {number}", date(2026, 12, 12), proposed_venue="Room A"
        )
    _event(head, world.club_b, "Two-day forum", date(2026, 12, 11), date(2026, 12, 12))

    response = client.get("/events/calendar/?start=2026-12-01")
    assert response.status_code == 200
    cells = {cell["key"]: cell for cell in response.context["cells"] if cell}
    assert cells["2026-12-11"]["count"] == 1
    assert cells["2026-12-11"]["level"] == "green"
    assert cells["2026-12-12"]["count"] == 4
    assert cells["2026-12-12"]["level"] == "red"
    assert cells["2026-12-13"]["count"] == 0
    assert "cal-day-red" in response.content.decode()

    detail = client.get("/events/calendar/?start=2026-12-01&date=2026-12-12")
    assert detail.status_code == 200
    assert detail.context["selected_label"] == "Saturday, 12 December 2026"
    assert len(detail.context["selected_events"]) == 4
    assert "Two-day forum" in detail.content.decode()


@pytest.mark.req("FR-EVT-10")
@pytest.mark.django_db
def test_calendar_json_uses_the_same_heat_level_as_the_page(world, head, client):
    """The modal cannot disagree with the full-page calendar about a busy day."""
    client.force_login(head)
    for number in range(3):
        _event(head, world.club_a, f"Workshop {number}", date(2026, 12, 12))
    _event(head, world.club_b, "Forum", date(2026, 12, 13))

    page = client.get("/events/calendar/?start=2026-12-01")
    payload = client.get("/events/calendar-data/?year=2026&month=12").json()
    assert payload["year"] == 2026
    assert payload["month"] == 12
    assert payload["first_day"] == "2026-12-01"
    assert payload["last_day"] == "2026-12-31"

    page_cells = {cell["key"]: cell for cell in page.context["cells"] if cell}
    for key in ("2026-12-12", "2026-12-13", "2026-12-14"):
        assert payload["days"][key]["count"] == page_cells[key]["count"]
        assert payload["days"][key]["level"] == page_cells[key]["level"]
    assert payload["days"]["2026-12-12"]["level"] == "orange"
    assert len(payload["days"]["2026-12-12"]["events"]) == 3
    assert "2026-11-30" not in payload["days"]


@pytest.mark.req("FR-EVT-03", "FR-EVT-10")
@pytest.mark.django_db
def test_venue_availability_json_filters_by_capacity_and_hours(world, head, client):
    """The booking popup sees only rooms that fit, inside their operating hours."""
    client.force_login(head)
    now = clock.now()
    Venue.objects.create(
        name="Synthetic classroom",
        location="Block A",
        capacity=60,
        kind=Venue.Kind.CLASSROOM,
        opens_at=time(9, 0),
        closes_at=time(22, 0),
        is_synthetic=True,
        created_at=now,
    )
    Venue.objects.create(
        name="Synthetic hall",
        location="Block B",
        capacity=400,
        kind=Venue.Kind.LARGE_HALL,
        opens_at=time(9, 0),
        closes_at=time(17, 0),
        is_synthetic=True,
        created_at=now,
    )

    url = "/events/venue-availability/?date=2026-12-16&start=18:00&end=21:00"
    response = client.get(url)
    assert response.status_code == 200
    rows = {row["name"]: row for row in response.json()["venues"]}
    assert rows["Synthetic classroom"]["status"] == "free"
    assert rows["Synthetic hall"]["status"] == "unavailable"

    limited = client.get(url + "&capacity=100")
    assert [row["name"] for row in limited.json()["venues"]] == ["Synthetic hall"]
    assert limited.json()["venues"][0]["status"] == "unavailable"
    assert client.get(url + "&capacity=500").json()["venues"] == []


@pytest.mark.req("FR-EVT-10")
@pytest.mark.django_db
def test_calendar_json_endpoints_deny_anonymous_json_clients(client):
    """Both JSON feeds use the same access rule as the calendar page."""
    for url in (
        "/events/calendar-data/?year=2026&month=12",
        "/events/venue-availability/?date=2026-12-16",
    ):
        assert client.get(url, HTTP_ACCEPT="application/json").status_code == 401

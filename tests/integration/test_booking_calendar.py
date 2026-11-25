"""Smoke tests for the deepened booking, venue, and calendar screens (FR-EVT-03, FR-EVT-04, FR-EVT-10)."""

import pytest


@pytest.mark.req("FR-EVT-03", "FR-EVT-04", "FR-EVT-10")
@pytest.mark.django_db
def test_booking_calendar_and_venue_screens_render(world, head, client):
    client.force_login(head)
    urls = [
        "/events/venues/",
        "/events/venues/new/",
        "/events/availability/",
        "/events/calendar/",
        "/events/suggestions/",
    ]
    for url in urls:
        assert client.get(url).status_code == 200, url
    # availability search returns a result set
    response = client.get(
        "/events/availability/?date=2026-12-16&start=18:00&end=21:00&capacity=10&use=classroom"
    )
    assert response.status_code == 200
    # calendar filters render
    response = client.get("/events/calendar/?view=list&status=approved")
    assert response.status_code == 200

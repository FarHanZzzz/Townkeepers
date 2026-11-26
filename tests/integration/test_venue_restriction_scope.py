"""Restricted hours are DoSA-only in the command, the POST view and the screen (FR-EVT-03)."""

from __future__ import annotations

from datetime import time

import pytest

from apps.events import booking
from apps.events.models import VenueRestriction
from apps.platform_core.exceptions import PermissionDeniedError
from tests import factories as f


def _restriction(actor):
    return booking.add_restriction(
        actor,
        venue_id=None,
        weekday=1,
        local_start=time(18, 0),
        local_end=time(21, 0),
        reason="Synthetic closure",
        operation_key=f.key(),
    )


@pytest.mark.req("FR-EVT-03")
@pytest.mark.django_db
def test_dosa_can_record_a_restriction(world):
    _restriction(world.head)
    assert VenueRestriction.objects.count() == 1


@pytest.mark.req("FR-EVT-03")
@pytest.mark.django_db
@pytest.mark.parametrize("persona", ["admin", "president_a", "advisor_a"])
def test_no_other_persona_can_record_a_restriction(world, persona):
    with pytest.raises(PermissionDeniedError):
        _restriction(getattr(world, persona))
    assert VenueRestriction.objects.count() == 0


@pytest.mark.req("FR-EVT-03")
@pytest.mark.django_db
@pytest.mark.parametrize("persona", ["admin", "president_a"])
def test_no_other_persona_can_post_the_restriction_form(world, client, persona):
    client.force_login(getattr(world, persona))
    response = client.post(
        "/events/venues/restrict/",
        {"weekday": "1", "local_start": "18:00", "local_end": "21:00", "reason": "Synthetic"},
    )
    assert response.status_code == 403
    assert VenueRestriction.objects.count() == 0


@pytest.mark.req("FR-EVT-03")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "persona,visible", [("head", True), ("admin", False), ("president_a", False)]
)
def test_restriction_form_is_rendered_only_for_dosa(world, client, persona, visible):
    client.force_login(getattr(world, persona))
    assert ("Restricted hours" in client.get("/events/venues/").content.decode()) is visible


@pytest.mark.req("FR-EVT-03")
@pytest.mark.django_db
@pytest.mark.parametrize("persona", ["admin", "president_a"])
def test_no_other_persona_reaches_the_venues_page(world, client, persona):
    client.force_login(getattr(world, persona))
    assert client.get("/events/venues/").status_code == 403

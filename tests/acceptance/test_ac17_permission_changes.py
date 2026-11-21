"""AC-17 Permission and profile changes (PRD Appendix B)."""

from datetime import date

import pytest

from apps.accounts.commands import decide_profile_change, request_profile_change
from apps.accounts.models import ProfileChangeRequest
from apps.clubs.commands import end_assignment
from apps.clubs.models import Assignment
from apps.events.commands import EventInput, create_event
from apps.platform_core.models import AuditEntry
from tests import factories as f


@pytest.mark.req("AC-17", "FR-IAM-04", "FR-IAM-05", "FR-COM-03", "UC-03")
@pytest.mark.django_db
def test_ac17_corrections_role_routing_and_ended_assignment_links(
    world, client, head, frozen_clock
):
    from datetime import time

    # An approved ordinary profile correction applies once and is audited.
    req_id = request_profile_change(
        world.treasurer_a,
        field="emergency_phone",
        proposed_value="01700-000000",
        operation_key=f.key(),
    ).object_id
    decide_profile_change(head, req_id, approve=True, operation_key=f.key())
    world.treasurer_a.refresh_from_db()
    assert world.treasurer_a.emergency_phone == "01700-000000"
    assert (
        AuditEntry.objects.filter(
            action="profile.update", object_id=str(world.treasurer_a.pk)
        ).count()
        == 1
    )

    # A role-change request must go through an authorized account administrator.
    role_req = request_profile_change(
        world.treasurer_a,
        field="access_category",
        proposed_value="dosa_head",
        operation_key=f.key(),
    ).object_id
    assert (
        ProfileChangeRequest.objects.get(pk=role_req).route == ProfileChangeRequest.Route.PROTECTED
    )

    # Historic work stays attributed; a previously opened link is denied once the assignment ends.
    event_id = create_event(
        world.treasurer_a,
        club_id=world.club_a.pk,
        data=EventInput(
            title="Synthetic Workshop",
            event_type="workshop",
            first_date=date(2026, 12, 18),
            last_date=date(2026, 12, 18),
            start_time=time(18),
            end_time=time(21),
        ),
        operation_key=f.key(),
    ).object_id
    client.force_login(world.treasurer_a)
    assert client.get(f"/events/{event_id}/").status_code == 200
    assignment = Assignment.objects.get(profile=world.treasurer_a, term=world.term_a)
    end_assignment(
        head, assignment.pk, end_date=date(2026, 11, 30), reason="Resigned", operation_key=f.key()
    )
    assert client.get(f"/events/{event_id}/").status_code == 404
    assert client.get(f"/finance/events/{event_id}/budget/").status_code == 404

    from apps.events.models import Event

    event = Event.objects.get(pk=event_id)
    assert event.organizer == world.treasurer_a and event.created_by == world.treasurer_a

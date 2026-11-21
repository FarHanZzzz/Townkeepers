"""Every primary page renders for the role that uses it (NFR-USE-01 empty states, FR-IAM-06)."""

from decimal import Decimal

import pytest

from apps.accounts.commands import request_profile_change
from apps.finance.commands import BudgetLineInput, save_budget_version
from apps.memos.models import MemoTemplate
from tests import factories as f
from tests import memo_helpers as h


@pytest.mark.req("FR-IAM-06", "NFR-USE-01")
@pytest.mark.django_db
def test_primary_pages_render_for_their_roles(world, head, system_admin, client, frozen_clock):
    memo = h.ready_memo(world, head)
    event_id = memo.event_id
    save_budget_version(
        world.treasurer_a,
        event_id,
        lines=[BudgetLineInput("Snacks", Decimal("100"))],
        requested_amount=Decimal("100"),
        requested_currency="BDT",
        purpose="Snacks",
        expected_version_number=0,
        operation_key=f.key(),
    )
    req = request_profile_change(
        world.president_a, field="full_name", proposed_value="Ayesha R.", operation_key=f.key()
    )
    template = MemoTemplate.objects.get()

    eb_pages = [
        "/",
        "/profile/",
        "/profile/requests/full_name/",
        "/notifications/",
        "/memos/",
        "/memos/new/",
        f"/memos/{memo.pk}/",
        f"/memos/{memo.pk}/edit/",
        f"/memos/{memo.pk}/preview/",
        "/events/",
        "/events/new/",
        f"/events/{event_id}/",
        f"/events/{event_id}/edit/",
        f"/finance/events/{event_id}/budget/",
        "/clubs/",
        f"/clubs/{world.club_a.pk}/",
        f"/clubs/{world.club_a.pk}/profile/",
        "/clubs/archive/",
    ]
    client.force_login(world.president_a)
    for url in eb_pages:
        assert client.get(url).status_code == 200, url

    h.send(world, memo)
    client.force_login(world.advisor_a)
    for url in ["/", f"/memos/{memo.pk}/review/", f"/finance/events/{event_id}/budget/"]:
        response = client.get(url)
        assert response.status_code == 200, url
    assert "Confirm and send" in client.get(f"/memos/{memo.pk}/review/").content.decode()

    client.force_login(head)
    for url in [
        "/",
        "/accounts/",
        "/accounts/new/",
        f"/accounts/{world.president_a.pk}/",
        "/accounts/profile-requests/",
        f"/accounts/profile-requests/{req.object_id}/",
        "/deliveries/",
        "/settings/policy/",
        "/memos/templates/",
        "/memos/templates/new/",
        f"/memos/templates/{template.pk}/",
        "/clubs/new/",
        f"/clubs/{world.club_a.pk}/identity/",
        f"/clubs/{world.club_a.pk}/terms/new/",
        f"/clubs/{world.club_a.pk}/advisors/new/",
        f"/clubs/terms/{world.term_a.pk}/appoint/",
        "/events/new/",
    ]:
        assert client.get(url).status_code == 200, url

    client.force_login(system_admin)
    for url in ["/", "/accounts/", "/accounts/profile-requests/", "/deliveries/"]:
        assert client.get(url).status_code == 200, url

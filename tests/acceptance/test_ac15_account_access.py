"""AC-15 Account access and role dashboard (PRD Appendix B)."""

import pytest

from apps.accounts.commands import ProfileInput, provision_profile
from apps.accounts.models import Profile
from apps.clubs import commands as clubs
from apps.platform_core.access import AccessCategory
from tests import factories as f


def _sign_in(client, email, sub):
    profile = Profile.objects.get(iub_email=email)
    client.force_login(profile)
    return client.get("/")


@pytest.mark.req(
    "AC-15", "FR-IAM-01", "FR-IAM-02", "FR-IAM-03", "FR-IAM-06", "UC-01", "UC-02", "UC-04"
)
@pytest.mark.django_db
def test_ac15_provisioned_users_sign_in_and_see_only_their_modules(
    system_admin, client, frozen_clock
):
    # A System Admin provisions the DoSA Head.
    head_id = provision_profile(
        system_admin,
        ProfileInput("head@iub-synthetic.test", "Synthetic Head", AccessCategory.DOSA_HEAD),
        grants=None,
        operation_key=f.key(),
    ).object_id
    head = Profile.objects.get(pk=head_id)
    # Authorized staff provision an EB member and a Faculty Advisor, then assign them.
    eb_id = provision_profile(
        head,
        ProfileInput(
            "eb@iub-synthetic.test",
            "Synthetic EB",
            AccessCategory.EB_MEMBER,
            designation="President",
        ),
        grants=None,
        operation_key=f.key(),
    ).object_id
    fa_id = provision_profile(
        head,
        ProfileInput("fa@iub-synthetic.test", "Synthetic Advisor", AccessCategory.FACULTY_ADVISOR),
        grants=None,
        operation_key=f.key(),
    ).object_id
    club_a = clubs.register_club(
        head, name="Club A", short_code="CA", operation_key=f.key()
    ).object_id
    club_b = clubs.register_club(
        head, name="Club B", short_code="CB", operation_key=f.key()
    ).object_id
    from datetime import date

    term = clubs.create_term(
        head,
        club_a,
        label="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        operation_key=f.key(),
    ).object_id
    clubs.activate_term(head, term, operation_key=f.key())
    clubs.appoint_member(
        head,
        term,
        profile_id=eb_id,
        designation="President",
        start_date=date(2026, 12, 1),
        operation_key=f.key(),
    )
    clubs.assign_advisor(
        head, club_a, profile_id=fa_id, start_date=date(2026, 12, 1), operation_key=f.key()
    )

    # A provisioned user signs in through IUB Google and sees the appropriate modules.
    assert _sign_in(client, "eb@iub-synthetic.test", "g-eb").status_code == 200
    page = client.get("/").content.decode()
    assert "Memo Management" in page and "Accounts" not in page
    assert client.get(f"/clubs/{club_a}/").status_code == 200
    assert client.get(f"/clubs/{club_b}/").status_code == 404  # only active club assignments
    client.post("/auth/sign-out/")

    assert _sign_in(client, "fa@iub-synthetic.test", "g-fa").status_code == 200
    assert "Memos awaiting your confirmation" in client.get("/").content.decode()
    assert client.get(f"/clubs/{club_b}/").status_code == 404
    client.post("/auth/sign-out/")

    assert client.get("/auth/google/start").status_code == 404
    Profile.objects.filter(pk=fa_id).update(is_active=False)
    assert _sign_in(client, "fa@iub-synthetic.test", "g-fa").status_code == 302

    # An anonymous calendar (events) request is denied.
    assert client.get("/events/").status_code == 302
    assert client.get("/events/", HTTP_ACCEPT="application/json").status_code == 401

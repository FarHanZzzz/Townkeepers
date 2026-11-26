"""Only the DoSA persona sees the administrative navigation links (FR-IAM-06)."""

import pytest

DOSA_ONLY = {
    "Dashboard",
    "Venues",
    "Reports",
    "Clubs",
    "Profile requests",
}
SHARED_WITH_FINANCE_SCOPE = {
    "Finance",
}


@pytest.mark.req("FR-IAM-06")
@pytest.mark.django_db
def test_dosa_persona_sees_the_administrative_links(world, head, client):
    client.force_login(head)
    labels = {label for label, _ in client.get("/").context["nav_items"]}
    assert labels >= DOSA_ONLY
    assert "Finance" in labels


@pytest.mark.req("FR-IAM-06")
@pytest.mark.django_db
@pytest.mark.parametrize("persona", ["admin", "president_a", "advisor_a"])
def test_other_personas_do_not_see_the_administrative_links(world, client, persona):
    client.force_login(getattr(world, persona))
    labels = {label for label, _ in client.get("/").context["nav_items"]}
    assert not (labels & DOSA_ONLY)

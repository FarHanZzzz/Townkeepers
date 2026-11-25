"""Smoke tests for the deepened finance overview screens (FR-FIN-06, FR-FIN-10, FR-FIN-13)."""

import pytest


@pytest.mark.req("FR-FIN-06", "FR-FIN-10", "FR-FIN-13")
@pytest.mark.django_db
def test_finance_overview_renders(world, head, client):
    client.force_login(head)
    assert client.get("/finance/").status_code == 200
    assert client.get("/finance/reconciliation/").status_code == 200

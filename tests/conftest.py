"""Shared fixtures: controllable clock, private temp storage, synthetic two-club world."""

from __future__ import annotations

from datetime import date

import pytest
from freezegun import freeze_time

from apps.platform_core.access import AccessCategory
from tests import factories as f


@pytest.fixture(autouse=True)
def private_storage(tmp_path, settings):
    """Each test writes private files to its own temporary directory."""
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "private"
    return settings.PRIVATE_MEDIA_ROOT


@pytest.fixture
def frozen_clock():
    """Freeze time at 1 Dec 2026 10:00 Asia/Dhaka (04:00 UTC); tick with ``frozen_clock.tick``."""
    with freeze_time("2026-12-01 04:00:00", tz_offset=0) as frozen:
        yield frozen


@pytest.fixture
def initial_policy(db):
    """Recreate the migration-seeded synthetic policy, which transactional tests truncate."""
    from datetime import UTC, datetime

    from apps.platform_core.models import PolicyVersion

    if not PolicyVersion.objects.exists():
        PolicyVersion.objects.create(
            effective_from=date(2000, 1, 1),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            working_days=[7, 1, 2, 3, 4],
            is_synthetic=True,
        )


@pytest.fixture
def system_admin(db):
    return f.make_profile(AccessCategory.SYSTEM_ADMIN, name="Synthetic System Admin")


@pytest.fixture
def head(db, system_admin):
    return f.make_profile(
        AccessCategory.DOSA_HEAD, name="Synthetic DoSA Head", created_by=system_admin
    )


@pytest.fixture
def world(db, system_admin, head):
    """Two clubs, active terms, EB members, advisors and a department-head signer."""

    class World:
        pass

    w = World()
    w.admin = system_admin
    w.head = head
    w.club_a = f.make_club("Synthetic Programming Club", "SPC")
    w.club_b = f.make_club("Synthetic Science Club", "SSC")
    w.term_a = f.make_term(w.club_a, head)
    w.term_b = f.make_term(w.club_b, head)
    w.president_a = f.make_profile(AccessCategory.EB_MEMBER, name="Ayesha President")
    w.treasurer_a = f.make_profile(AccessCategory.EB_MEMBER, name="Tanvir Treasurer")
    w.president_b = f.make_profile(AccessCategory.EB_MEMBER, name="Bilal President")
    f.assign_eb(w.president_a, w.term_a, head, "President")
    f.assign_eb(w.treasurer_a, w.term_a, head, "Treasurer")
    f.assign_eb(w.president_b, w.term_b, head, "President")
    w.advisor_a = f.make_profile(AccessCategory.FACULTY_ADVISOR, name="Dr Advisor A")
    w.advisor_b = f.make_profile(AccessCategory.FACULTY_ADVISOR, name="Dr Advisor B")
    f.assign_advisor(w.advisor_a, w.club_a, head)
    f.assign_advisor(w.advisor_b, w.club_b, head)
    w.dept_head = f.make_profile(AccessCategory.SIGNER, name="Prof Department Head")
    w.dept_head.designation = "Head, Department of CSE"
    w.dept_head.save(update_fields=["designation"])
    w.today = date(2026, 12, 1)
    return w

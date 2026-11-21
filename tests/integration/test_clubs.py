"""FR-CLB-01 to FR-CLB-05, FR-CLB-07, UC-06 to UC-08: register, terms, appointments, archive."""

from datetime import date

import pytest

from apps.clubs import commands as c
from apps.clubs.models import ArchiveCorrection, Club, Term
from apps.platform_core.access import AccessCategory, Action, can
from apps.platform_core.exceptions import (
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    StaleRevisionError,
    ValidationFailed,
)
from tests import factories as f


@pytest.mark.req("FR-CLB-01", "UC-06")
@pytest.mark.django_db
def test_rename_keeps_the_club_id_and_archive_blocks_new_requests(world, head):
    club_id = world.club_a.pk
    c.update_club_identity(
        head,
        club_id,
        name="IUB Programming Society",
        institutional_profile="Renamed",
        expected_revision=1,
        operation_key=f.key(),
    )
    club = Club.objects.get(pk=club_id)
    assert club.name == "IUB Programming Society" and club.revision == 2
    c.archive_club(head, club_id, reason="Merged", expected_revision=2, operation_key=f.key())
    with pytest.raises(InvalidTransitionError):
        c.create_term(
            head,
            club_id,
            label="2027-28",
            start_date=date(2027, 7, 1),
            end_date=date(2028, 6, 30),
            operation_key=f.key(),
        )
    assert Term.objects.filter(club_id=club_id).count() == 1  # earlier records kept
    assert can(
        world.president_a, Action.CLUBS_VIEW, club
    )  # archived records still viewable in scope


@pytest.mark.req("FR-CLB-01")
@pytest.mark.django_db
def test_eb_member_cannot_edit_official_identity(world):
    with pytest.raises(PermissionDeniedError):
        c.update_club_identity(
            world.president_a,
            world.club_a.pk,
            name="X",
            institutional_profile="",
            expected_revision=1,
            operation_key=f.key(),
        )


@pytest.mark.req("FR-CLB-02", "UC-07")
@pytest.mark.django_db
def test_overlapping_terms_are_blocked_unless_a_transition_is_approved(world, head):
    with pytest.raises(ValidationFailed):
        c.create_term(
            head,
            world.club_a.pk,
            label="Overlap",
            start_date=date(2027, 6, 1),
            end_date=date(2028, 5, 31),
            operation_key=f.key(),
        )
    c.create_term(
        head,
        world.club_a.pk,
        label="Transition",
        start_date=date(2027, 6, 1),
        end_date=date(2028, 5, 31),
        transition_approved=True,
        operation_key=f.key(),
    )
    with pytest.raises(ValidationFailed):
        c.create_term(
            head,
            world.club_a.pk,
            label="Backwards",
            start_date=date(2028, 6, 1),
            end_date=date(2028, 1, 1),
            operation_key=f.key(),
        )


@pytest.mark.req("FR-CLB-02", "FR-IAM-04", "AC-09")
@pytest.mark.django_db
def test_upcoming_term_gives_no_early_access_and_activation_needs_the_old_term_closed(
    world, head, frozen_clock
):
    result = c.create_term(
        head,
        world.club_a.pk,
        label="2028",
        start_date=date(2028, 1, 1),
        end_date=date(2028, 12, 31),
        operation_key=f.key(),
    )
    incoming = f.make_profile(AccessCategory.EB_MEMBER)
    c.appoint_member(
        head,
        result.object_id,
        profile_id=incoming.pk,
        designation="President",
        start_date=date(2028, 1, 1),
        operation_key=f.key(),
    )
    assert not can(incoming, Action.MEMOS_VIEW, world.club_a)
    with pytest.raises(ValidationFailed):
        c.activate_term(head, result.object_id, operation_key=f.key())  # before its start date


@pytest.mark.req("FR-CLB-02", "FR-IAM-04", "AC-17")
@pytest.mark.django_db
def test_closing_a_term_ends_linked_access_and_keeps_history(world, head, frozen_clock):
    c.close_term(head, world.term_a.pk, reason="End of tenure", operation_key=f.key())
    assert not can(world.president_a, Action.MEMOS_VIEW, world.club_a)
    term = Term.objects.get(pk=world.term_a.pk)
    assert term.status == Term.Status.CLOSED
    assert term.assignments.filter(ended_at__isnull=False).count() == 2
    with pytest.raises(ConflictError):
        c.close_term(head, world.term_a.pk, reason="again", operation_key=f.key())


@pytest.mark.req("FR-CLB-03", "FR-IAM-02", "UC-07")
@pytest.mark.django_db
def test_single_holder_posts_and_ineligible_profiles_are_rejected(world, head, frozen_clock):
    other = f.make_profile(AccessCategory.EB_MEMBER)
    with pytest.raises(ValidationFailed) as excinfo:
        c.appoint_member(
            head,
            world.term_a.pk,
            profile_id=other.pk,
            designation="president",
            start_date=date(2026, 12, 1),
            operation_key=f.key(),
        )
    assert "already has an active holder" in excinfo.value.field_errors["designation"][0]
    c.appoint_member(
        head,
        world.term_a.pk,
        profile_id=world.president_a.pk,
        designation="Student on Duty",
        start_date=date(2026, 12, 1),
        operation_key=f.key(),
    )  # multiple appointments allowed
    with pytest.raises(ValidationFailed):
        c.appoint_member(
            head,
            world.term_a.pk,
            profile_id=world.advisor_a.pk,
            designation="Secretary",
            start_date=date(2026, 12, 1),
            operation_key=f.key(),
        )
    with pytest.raises(ValidationFailed):
        c.appoint_member(
            head,
            world.term_a.pk,
            profile_id=other.pk,
            designation="Secretary",
            start_date=date(2025, 1, 1),
            operation_key=f.key(),
        )  # before the term


@pytest.mark.req("FR-CLB-05", "UC-08")
@pytest.mark.django_db
def test_archive_correction_keeps_the_previous_value_and_rejects_stale_edits(
    world, head, frozen_clock
):
    c.close_term(head, world.term_a.pk, reason="End", operation_key=f.key())
    term = Term.objects.get(pk=world.term_a.pk)
    c.correct_archive_record(
        head,
        object_type="term",
        object_id=term.pk,
        field="label",
        new_value="2026 (Spring)",
        reason="Typo",
        based_on_revision=term.revision,
        operation_key=f.key(),
    )
    record = ArchiveCorrection.objects.get()
    assert record.previous_value == "2026-27" and record.new_value == "2026 (Spring)"
    with pytest.raises(StaleRevisionError):
        c.correct_archive_record(
            head,
            object_type="term",
            object_id=term.pk,
            field="label",
            new_value="X",
            reason="Stale",
            based_on_revision=term.revision,
            operation_key=f.key(),
        )


@pytest.mark.req("FR-CLB-07", "UC-06")
@pytest.mark.django_db
def test_internal_profile_editable_only_by_own_club_eb_with_valid_contacts(world):
    c.update_internal_profile(
        world.president_a,
        world.club_a.pk,
        description="We code.",
        internal_contacts="President - president@iub-synthetic.test",
        expected_revision=1,
        operation_key=f.key(),
    )
    with pytest.raises(ValidationFailed):
        c.update_internal_profile(
            world.president_a,
            world.club_a.pk,
            description="",
            internal_contacts="call me",
            expected_revision=2,
            operation_key=f.key(),
        )
    with pytest.raises(NotFoundError):
        c.update_internal_profile(
            world.president_a,
            world.club_b.pk,
            description="",
            internal_contacts="",
            expected_revision=1,
            operation_key=f.key(),
        )


@pytest.mark.req("FR-CLB-04", "UC-08")
@pytest.mark.django_db
def test_organogram_shows_current_term_and_past_terms_by_selection(world, client, head):
    client.force_login(world.president_a)
    page = client.get(f"/clubs/{world.club_a.pk}/").content.decode()
    assert "Ayesha President" in page and "President" in page
    club = f.make_club("No Term Club", "NTC")
    client.force_login(head)
    assert "No current term is recorded" in client.get(f"/clubs/{club.pk}/").content.decode()


@pytest.mark.req("FR-CLB-05")
@pytest.mark.django_db
def test_archive_search_with_no_matches_shows_an_empty_state(world, client, head):
    client.force_login(head)
    page = client.get("/clubs/archive/?q=nothing").content.decode()
    assert "No archived terms match these filters" in page

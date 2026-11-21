"""FR-IAM-01/02/04/05/06, UC-01/03/04: sign-in, scope, profile corrections and dashboards."""


import pytest

from apps.accounts.commands import (
    SignInDenied,
    VerifiedIdentity,
    decide_profile_change,
    request_profile_change,
    set_grants,
    set_profile_active,
    sign_in_with_identity,
)
from apps.accounts.models import Profile, ProfileChangeRequest
from apps.platform_core.access import AccessCategory, Action, can
from apps.platform_core.exceptions import ConflictError, PermissionDeniedError, ValidationFailed
from apps.platform_core.models import AuditEntry, Notification
from tests import factories as f

ISS = "https://accounts.google.com"


def identity(email, sub="sub-1", hd="iub-synthetic.test", verified=True):
    return VerifiedIdentity(
        issuer=ISS, subject=sub, email=email, email_verified=verified, hosted_domain=hd
    )


# --------------------------------------------------------------------------- sign-in (FR-IAM-01)


@pytest.mark.req("FR-IAM-01", "UC-01", "AC-15")
@pytest.mark.django_db
def test_first_sign_in_binds_issuer_and_subject_and_later_uses_the_binding(world):
    profile = sign_in_with_identity(identity(world.president_a.iub_email, sub="g-123"))
    assert profile.pk == world.president_a.pk
    profile.refresh_from_db()
    assert (profile.oidc_issuer, profile.oidc_subject) == (ISS, "g-123")
    assert (
        sign_in_with_identity(identity(world.president_a.iub_email, sub="g-123")).pk == profile.pk
    )
    with pytest.raises(SignInDenied):
        sign_in_with_identity(identity(world.president_a.iub_email, sub="someone-else"))


@pytest.mark.req("FR-IAM-01", "UC-01", "AC-15")
@pytest.mark.parametrize(
    "case",
    ["personal_gmail", "unverified", "unknown", "wrong_hd", "inactive", "demo"],
)
@pytest.mark.django_db
def test_ineligible_sign_ins_are_denied_without_detail(world, case):
    target = world.president_a
    ident = identity(target.iub_email)
    if case == "personal_gmail":
        ident = identity("someone@gmail.com", hd="")
    elif case == "unverified":
        ident = identity(target.iub_email, verified=False)
    elif case == "unknown":
        ident = identity("nobody@iub-synthetic.test")
    elif case == "wrong_hd":
        ident = identity(target.iub_email, hd="other.test")
    elif case == "inactive":
        Profile.objects.filter(pk=target.pk).update(is_active=False)
    elif case == "demo":
        Profile.objects.filter(pk=target.pk).update(is_demo=True)
    with pytest.raises(SignInDenied):
        sign_in_with_identity(ident)


@pytest.mark.req("FR-IAM-01")
@pytest.mark.django_db
def test_explicit_test_account_does_not_enable_its_whole_domain(world, settings):
    settings.EXPLICIT_TEST_ACCOUNTS = ["townkeepers.test.account@gmail.com"]
    tester = f.make_profile(AccessCategory.EB_MEMBER, email="townkeepers.test.account@gmail.com")
    assert sign_in_with_identity(identity(tester.iub_email, sub="t1", hd="")).pk == tester.pk
    f.make_profile(AccessCategory.EB_MEMBER, email="other@gmail.com")
    with pytest.raises(SignInDenied):
        sign_in_with_identity(identity("other@gmail.com", sub="t2", hd=""))


@pytest.mark.req("FR-IAM-01", "UC-01", "NFR-SEC-01")
@pytest.mark.django_db
def test_sign_in_page_offers_personas_and_not_google(world, client):
    response = client.get("/auth/sign-in/")
    assert response.status_code == 200
    assert b"Continue with Google" not in response.content
    assert b"Choose a demonstration persona" in response.content
    assert client.get("/auth/google/start").status_code == 404
    assert client.get("/auth/google/callback").status_code == 404


@pytest.mark.req("FR-IAM-01", "AC-15")
@pytest.mark.django_db
def test_signed_out_or_deactivated_session_cannot_reach_protected_pages(world, client, head):
    client.force_login(world.president_a)
    assert client.get("/memos/").status_code == 200
    set_profile_active(
        head,
        world.president_a.pk,
        active=False,
        reason="Left the club",
        expected_revision=None,
        operation_key=f.key(),
    )
    assert client.get("/memos/").status_code == 302


@pytest.mark.req("AC-15", "NFR-SEC-02")
@pytest.mark.django_db
def test_demo_login_is_isolated_from_live_mode(client, settings, world):
    demo = f.make_profile(AccessCategory.EB_MEMBER, email="demo@townhall.test", is_demo=True)
    assert client.get("/dev/login/").status_code == 200
    assert (
        client.post("/dev/login/", {"profile_id": world.president_a.pk}).status_code == 200
    )  # not a demo persona
    assert "_auth_user_id" not in client.session
    client.post("/dev/login/", {"profile_id": demo.pk})
    assert int(client.session["_auth_user_id"]) == demo.pk
    settings.DEMO_AUTH = False
    assert client.get("/").status_code == 302  # demo session no longer valid
    assert client.get("/dev/login/").status_code == 404


@pytest.mark.req("AC-15")
def test_production_settings_refuse_demo_auth(settings):
    from apps.platform_core.checks import demo_auth_disabled_in_production

    settings.IS_PRODUCTION = True
    settings.DEMO_AUTH = True
    assert [e.id for e in demo_auth_disabled_in_production(None)] == ["townhall.E001"]


# --------------------------------------------------------------------------- scope (FR-IAM-02/04)


@pytest.mark.req("FR-IAM-02", "FR-IAM-04", "AC-11", "BR-01")
@pytest.mark.django_db
def test_eb_member_acts_only_in_the_assigned_club(world):
    assert can(world.president_a, Action.MEMOS_AUTHOR, world.club_a)
    assert not can(world.president_a, Action.MEMOS_AUTHOR, world.club_b)
    assert not can(world.president_a, Action.MEMOS_HEAD_APPROVE)
    assert not can(world.advisor_a, Action.MEMOS_ADVISOR_CONFIRM, world.club_b)


@pytest.mark.req("FR-IAM-02", "AC-17")
@pytest.mark.django_db
def test_grant_change_applies_to_the_next_request_on_an_open_page(world, client, head):
    client.force_login(world.president_a)
    assert client.get("/events/").status_code == 200
    remaining = {Action.MEMOS_VIEW, Action.MEMOS_AUTHOR}
    set_grants(
        head,
        world.president_a.pk,
        remaining,
        expected_revision=world.president_a.revision,
        operation_key=f.key(),
    )
    assert client.get("/events/").status_code == 403
    assert AuditEntry.objects.filter(action="profile.set_grants").count() == 1


@pytest.mark.req("FR-IAM-02")
@pytest.mark.django_db
def test_empty_grant_set_gives_no_module_access(world, head):
    set_grants(head, world.treasurer_a.pk, set(), expected_revision=1, operation_key=f.key())
    assert not can(world.treasurer_a, Action.MEMOS_VIEW, world.club_a)
    assert not can(world.treasurer_a, Action.CLUBS_VIEW, world.club_a)


@pytest.mark.req("FR-IAM-02", "FR-IAM-07")
@pytest.mark.django_db
def test_grant_edits_from_a_stale_page_or_by_self_are_refused(world, head):
    from apps.platform_core.exceptions import StaleRevisionError

    with pytest.raises(StaleRevisionError):
        set_grants(head, world.president_a.pk, set(), expected_revision=99, operation_key=f.key())
    with pytest.raises(PermissionDeniedError):
        set_grants(head, head.pk, set(), expected_revision=head.revision, operation_key=f.key())


@pytest.mark.req("FR-IAM-04", "AC-17")
@pytest.mark.django_db
def test_assignment_effective_only_between_its_dates(world, frozen_clock, head):
    from datetime import date

    from apps.clubs.models import Assignment

    eb = f.make_profile(AccessCategory.EB_MEMBER)
    f.assign_eb(eb, world.term_a, head, "Member", start=date(2027, 1, 1))
    assert not can(eb, Action.MEMOS_VIEW, world.club_a)  # pending assignment
    Assignment.objects.filter(profile=eb).update(
        start_date=date(2026, 1, 1), end_date=date(2026, 11, 30)
    )
    assert not can(eb, Action.MEMOS_VIEW, world.club_a)  # ended yesterday
    Assignment.objects.filter(profile=eb).update(end_date=date(2026, 12, 1))
    assert can(eb, Action.MEMOS_VIEW, world.club_a)  # inclusive end date


# --------------------------------------------------------------------------- profile corrections (FR-IAM-05)


@pytest.mark.req("FR-IAM-05", "UC-03", "AC-17")
@pytest.mark.django_db
def test_ordinary_correction_applies_once_and_is_audited(world, head):
    result = request_profile_change(
        world.president_a,
        field="personal_phone",
        proposed_value="+880 1700 000000",
        operation_key=f.key(),
    )
    req = ProfileChangeRequest.objects.get(pk=result.object_id)
    assert req.route == ProfileChangeRequest.Route.ORDINARY
    notice = Notification.objects.get(recipient=head, event_type="profile_change.submitted")
    assert "+880" not in notice.message  # sensitive value withheld
    world.president_a.refresh_from_db()
    assert world.president_a.personal_phone == ""  # saved value stays while pending

    decide_profile_change(head, req.pk, approve=True, operation_key=f.key())
    world.president_a.refresh_from_db()
    assert world.president_a.personal_phone == "+880 1700 000000"
    entry = AuditEntry.objects.get(action="profile.update")
    assert entry.before == {"personal_phone": ""} and entry.after == {
        "personal_phone": "+880 1700 000000"
    }
    with pytest.raises(ConflictError):
        decide_profile_change(head, req.pk, approve=True, operation_key=f.key())


@pytest.mark.req("FR-IAM-05", "AC-17")
@pytest.mark.django_db
def test_role_change_request_routes_to_an_account_administrator(world, head, system_admin):
    result = request_profile_change(
        world.president_a,
        field="access_category",
        proposed_value=AccessCategory.DOSA_HEAD,
        operation_key=f.key(),
    )
    req = ProfileChangeRequest.objects.get(pk=result.object_id)
    assert req.route == ProfileChangeRequest.Route.PROTECTED
    assert Notification.objects.filter(
        recipient=system_admin, event_type="profile_change.submitted"
    ).exists()
    decide_profile_change(system_admin, req.pk, approve=True, operation_key=f.key())
    world.president_a.refresh_from_db()
    assert (
        world.president_a.access_category == AccessCategory.EB_MEMBER
    )  # applied only via controlled screens


@pytest.mark.req("FR-IAM-05")
@pytest.mark.django_db
def test_correction_whose_saved_value_changed_during_review_is_not_applied(world, head):
    result = request_profile_change(
        world.president_a, field="full_name", proposed_value="Ayesha Rahman", operation_key=f.key()
    )
    Profile.objects.filter(pk=world.president_a.pk).update(full_name="Changed Elsewhere")
    with pytest.raises(ConflictError) as excinfo:
        decide_profile_change(head, result.object_id, approve=True, operation_key=f.key())
    assert excinfo.value.current_state["current_value"] == "Changed Elsewhere"


@pytest.mark.req("FR-IAM-05")
@pytest.mark.django_db
def test_invalid_proposed_values_are_flagged(world):
    with pytest.raises(ValidationFailed):
        request_profile_change(
            world.president_a,
            field="personal_email",
            proposed_value="not-an-email",
            operation_key=f.key(),
        )
    with pytest.raises(ValidationFailed):
        request_profile_change(
            world.president_a, field="password", proposed_value="x", operation_key=f.key()
        )


# --------------------------------------------------------------------------- dashboards and pages (FR-IAM-06)


@pytest.mark.req("FR-IAM-06", "UC-04", "AC-15")
@pytest.mark.django_db
def test_dashboards_show_role_modules_and_hide_others(world, client, head):
    client.force_login(world.president_a)
    page = client.get("/").content.decode()
    assert "Memo Management" in page and "Accounts" not in page and "Workflow settings" not in page
    client.force_login(head)
    page = client.get("/").content.decode()
    assert (
        "Memos awaiting your approval" in page and "No memos are waiting for DoSA approval." in page
    )
    assert "Workflow settings" in page
    client.force_login(world.dept_head)
    page = client.get("/").content.decode()
    assert "No signature tasks are assigned to you." in page


@pytest.mark.req("FR-IAM-06", "AC-11")
@pytest.mark.django_db
def test_direct_links_to_admin_pages_are_denied(world, client):
    client.force_login(world.president_a)
    assert client.get("/accounts/").status_code == 403
    assert client.get("/accounts/new/").status_code == 403
    assert client.get("/settings/policy/").status_code == 403
    assert client.get(f"/clubs/{world.club_b.pk}/").status_code == 404


@pytest.mark.req("FR-IAM-03", "UC-02")
@pytest.mark.django_db
def test_provisioning_form_creates_profile_and_reports_field_errors(head, client):
    client.force_login(head)
    page = client.get("/accounts/new/")
    key = page.context["form"].initial["operation_key"]
    bad = client.post(
        "/accounts/new/",
        {
            "operation_key": key,
            "full_name": "",
            "iub_email": "x@gmail.com",
            "access_category": "eb_member",
            "department": "na",
            "major": "na",
            "use_default_grants": "on",
        },
    )
    assert bad.status_code == 200 and "There is a problem" in bad.content.decode()
    ok = client.post(
        "/accounts/new/",
        {
            "operation_key": key,
            "full_name": "New Member",
            "iub_email": "new.member@iub-synthetic.test",
            "access_category": "eb_member",
            "department": "cse",
            "major": "cs",
            "use_default_grants": "on",
        },
    )
    assert ok.status_code == 302
    assert Profile.objects.filter(iub_email="new.member@iub-synthetic.test").exists()

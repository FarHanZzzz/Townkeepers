"""FR-IAM-02/03, UC-02: provisioning profiles, starting with the first-Head slice (PRD C.3)."""

import pytest

from apps.accounts.commands import ProfileInput, bootstrap_admin, provision_profile
from apps.accounts.models import Grant, Profile
from apps.platform_core.access import CEILING, AccessCategory, Action
from apps.platform_core.exceptions import (
    ConflictError,
    OperationKeyConflict,
    PermissionDeniedError,
    ValidationFailed,
)
from apps.platform_core.models import AuditEntry, Job, Notification
from tests.factories import key


def head_input(email="head@iub-synthetic.test", **overrides) -> ProfileInput:
    data = {
        "iub_email": email,
        "full_name": "Synthetic DoSA Head",
        "access_category": AccessCategory.DOSA_HEAD,
        "designation": "Head, Division of Student Activities",
    }
    data.update(overrides)
    return ProfileInput(**data)


@pytest.mark.req("FR-IAM-03", "UC-02", "AC-15")
@pytest.mark.django_db
def test_provisioning_rejects_duplicate_iub_address(system_admin):
    # Arrange
    provision_profile(system_admin, head_input(), grants=None, operation_key=key())

    # Act
    with pytest.raises(ValidationFailed) as excinfo:
        provision_profile(
            system_admin,
            head_input(email="HEAD@iub-synthetic.test", access_category=AccessCategory.SIGNER),
            grants=None,
            operation_key=key(),
        )

    # Assert
    assert "iub_email" in excinfo.value.field_errors
    assert Profile.objects.filter(iub_email__iexact="head@iub-synthetic.test").count() == 1


@pytest.mark.req("FR-IAM-03", "UC-02", "AC-15")
@pytest.mark.django_db
def test_system_admin_provisions_first_head_with_one_audit_row_and_one_invitation(system_admin):
    result = provision_profile(system_admin, head_input(), grants=None, operation_key=key())

    head = Profile.objects.get(pk=result.object_id)
    assert head.access_category == AccessCategory.DOSA_HEAD
    assert not head.has_usable_password()
    assert set(Grant.objects.filter(profile=head).values_list("action", flat=True)) == set(
        CEILING[AccessCategory.DOSA_HEAD]
    )
    audits = AuditEntry.objects.filter(action="profile.provision", object_id=str(head.pk))
    assert audits.count() == 1
    assert audits.get().actor == system_admin
    invitations = Notification.objects.filter(recipient=head, event_type="profile.invitation")
    assert invitations.count() == 1
    assert invitations.get().email_address == "head@iub-synthetic.test"
    assert Job.objects.filter(kind="notification.email").count() == 1


@pytest.mark.req("FR-IAM-03", "BR-10")
@pytest.mark.django_db
def test_replayed_provisioning_returns_the_same_profile(system_admin):
    op = key()
    first = provision_profile(system_admin, head_input(), grants=None, operation_key=op)
    second = provision_profile(system_admin, head_input(), grants=None, operation_key=op)

    assert second.replayed is True
    assert second.object_id == first.object_id
    assert Profile.objects.filter(access_category=AccessCategory.DOSA_HEAD).count() == 1
    assert Job.objects.count() == 1


@pytest.mark.req("FR-COM-04", "BR-10")
@pytest.mark.django_db
def test_operation_key_reused_with_different_content_is_a_conflict(system_admin):
    op = key()
    provision_profile(system_admin, head_input(), grants=None, operation_key=op)
    with pytest.raises(OperationKeyConflict):
        provision_profile(
            system_admin, head_input(full_name="Someone Else"), grants=None, operation_key=op
        )


@pytest.mark.req("FR-IAM-03", "UC-02")
@pytest.mark.django_db
def test_head_cannot_provision_another_head_or_grant_account_administration(head):
    with pytest.raises(PermissionDeniedError):
        provision_profile(
            head, head_input(email="h2@iub-synthetic.test"), grants=None, operation_key=key()
        )
    with pytest.raises(ValidationFailed):
        provision_profile(
            head,
            head_input(email="x@iub-synthetic.test", access_category=AccessCategory.EB_MEMBER),
            grants={Action.MEMOS_HEAD_APPROVE},
            operation_key=key(),
        )


@pytest.mark.req("FR-IAM-02", "FR-IAM-03")
@pytest.mark.django_db
def test_unrecognized_or_out_of_role_grants_are_rejected(head):
    eb = head_input(email="eb@iub-synthetic.test", access_category=AccessCategory.EB_MEMBER)
    with pytest.raises(ValidationFailed) as excinfo:
        provision_profile(head, eb, grants={"memos.fly_to_moon"}, operation_key=key())
    assert "grants" in excinfo.value.field_errors
    with pytest.raises(ValidationFailed):
        provision_profile(head, eb, grants={Action.MEMOS_ADVISOR_CONFIRM}, operation_key=key())
    assert not Profile.objects.filter(iub_email="eb@iub-synthetic.test").exists()


@pytest.mark.req("FR-IAM-03")
@pytest.mark.django_db
def test_missing_fields_and_ineligible_domain_are_identified_before_saving(head):
    bad = head_input(
        email="someone@gmail.com",
        full_name=" ",
        access_category=AccessCategory.EB_MEMBER,
        personal_phone="abc",
    )
    with pytest.raises(ValidationFailed) as excinfo:
        provision_profile(head, bad, grants=None, operation_key=key())
    assert {"iub_email", "full_name", "personal_phone"} <= set(excinfo.value.field_errors)


@pytest.mark.req("FR-IAM-03", "UC-02")
@pytest.mark.django_db
def test_only_one_active_head_can_exist(system_admin, head):
    with pytest.raises(ValidationFailed):
        provision_profile(
            system_admin,
            head_input(email="h2@iub-synthetic.test"),
            grants=None,
            operation_key=key(),
        )


@pytest.mark.req("UC-02", "FR-IAM-03")
@pytest.mark.django_db
def test_bootstrap_admin_is_idempotent_and_audited():
    first = bootstrap_admin(
        iub_email="Admin@iub-synthetic.test", full_name="Synthetic Admin", operator="ops"
    )
    again = bootstrap_admin(
        iub_email="admin@iub-synthetic.test", full_name="Synthetic Admin", operator="ops"
    )

    assert first.pk == again.pk
    assert first.access_category == AccessCategory.SYSTEM_ADMIN
    assert AuditEntry.objects.filter(action="profile.bootstrap_admin").count() == 1
    with pytest.raises(ConflictError):
        bootstrap_admin(iub_email="other@iub-synthetic.test", full_name="Other", operator="ops")

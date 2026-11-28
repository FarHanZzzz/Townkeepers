"""Account commands (FR-IAM-01 to FR-IAM-05, FR-IAM-07, UC-01 to UC-03).

Every public command takes the authenticated actor, checks authority inside its transaction, and
writes the change, its audit entry and any notification intent together.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.platform_core import audit, clock
from apps.platform_core.access import (
    ADMIN_ONLY_GRANTS,
    CEILING,
    AccessCategory,
    Action,
    effective_actions,
)
from apps.platform_core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    StaleRevisionError,
    ValidationFailed,
)
from apps.platform_core.notifications import notify
from apps.platform_core.protocol import CommandResult, execute

from .models import Department, Grant, Major, Profile, ProfileChangeRequest

PHONE = re.compile(r"^\+?[0-9][0-9 \-]{5,18}$")
NON_STUDENT = {
    AccessCategory.SYSTEM_ADMIN,
    AccessCategory.DOSA_HEAD,
    AccessCategory.SIGNER,
    AccessCategory.FACULTY_ADVISOR,
}
ORDINARY_FIELDS = {
    "full_name": "Full name",
    "designation": "Designation",
    "department": "Department",
    "major": "Major",
    "personal_email": "Personal email",
    "personal_phone": "Personal phone",
    "emergency_phone": "Emergency phone",
    "permanent_address": "Permanent address",
    "temporary_address": "Temporary address",
}
PROTECTED_FIELDS = {
    "iub_email": "IUB sign-in address",
    "access_category": "Role",
    "club_assignment": "Club assignment",
    "tenure": "Tenure",
    "privileges": "Privileges",
}
SENSITIVE_FIELDS = {
    "personal_email",
    "personal_phone",
    "emergency_phone",
    "permanent_address",
    "temporary_address",
    "iub_email",
}


class SignInDenied(Exception):
    """Generic sign-in failure. Never reveals whether a profile exists (FR-IAM-01)."""


@dataclass(frozen=True)
class ProfileInput:
    """Fields collected by the provisioning form (FR-IAM-03)."""

    iub_email: str
    full_name: str
    access_category: str
    designation: str = ""
    department: str = Department.NA
    major: str = Major.NA
    personal_email: str = ""
    personal_phone: str = ""
    emergency_phone: str = ""
    permanent_address: str = ""
    temporary_address: str = ""
    is_demo: bool = False


@dataclass(frozen=True)
class VerifiedIdentity:
    """Claims from a server-validated Google ID token."""

    issuer: str
    subject: str
    email: str
    email_verified: bool
    hosted_domain: str = ""


# --------------------------------------------------------------------------- validation helpers


def normalize_email(value: str) -> str:
    """Canonical stored form of an email address: trimmed and lower-case."""
    return (value or "").strip().lower()


def is_eligible_iub_address(email: str) -> bool:
    """True for any well-formed email address."""
    email = normalize_email(email)
    if "@" not in email:
        return False
    domain = email.rpartition("@")[2]
    return bool(domain)


def _field_value_errors(field: str, value: str, category: str | None = None) -> list[str]:
    value = value or ""
    if field == "full_name" and not value.strip():
        return ["Enter the full name."]
    if field in {"personal_email"} and value:
        try:
            validate_email(value)
        except DjangoValidationError:
            return ["Enter a valid email address."]
    if field in {"personal_phone", "emergency_phone"} and value and not PHONE.match(value):
        return ["Enter a phone number using digits, spaces or dashes (6 to 19 characters)."]
    if field == "department" and value not in Department.values:
        return ["Choose a department from the list."]
    if field == "major" and value not in Major.values:
        return ["Choose a major from the list."]
    if field == "major" and category in NON_STUDENT and value != Major.NA:
        return ["Major is N/A for this access category."]
    if field == "access_category" and value not in AccessCategory.values:
        return ["Choose an access category from the list."]
    if field == "iub_email":
        try:
            validate_email(value)
        except DjangoValidationError:
            return ["Enter a valid IUB email address."]
    if field in {"designation"} and len(value) > 120:
        return ["Keep the designation under 120 characters."]
    return []


def validate_profile_input(data: ProfileInput) -> dict[str, list[str]]:
    """Field errors for a provisioning form; demo identities must use the synthetic demo domain."""
    errors: dict[str, list[str]] = {}
    for field in [
        "full_name",
        "access_category",
        "department",
        "major",
        "personal_email",
        "personal_phone",
        "emergency_phone",
        "designation",
        "iub_email",
    ]:
        problems = _field_value_errors(field, getattr(data, field), data.access_category)
        if problems:
            errors[field] = problems
    email = normalize_email(data.iub_email)
    if "iub_email" not in errors:
        if data.is_demo:
            if not settings.DEMO_AUTH or not email.endswith("@" + settings.DEMO_EMAIL_DOMAIN):
                errors["iub_email"] = [
                    f"Demonstration identities must use @{settings.DEMO_EMAIL_DOMAIN} with DEMO_AUTH enabled."
                ]
        elif not is_eligible_iub_address(email):
            errors["iub_email"] = ["Enter a valid email address."]
    return errors


def validate_grants(category: str, actions: set[str] | None, actor: Profile) -> set[str]:
    """Return the grant set or raise. Unrecognized, out-of-role or beyond-authority grants fail."""
    ceiling = CEILING.get(category, frozenset())
    if actions is None:
        actions = set(ceiling)
    unknown = {a for a in actions if a not in Action.values}
    if unknown:
        raise ValidationFailed(
            field_errors={"grants": ["Unrecognized privilege: " + ", ".join(sorted(unknown))]}
        )
    outside = actions - ceiling
    if outside:
        raise ValidationFailed(
            field_errors={
                "grants": ["Not available for this access category: " + ", ".join(sorted(outside))]
            }
        )
    if actor.access_category != AccessCategory.SYSTEM_ADMIN and actions & ADMIN_ONLY_GRANTS:
        raise ValidationFailed(
            field_errors={"grants": ["Only a System Admin can grant account administration."]}
        )
    return set(actions)


def _require_active_actor(actor: Profile, action: str) -> None:
    if actor is None or not actor.is_active or action not in effective_actions(actor):
        raise PermissionDeniedError()


def _require_category_authority(actor: Profile, target_category: str) -> None:
    """Only a System Admin manages System Admin and DoSA Head profiles (delegation limit)."""
    if target_category in {AccessCategory.SYSTEM_ADMIN, AccessCategory.DOSA_HEAD} and (
        actor.access_category != AccessCategory.SYSTEM_ADMIN
    ):
        raise PermissionDeniedError("Only a System Admin can manage this profile.")


def _another_active_head_exists(exclude_pk=None) -> bool:
    qs = Profile.objects.filter(access_category=AccessCategory.DOSA_HEAD, is_active=True)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def _lock_profile(profile_id) -> Profile:
    try:
        return Profile.objects.select_for_update().get(pk=profile_id)
    except Profile.DoesNotExist as exc:
        raise NotFoundError() from exc


def _check_revision(obj, expected: int | None) -> None:
    if expected is not None and obj.revision != expected:
        raise StaleRevisionError(current_state={"revision": obj.revision})


def _send_invitation(profile: Profile) -> None:
    notify(
        [profile],
        event_key=f"profile:{profile.pk}:invitation",
        event_type="profile.invitation",
        object_type="accounts.profile",
        object_id=profile.pk,
        subject="Your Amader TOWNHALL profile is ready",
        message=(
            f"Hello {profile.full_name}, a profile was created for you as "
            f"{profile.designation_display}. Sign in with your IUB Google account."
        ),
        link="/auth/sign-in/",
        email=True,
    )


# --------------------------------------------------------------------------- bootstrap


def bootstrap_admin(*, iub_email: str, full_name: str, operator: str) -> Profile:
    """Create the first System Admin for a named IUB identity (operator-only, idempotent; TR 4.2).

    Actor scope: operator shell access, recorded in the audit reason. Running it again for the same
    address returns the existing System Admin without changes. A different address is refused once
    a System Admin exists, so the command cannot mint extra administrators.
    """
    email = normalize_email(iub_email)
    errors = _field_value_errors("iub_email", email) or (
        [] if is_eligible_iub_address(email) else ["Enter a valid email address."]
    )
    if not full_name.strip():
        raise ValidationFailed(field_errors={"full_name": ["Enter the full name."]})
    if errors:
        raise ValidationFailed(field_errors={"iub_email": errors})
    with transaction.atomic():
        existing = Profile.objects.select_for_update().filter(iub_email__iexact=email).first()
        if existing:
            if existing.access_category != AccessCategory.SYSTEM_ADMIN:
                raise ValidationFailed(
                    field_errors={"iub_email": ["This address belongs to another profile."]}
                )
            return existing
        if Profile.objects.filter(access_category=AccessCategory.SYSTEM_ADMIN).exists():
            raise ConflictError(
                "A System Admin already exists. Provision further accounts in the application."
            )
        admin = Profile(
            iub_email=email,
            full_name=full_name.strip(),
            access_category=AccessCategory.SYSTEM_ADMIN,
            designation="System Admin",
            created_at=clock.now(),
        )
        admin.set_unusable_password()
        admin.save()
        audit.record(
            None,
            "profile.bootstrap_admin",
            admin,
            after={"iub_email": email},
            reason=f"Operator bootstrap by {operator}",
        )
        _send_invitation(admin)
        return admin


# --------------------------------------------------------------------------- provisioning


def provision_profile(
    actor: Profile,
    data: ProfileInput,
    *,
    grants: set[str] | None,
    operation_key: str | None,
    club_id: int | None = None,
    term_id: int | None = None,
) -> CommandResult:
    """Create a profile with its grants and send one IUB invitation (FR-IAM-02, FR-IAM-03, UC-02).

    Actor scope: System Admin, or a DoSA Head holding ``accounts.provision`` for Signer, EB and
    Advisor profiles. ``grants=None`` grants the target category's full ceiling.
    EB and Faculty Advisor profiles must be assigned to a club at creation time.
    Transaction: profile, grant rows, audit entry, notice and email job commit together.
    """
    payload = {
        **asdict(data),
        "grants": sorted(grants) if grants is not None else None,
        "club_id": club_id,
        "term_id": term_id,
    }

    def handler() -> CommandResult:
        from apps.clubs.models import Assignment, Club, Term

        _require_active_actor(actor, Action.ACCOUNTS_PROVISION)
        _require_category_authority(actor, data.access_category)
        errors = validate_profile_input(data)
        email = normalize_email(data.iub_email)
        if "iub_email" not in errors and Profile.objects.filter(iub_email__iexact=email).exists():
            errors["iub_email"] = ["A profile with this IUB address already exists."]
        needs_club = data.access_category in {
            AccessCategory.EB_MEMBER,
            AccessCategory.FACULTY_ADVISOR,
        }
        club = None
        term = None
        if needs_club and not club_id:
            errors["club"] = ["A club affiliation is required for this access category."]
        if data.access_category == AccessCategory.EB_MEMBER and not term_id:
            errors["term"] = ["An EB term is required for EB member profiles."]
        if club_id:
            club = Club.objects.filter(pk=club_id, status=Club.Status.ACTIVE).first()
            if club is None:
                errors["club"] = ["Choose an active club."]
        if term_id:
            term = Term.objects.select_related("club").filter(pk=term_id).first()
            if term is None:
                errors["term"] = ["Choose a valid EB term."]
            elif club and term.club_id != club.pk:
                errors["term"] = ["Select a term that belongs to the chosen club."]
            elif term.status == Term.Status.CLOSED:
                errors["term"] = ["Choose an active or upcoming term."]
        if errors:
            raise ValidationFailed(field_errors=errors)
        if data.access_category == AccessCategory.DOSA_HEAD and _another_active_head_exists():
            raise ValidationFailed(
                field_errors={
                    "access_category": ["The DoSA Head role already has an active holder."]
                }
            )
        granted = validate_grants(data.access_category, grants, actor)
        profile = Profile(
            **{k: v for k, v in asdict(data).items() if k != "iub_email"},
            iub_email=email,
            created_by=actor,
            created_at=clock.now(),
        )
        profile.full_name = profile.full_name.strip()
        profile.set_unusable_password()
        try:
            with transaction.atomic():
                profile.save()
                if data.access_category != AccessCategory.SYSTEM_ADMIN:
                    now = clock.now()
                    Grant.objects.bulk_create(
                        [
                            Grant(profile=profile, action=a, granted_by=actor, granted_at=now)
                            for a in sorted(granted)
                        ]
                    )
                if needs_club and club is not None:
                    today = clock.local_today()
                    if data.access_category == AccessCategory.EB_MEMBER and term is not None:
                        Assignment.objects.create(
                            profile=profile,
                            kind=Assignment.Kind.EB_MEMBER,
                            club=club,
                            term=term,
                            designation=(data.designation or "").strip(),
                            start_date=max(today, term.start_date),
                            end_date=None,
                            granted_by=actor,
                            created_at=clock.now(),
                        )
                    elif data.access_category == AccessCategory.FACULTY_ADVISOR:
                        Assignment.objects.create(
                            profile=profile,
                            kind=Assignment.Kind.FACULTY_ADVISOR,
                            club=club,
                            term=None,
                            designation=(data.designation or "Faculty Advisor").strip(),
                            start_date=today,
                            end_date=None,
                            granted_by=actor,
                            created_at=clock.now(),
                        )
        except IntegrityError as exc:
            raise ValidationFailed(
                field_errors={"iub_email": ["A profile with this IUB address already exists."]}
            ) from exc
        audit.record(
            actor,
            "profile.provision",
            profile,
            after={
                "iub_email": email,
                "access_category": data.access_category,
                "designation": data.designation,
                "grants": sorted(granted),
                "club_id": club_id,
                "term_id": term_id,
            },
            revision=profile.revision,
        )
        _send_invitation(profile)
        return CommandResult("accounts.profile", profile.pk, "provisioned")

    return execute(
        actor=actor,
        action="profile.provision",
        operation_key=operation_key,
        payload=payload,
        handler=handler,
    )


def set_grants(
    actor: Profile,
    profile_id: int,
    actions: set[str],
    *,
    expected_revision: int | None,
    operation_key: str | None,
) -> CommandResult:
    """Replace a profile's active grants (FR-IAM-02, FR-IAM-07).

    Actor scope: ``accounts.manage_grants``; only a System Admin edits Head/Admin profiles or grants
    account administration. Nobody but a System Admin edits their own grants.
    Transaction: revoked rows keep their history; new rows record the granting actor; audited.
    Retry safety: operation key replay; ``expected_revision`` rejects edits from a stale page.
    """

    def handler() -> CommandResult:
        _require_active_actor(actor, Action.ACCOUNTS_MANAGE_GRANTS)
        target = _lock_profile(profile_id)
        _require_category_authority(actor, target.access_category)
        if target.pk == actor.pk and actor.access_category != AccessCategory.SYSTEM_ADMIN:
            raise PermissionDeniedError("You cannot change your own privileges.")
        _check_revision(target, expected_revision)
        wanted = validate_grants(target.access_category, set(actions), actor)
        current = set(
            Grant.objects.filter(profile=target, revoked_at__isnull=True).values_list(
                "action", flat=True
            )
        )
        now = clock.now()
        Grant.objects.filter(
            profile=target, revoked_at__isnull=True, action__in=current - wanted
        ).update(revoked_at=now, revoked_by=actor)
        Grant.objects.bulk_create(
            [
                Grant(profile=target, action=a, granted_by=actor, granted_at=now)
                for a in sorted(wanted - current)
            ]
        )
        target.revision += 1
        target.save(update_fields=["revision"])
        audit.record(
            actor,
            "profile.set_grants",
            target,
            before={"grants": sorted(current)},
            after={"grants": sorted(wanted)},
            revision=target.revision,
        )
        return CommandResult("accounts.profile", target.pk, "grants_updated")

    return execute(
        actor=actor,
        action="profile.set_grants",
        operation_key=operation_key,
        payload={"profile": profile_id, "actions": sorted(actions)},
        handler=handler,
    )


def set_profile_active(
    actor: Profile,
    profile_id: int,
    *,
    active: bool,
    reason: str,
    expected_revision: int | None,
    operation_key: str | None,
) -> CommandResult:
    """Deactivate or reactivate a profile (FR-IAM-03).

    Deactivation ends access on the next request and preserves all submissions, decisions,
    signatures and audit records. Reactivation re-checks the single DoSA Head rule; existing
    assignments still apply only within their dates.
    """

    def handler() -> CommandResult:
        _require_active_actor(actor, Action.ACCOUNTS_PROVISION)
        target = _lock_profile(profile_id)
        _require_category_authority(actor, target.access_category)
        if target.pk == actor.pk:
            raise PermissionDeniedError("You cannot change your own activation.")
        _check_revision(target, expected_revision)
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter a reason."]})
        if target.is_active == active:
            raise ConflictError("The profile already has this status.")
        if (
            active
            and target.access_category == AccessCategory.DOSA_HEAD
            and _another_active_head_exists(target.pk)
        ):
            raise ValidationFailed("The DoSA Head role already has an active holder.")
        target.is_active = active
        target.deactivated_at = None if active else clock.now()
        target.revision += 1
        target.save(update_fields=["is_active", "deactivated_at", "revision"])
        audit.record(
            actor,
            "profile.reactivate" if active else "profile.deactivate",
            target,
            before={"is_active": not active},
            after={"is_active": active},
            reason=reason,
            revision=target.revision,
        )
        return CommandResult(
            "accounts.profile", target.pk, "reactivated" if active else "deactivated"
        )

    return execute(
        actor=actor,
        action="profile.set_active",
        operation_key=operation_key,
        payload={"profile": profile_id, "active": active, "reason": reason},
        handler=handler,
    )


def resend_invitation(actor: Profile, profile_id: int) -> None:
    """Retry the original invitation email without creating another profile (FR-IAM-03)."""
    from apps.platform_core.jobs import retry_job
    from apps.platform_core.models import Notification

    _require_active_actor(actor, Action.NOTIFICATIONS_RETRY)
    notice = Notification.objects.filter(event_key=f"profile:{profile_id}:invitation").first()
    if notice is None or notice.email_job_id is None:
        raise NotFoundError()
    retry_job(actor, notice.email_job_id)


# --------------------------------------------------------------------------- profile corrections


def _reviewers_for(route: str):
    if route == ProfileChangeRequest.Route.ORDINARY:
        candidates = Profile.objects.filter(
            access_category=AccessCategory.DOSA_HEAD, is_active=True
        )
        needed = Action.PROFILE_REVIEW
    else:
        candidates = Profile.objects.filter(
            access_category__in=[AccessCategory.SYSTEM_ADMIN, AccessCategory.DOSA_HEAD],
            is_active=True,
        )
        needed = Action.ACCOUNTS_MANAGE_GRANTS
    return [p for p in candidates if needed in effective_actions(p)]


def request_profile_change(
    actor: Profile, *, field: str, proposed_value: str, operation_key: str | None
) -> CommandResult:
    """Propose a correction to one's own profile field (FR-IAM-05, UC-03).

    The saved value stays in force while pending. Ordinary fields notify active DoSA personnel;
    protected fields (IUB address, role, club assignment, tenure, privileges) route to account
    administrators. Sensitive values never appear in the notice, only the request reference.
    """

    def handler() -> CommandResult:
        if actor is None or not actor.is_active:
            raise PermissionDeniedError()
        if field in ORDINARY_FIELDS:
            route = ProfileChangeRequest.Route.ORDINARY
        elif field in PROTECTED_FIELDS:
            route = ProfileChangeRequest.Route.PROTECTED
        else:
            raise ValidationFailed(
                field_errors={"field": ["This field cannot be changed by request."]}
            )
        value = (proposed_value or "").strip()
        if field == "iub_email":
            value = normalize_email(value)
        errors = (
            _field_value_errors(field, value, actor.access_category)
            if field in ORDINARY_FIELDS or field in {"iub_email", "access_category"}
            else ([] if value else ["Describe the requested change."])
        )
        if not value and field not in {
            "designation",
            "personal_email",
            "personal_phone",
            "emergency_phone",
            "permanent_address",
            "temporary_address",
        }:
            errors = errors or ["Enter the proposed value."]
        if errors:
            raise ValidationFailed(field_errors={"proposed_value": errors})
        current = str(getattr(actor, field, "") or "") if hasattr(actor, field) else ""
        if hasattr(actor, field) and current == value:
            raise ValidationFailed(
                field_errors={"proposed_value": ["The proposed value matches the saved value."]}
            )
        if ProfileChangeRequest.objects.filter(
            profile=actor, field=field, status=ProfileChangeRequest.Status.PENDING
        ).exists():
            raise ConflictError("A request for this field is already pending.")
        req = ProfileChangeRequest.objects.create(
            profile=actor,
            field=field,
            original_value=current,
            proposed_value=value,
            route=route,
            requested_at=clock.now(),
        )
        label = ORDINARY_FIELDS.get(field) or PROTECTED_FIELDS[field]
        detail = "" if field in SENSITIVE_FIELDS else f" Proposed value: {value}."
        notify(
            _reviewers_for(route),
            event_key=f"profile_change:{req.pk}:submitted",
            event_type="profile_change.submitted",
            object_type="accounts.profilechangerequest",
            object_id=req.pk,
            subject=f"Profile correction request #{req.pk}",
            message=f"{actor.full_name} requested a change to {label}.{detail}",
            link=f"/accounts/profile-requests/{req.pk}/",
        )
        audit.record(actor, "profile_change.request", req, after={"field": field, "route": route})
        return CommandResult("accounts.profilechangerequest", req.pk, "pending")

    return execute(
        actor=actor,
        action="profile_change.request",
        operation_key=operation_key,
        payload={"field": field, "value": proposed_value},
        handler=handler,
    )


DIRECT_EDIT_FIELDS = set(ORDINARY_FIELDS) | {"iub_email", "access_category"}


def _club_notification_recipients(actor: Profile) -> list[Profile]:
    """Other EB members and Faculty Advisors of the actor's active clubs."""
    from apps.clubs.models import Assignment

    today = clock.local_today()
    club_ids = list(
        Assignment.objects.filter(
            profile=actor,
            start_date__lte=today,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        .values_list("club_id", flat=True)
        .distinct()
    )
    if not club_ids:
        return []
    recipient_ids = (
        Assignment.objects.filter(
            club_id__in=club_ids,
            kind__in=[Assignment.Kind.EB_MEMBER, Assignment.Kind.FACULTY_ADVISOR],
            start_date__lte=today,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        .exclude(profile=actor)
        .values_list("profile_id", flat=True)
        .distinct()
    )
    return list(Profile.objects.filter(pk__in=recipient_ids, is_active=True))


def update_own_profile(
    actor: Profile, *, field: str, proposed_value: str, operation_key: str | None
) -> CommandResult:
    """Directly update an own profile field (no request/approval flow).

    DoSA Head: can directly edit profile fields with no notification.
    EB/Faculty Advisor: can directly edit personal/contact info (ORDINARY_FIELDS) with
    notification to other EB profiles and the advisor of that club.
    """

    def handler() -> CommandResult:
        if actor is None or not actor.is_active:
            raise PermissionDeniedError()
        is_dosa = actor.access_category == AccessCategory.DOSA_HEAD
        is_eb_or_advisor = actor.access_category in {
            AccessCategory.EB_MEMBER,
            AccessCategory.FACULTY_ADVISOR,
        }

        if field not in DIRECT_EDIT_FIELDS and field not in ORDINARY_FIELDS:
            raise ValidationFailed(
                field_errors={"field": ["This field cannot be edited here."]}
            )

        if is_dosa:
            allowed = field in DIRECT_EDIT_FIELDS
        elif is_eb_or_advisor:
            allowed = field in ORDINARY_FIELDS
        else:
            # Fall back to request flow for other roles
            raise PermissionDeniedError(
                "Use the request flow for this profile type."
            )
        if not allowed:
            raise PermissionDeniedError("You cannot edit this field directly.")

        value = (proposed_value or "").strip()
        if field == "iub_email":
            value = normalize_email(value)
        errors = _field_value_errors(field, value, actor.access_category)
        if not value and field not in {
            "designation",
            "personal_email",
            "personal_phone",
            "emergency_phone",
            "permanent_address",
            "temporary_address",
        }:
            errors = errors or ["Enter a value."]
        if errors:
            raise ValidationFailed(field_errors={"proposed_value": errors})

        target = _lock_profile(actor.pk)
        current = str(getattr(target, field, "") or "")
        if current == value:
            raise ValidationFailed(
                field_errors={"proposed_value": ["The value matches the saved value."]}
            )
        if field == "iub_email":
            if not is_eligible_iub_address(value):
                raise ValidationFailed(
                    field_errors={"proposed_value": ["Enter a valid email address."]}
                )
            if Profile.objects.filter(iub_email__iexact=value).exclude(pk=target.pk).exists():
                raise ValidationFailed(
                    field_errors={"proposed_value": ["Another profile already uses that IUB address."]}
                )
            target.oidc_issuer = ""
            target.oidc_subject = ""

        setattr(target, field, value)
        target.revision += 1
        target.save()
        audit.record(
            actor,
            "profile.direct_update",
            target,
            before={field: current},
            after={field: value},
            revision=target.revision,
        )

        if is_eb_or_advisor and field in ORDINARY_FIELDS:
            recipients = _club_notification_recipients(target)
            if recipients:
                label = ORDINARY_FIELDS.get(field, field)
                detail = "" if field in SENSITIVE_FIELDS else f" New value: {value}."
                notify(
                    recipients,
                    event_key=f"profile_direct:{target.pk}:{field}:{target.revision}",
                    event_type="profile.updated",
                    object_type="accounts.profile",
                    object_id=target.pk,
                    subject=f"Profile updated: {target.full_name}",
                    message=f"{target.full_name} updated their {label}.{detail}",
                    link="/accounts/directory/",
                )

        return CommandResult("accounts.profile", target.pk, "updated")

    return execute(
        actor=actor,
        action="profile.direct_update",
        operation_key=operation_key,
        payload={"field": field, "value": proposed_value},
        handler=handler,
    )


def decide_profile_change(
    actor: Profile, request_id: int, *, approve: bool, reason: str = "", operation_key: str | None
) -> CommandResult:
    """Approve or decline a pending correction once (FR-IAM-05).

    Ordinary corrections need ``accounts.review_profile_change``; protected ones need
    ``accounts.manage_grants`` and the System Admin rule for Head/Admin profiles. An approved
    ordinary or IUB-address change applies once, recording old and new values; role, assignment,
    tenure and privilege requests are applied through their own controlled screens.
    Stale safety: a request already decided, or whose saved value changed during review, raises
    ConflictError carrying the current state instead of applying anything.
    """

    def handler() -> CommandResult:
        try:
            req = ProfileChangeRequest.objects.select_for_update().get(pk=request_id)
        except ProfileChangeRequest.DoesNotExist as exc:
            raise NotFoundError() from exc
        needed = (
            Action.PROFILE_REVIEW
            if req.route == ProfileChangeRequest.Route.ORDINARY
            else Action.ACCOUNTS_MANAGE_GRANTS
        )
        _require_active_actor(actor, needed)
        if req.status != ProfileChangeRequest.Status.PENDING:
            raise ConflictError(
                "This request was already decided.",
                current_state={
                    "status": req.status,
                    "decided_by": getattr(req.decided_by, "full_name", ""),
                },
            )
        if req.profile_id == actor.pk:
            raise PermissionDeniedError("You cannot decide your own request.")
        target = _lock_profile(req.profile_id)
        if req.route == ProfileChangeRequest.Route.PROTECTED:
            _require_category_authority(actor, target.access_category)
        before: dict = {}
        after: dict = {}
        if approve and hasattr(target, req.field) and req.field != "access_category":
            current = str(getattr(target, req.field) or "")
            if current != req.original_value:
                raise ConflictError(
                    "The saved value changed during review. Review the current value first.",
                    current_state={"field": req.field, "current_value": current},
                )
            if req.field == "iub_email":
                email = req.proposed_value
                if not is_eligible_iub_address(email):
                    raise ValidationFailed("Enter a valid email address.")
                if Profile.objects.filter(iub_email__iexact=email).exclude(pk=target.pk).exists():
                    raise ValidationFailed("Another profile already uses that IUB address.")
                target.oidc_issuer = ""
                target.oidc_subject = ""
            before = {req.field: current}
            after = {req.field: req.proposed_value}
            setattr(target, req.field, req.proposed_value)
            target.revision += 1
            target.save()
        req.status = (
            ProfileChangeRequest.Status.APPROVED
            if approve
            else ProfileChangeRequest.Status.DECLINED
        )
        req.decided_by = actor
        req.decided_at = clock.now()
        req.decision_reason = reason
        req.save(update_fields=["status", "decided_by", "decided_at", "decision_reason"])
        audit.record(
            actor,
            "profile_change.approve" if approve else "profile_change.decline",
            req,
            before=before,
            after=after,
            reason=reason,
        )
        if before:
            audit.record(
                actor,
                "profile.update",
                target,
                before=before,
                after=after,
                reason=f"Profile change request #{req.pk}",
                revision=target.revision,
            )
        notify(
            [target],
            event_key=f"profile_change:{req.pk}:decided",
            event_type="profile_change.decided",
            object_type="accounts.profilechangerequest",
            object_id=req.pk,
            subject=f"Profile correction request #{req.pk} {req.get_status_display().lower()}",
            message=f"Your request was {req.get_status_display().lower()}."
            + (f" Reason: {reason}" if reason else ""),
            link="/profile/",
        )
        return CommandResult("accounts.profilechangerequest", req.pk, req.status)

    return execute(
        actor=actor,
        action="profile_change.decide",
        operation_key=operation_key,
        payload={"request": request_id, "approve": approve, "reason": reason},
        handler=handler,
    )


# --------------------------------------------------------------------------- sign-in


def sign_in_with_identity(identity: VerifiedIdentity) -> Profile:
    """Match a verified IUB Google identity to one active profile (FR-IAM-01, TR 4.1).

    The first sign-in binds the stable issuer and subject; later sign-ins use that binding.
    Raises SignInDenied with no detail for unverified email, an ineligible domain, a missing,
    inactive or demonstration profile, or a profile already bound to another Google subject.
    """
    email = normalize_email(identity.email)
    if not identity.email_verified or not identity.subject or not identity.issuer:
        raise SignInDenied()
    _domain = email.rpartition("@")[2]
    if not _domain:
        raise SignInDenied()
    with transaction.atomic():
        profile = (
            Profile.objects.select_for_update()
            .filter(oidc_issuer=identity.issuer, oidc_subject=identity.subject)
            .first()
        )
        if profile is None:
            profile = Profile.objects.select_for_update().filter(iub_email__iexact=email).first()
            if profile is None or profile.oidc_subject:
                raise SignInDenied()
            if not profile.is_active or profile.is_demo:
                raise SignInDenied()
            profile.oidc_issuer = identity.issuer
            profile.oidc_subject = identity.subject
            profile.save(update_fields=["oidc_issuer", "oidc_subject"])
            audit.record(profile, "profile.oidc_bound", profile, after={"issuer": identity.issuer})
        if not profile.is_active or profile.is_demo:
            raise SignInDenied()
        audit.record(profile, "session.sign_in", profile)
        return profile

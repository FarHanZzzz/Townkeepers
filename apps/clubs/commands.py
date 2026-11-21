"""Club commands (FR-CLB-01 to FR-CLB-05, FR-CLB-07, FR-IAM-04; UC-06 to UC-08).

Lock order: Club row, then Term row, then Assignment rows. Every command that changes terms or
appointments locks the club first so overlapping-term and single-holder checks serialize.
"""

from __future__ import annotations

import re
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db.models import Q

from apps.platform_core import audit, clock
from apps.platform_core.access import AccessCategory, Action, can, require
from apps.platform_core.exceptions import (
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    StaleRevisionError,
    ValidationFailed,
)
from apps.platform_core.protocol import CommandResult, execute

from .models import ArchiveCorrection, Assignment, Club, Term

PHONE = re.compile(r"\+?[0-9][0-9 \-]{5,18}")


def _lock(model, pk):
    try:
        return model.objects.select_for_update().get(pk=pk)
    except model.DoesNotExist as exc:
        raise NotFoundError() from exc


def _check_revision(obj, expected):
    if expected is not None and obj.revision != expected:
        raise StaleRevisionError(current_state={"revision": obj.revision})


def _require_open(club: Club) -> None:
    if club.is_archived:
        raise InvalidTransitionError("This club is archived and cannot start new work.")


# --------------------------------------------------------------------------- register


def register_club(
    actor, *, name: str, short_code: str, institutional_profile: str = "", operation_key: str | None
) -> CommandResult:
    """Add a club to the official register (FR-CLB-01). Actor: ``clubs.manage`` (DoSA Head)."""

    def handler():
        require(actor, Action.CLUBS_MANAGE)
        errors = {}
        if not name.strip():
            errors["name"] = ["Enter the official name."]
        if not re.fullmatch(r"[A-Za-z0-9\-]{2,20}", short_code or ""):
            errors["short_code"] = ["Use 2 to 20 letters, digits or dashes."]
        if Club.objects.filter(name__iexact=name.strip()).exists():
            errors["name"] = ["A club with this name already exists."]
        if Club.objects.filter(short_code__iexact=short_code).exists():
            errors["short_code"] = ["This short code is already used."]
        if errors:
            raise ValidationFailed(field_errors=errors)
        club = Club.objects.create(
            name=name.strip(),
            short_code=short_code.upper(),
            institutional_profile=institutional_profile,
            created_at=clock.now(),
        )
        audit.record(
            actor, "club.register", club, after={"name": club.name, "short_code": club.short_code}
        )
        return CommandResult("clubs.club", club.pk, "registered")

    return execute(
        actor=actor,
        action="club.register",
        operation_key=operation_key,
        payload={"name": name, "code": short_code, "profile": institutional_profile},
        handler=handler,
    )


def update_club_identity(
    actor,
    club_id: int,
    *,
    name: str,
    institutional_profile: str,
    expected_revision: int | None,
    operation_key: str | None,
) -> CommandResult:
    """Rename or update the official profile while keeping the same club ID (FR-CLB-01)."""

    def handler():
        club = _lock(Club, club_id)
        require(actor, Action.CLUBS_MANAGE, club)
        _check_revision(club, expected_revision)
        if not name.strip():
            raise ValidationFailed(field_errors={"name": ["Enter the official name."]})
        if Club.objects.filter(name__iexact=name.strip()).exclude(pk=club.pk).exists():
            raise ValidationFailed(field_errors={"name": ["A club with this name already exists."]})
        before = {"name": club.name, "institutional_profile": club.institutional_profile}
        club.name = name.strip()
        club.institutional_profile = institutional_profile
        club.revision += 1
        club.save()
        audit.record(
            actor,
            "club.update_identity",
            club,
            before=before,
            after={"name": club.name, "institutional_profile": club.institutional_profile},
            revision=club.revision,
        )
        return CommandResult("clubs.club", club.pk, "updated")

    return execute(
        actor=actor,
        action="club.update_identity",
        operation_key=operation_key,
        payload={"club": club_id, "name": name, "profile": institutional_profile},
        handler=handler,
    )


def archive_club(
    actor, club_id: int, *, reason: str, expected_revision: int | None, operation_key: str | None
) -> CommandResult:
    """Archive a club. Earlier terms, events, memos and finance stay linked and viewable (FR-CLB-01).

    A failed archive leaves the current status; archiving never deletes records (BR-07).
    """

    def handler():
        club = _lock(Club, club_id)
        require(actor, Action.CLUBS_MANAGE, club)
        _check_revision(club, expected_revision)
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter a reason."]})
        if club.is_archived:
            raise ConflictError("The club is already archived.")
        club.status = Club.Status.ARCHIVED
        club.archived_at = clock.now()
        club.revision += 1
        club.save()
        audit.record(
            actor,
            "club.archive",
            club,
            before={"status": "active"},
            after={"status": "archived"},
            reason=reason,
            revision=club.revision,
        )
        return CommandResult("clubs.club", club.pk, "archived")

    return execute(
        actor=actor,
        action="club.archive",
        operation_key=operation_key,
        payload={"club": club_id, "reason": reason},
        handler=handler,
    )


def _contact_errors(text: str) -> list[str]:
    errors = []
    for number, line in enumerate((text or "").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        emails = [w for w in re.split(r"[\s,;]+", line) if "@" in w]
        for email in emails:
            try:
                validate_email(email)
            except DjangoValidationError:
                errors.append(f"Line {number}: '{email}' is not a valid email address.")
        if not emails and not PHONE.search(line):
            errors.append(f"Line {number}: include an email address or phone number.")
    return errors


def update_internal_profile(
    actor,
    club_id: int,
    *,
    description: str,
    internal_contacts: str,
    expected_revision: int | None,
    operation_key: str | None,
) -> CommandResult:
    """EB update of the internal club page (FR-CLB-07). Official identity and status are untouched."""

    def handler():
        club = _lock(Club, club_id)
        if not can(actor, Action.CLUBS_EDIT_PROFILE, club):
            raise (
                NotFoundError()
                if not can(actor, Action.CLUBS_VIEW, club)
                else PermissionDeniedError()
            )
        _require_open(club)
        _check_revision(club, expected_revision)
        errors = _contact_errors(internal_contacts)
        if errors:
            raise ValidationFailed(field_errors={"internal_contacts": errors})
        before = {"description": club.description, "internal_contacts": club.internal_contacts}
        club.description = description
        club.internal_contacts = internal_contacts
        club.revision += 1
        club.save()
        audit.record(
            actor,
            "club.update_internal_profile",
            club,
            before=before,
            after={"description": description, "internal_contacts": internal_contacts},
            revision=club.revision,
        )
        return CommandResult("clubs.club", club.pk, "updated")

    return execute(
        actor=actor,
        action="club.update_internal_profile",
        operation_key=operation_key,
        payload={"club": club_id, "d": description, "c": internal_contacts},
        handler=handler,
    )


# --------------------------------------------------------------------------- terms


def _overlapping_terms(club: Club, start: date, end: date, exclude_pk=None):
    qs = club.terms.exclude(status=Term.Status.CLOSED).filter(
        start_date__lte=end, end_date__gte=start
    )
    return qs.exclude(pk=exclude_pk) if exclude_pk else qs


def create_term(
    actor,
    club_id: int,
    *,
    label: str,
    start_date: date,
    end_date: date,
    transition_approved: bool = False,
    operation_key: str | None,
) -> CommandResult:
    """Record an upcoming EB term (FR-CLB-02). It grants no access until activated and started."""

    def handler():
        club = _lock(Club, club_id)
        require(actor, Action.CLUBS_MANAGE, club)
        _require_open(club)
        errors = {}
        if not label.strip():
            errors["label"] = ["Enter a term label, for example 2026-27."]
        if end_date < start_date:
            errors["end_date"] = ["The end date cannot be before the start date."]
        elif _overlapping_terms(club, start_date, end_date).exists() and not transition_approved:
            errors["start_date"] = [
                "These dates overlap another current or upcoming term. "
                "Record an approved transition period to allow it."
            ]
        if errors:
            raise ValidationFailed(field_errors=errors)
        term = Term.objects.create(
            club=club,
            label=label.strip(),
            start_date=start_date,
            end_date=end_date,
            transition_approved=transition_approved,
            created_by=actor,
            created_at=clock.now(),
        )
        audit.record(
            actor,
            "term.create",
            term,
            after={
                "label": term.label,
                "start": start_date,
                "end": end_date,
                "transition": transition_approved,
            },
        )
        return CommandResult("clubs.term", term.pk, "created")

    return execute(
        actor=actor,
        action="term.create",
        operation_key=operation_key,
        payload={
            "club": club_id,
            "label": label,
            "start": start_date,
            "end": end_date,
            "transition": transition_approved,
        },
        handler=handler,
    )


def activate_term(actor, term_id: int, *, operation_key: str | None) -> CommandResult:
    """Make an upcoming term the club's active term (FR-CLB-02).

    Blocked while another term is active (close it first) and when today is outside the term's
    dates, so incoming members never gain early access.
    """

    def handler():
        term = _lock(Term, term_id)
        club = _lock(Club, term.club_id)
        require(actor, Action.CLUBS_MANAGE, club)
        _require_open(club)
        if term.status != Term.Status.UPCOMING:
            raise InvalidTransitionError("Only an upcoming term can be activated.")
        today = clock.local_today()
        if not term.start_date <= today <= term.end_date:
            raise ValidationFailed("A term can be activated only between its start and end dates.")
        if club.terms.filter(status=Term.Status.ACTIVE).exists():
            raise ConflictError("Close the current active term before activating its successor.")
        term.status = Term.Status.ACTIVE
        term.revision += 1
        term.save(update_fields=["status", "revision"])
        audit.record(
            actor, "term.activate", term, before={"status": "upcoming"}, after={"status": "active"}
        )
        return CommandResult("clubs.term", term.pk, "activated")

    return execute(
        actor=actor,
        action="term.activate",
        operation_key=operation_key,
        payload={"term": term_id},
        handler=handler,
    )


def close_term(actor, term_id: int, *, reason: str, operation_key: str | None) -> CommandResult:
    """Close a term: linked EB access ends; historical records stay attributed (FR-CLB-02, FR-IAM-04)."""

    def handler():
        term = _lock(Term, term_id)
        club = _lock(Club, term.club_id)
        require(actor, Action.CLUBS_MANAGE, club)
        if term.status == Term.Status.CLOSED:
            raise ConflictError("This term is already closed.")
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter a reason."]})
        today = clock.local_today()
        now = clock.now()
        open_assignments = term.assignments.select_for_update().filter(ended_at__isnull=True)
        for a in open_assignments:
            a.end_date = max(a.start_date, min(a.end_date or today, today))
            a.ended_at = now
            a.ended_by = actor
            a.end_reason = f"Term closed: {reason}"
            a.revision += 1
            a.save()
        before = term.status
        term.status = Term.Status.CLOSED
        term.closed_at = now
        term.closed_by = actor
        term.revision += 1
        term.save()
        audit.record(
            actor,
            "term.close",
            term,
            before={"status": before},
            after={"status": "closed"},
            reason=reason,
        )
        return CommandResult("clubs.term", term.pk, "closed")

    return execute(
        actor=actor,
        action="term.close",
        operation_key=operation_key,
        payload={"term": term_id, "reason": reason},
        handler=handler,
    )


# --------------------------------------------------------------------------- assignments


def _overlaps(qs, start: date, end: date | None):
    far = date(9999, 12, 31)
    return qs.filter(start_date__lte=end or far).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=start)
    )


def appoint_member(
    actor,
    term_id: int,
    *,
    profile_id: int,
    designation: str,
    responsibilities: str = "",
    start_date: date,
    end_date: date | None = None,
    operation_key: str | None,
) -> CommandResult:
    """Appoint a provisioned EB member to a typed position in a term (FR-CLB-03, FR-IAM-04).

    The title is descriptive; access still follows the member's grants and these dates. Duplicate
    or overlapping appointments, a second holder of a single-holder post, dates outside the term,
    and non-EB or inactive profiles are returned for correction before anything is saved.
    """
    from apps.accounts.models import Profile

    def handler():
        term = _lock(Term, term_id)
        club = _lock(Club, term.club_id)
        require(actor, Action.CLUBS_MANAGE, club)
        _require_open(club)
        if term.status == Term.Status.CLOSED:
            raise InvalidTransitionError("Appointments cannot be added to a closed term.")
        profile = Profile.objects.filter(pk=profile_id).first()
        errors: dict[str, list[str]] = {}
        if (
            profile is None
            or not profile.is_active
            or profile.access_category != AccessCategory.EB_MEMBER
        ):
            errors["profile"] = [
                "Choose an active profile with the Club EB member access category."
            ]
        title = designation.strip()
        if not title:
            errors["designation"] = ["Type the position title."]
        if end_date and end_date < start_date:
            errors["end_date"] = ["The end date cannot be before the start date."]
        if start_date < term.start_date or (end_date or term.end_date) > term.end_date:
            errors["start_date"] = [
                f"Dates must fall within the term ({term.start_date:%d %b %Y} to {term.end_date:%d %b %Y})."
            ]
        if not errors:
            active = term.assignments.filter(kind=Assignment.Kind.EB_MEMBER, ended_at__isnull=True)
            if _overlaps(
                active.filter(profile=profile, designation__iexact=title), start_date, end_date
            ).exists():
                errors["designation"] = ["This member already holds this position for these dates."]
            elif (
                title.lower() in settings.SINGLE_HOLDER_DESIGNATIONS
                and _overlaps(
                    active.filter(designation__iexact=title), start_date, end_date
                ).exists()
            ):
                errors["designation"] = [f"{title} already has an active holder in this term."]
        if errors:
            raise ValidationFailed(field_errors=errors)
        assignment = Assignment.objects.create(
            profile=profile,
            kind=Assignment.Kind.EB_MEMBER,
            club=club,
            term=term,
            designation=title,
            responsibilities=responsibilities,
            start_date=start_date,
            end_date=end_date,
            granted_by=actor,
            created_at=clock.now(),
        )
        audit.record(
            actor,
            "assignment.appoint",
            assignment,
            after={
                "profile": profile.pk,
                "term": term.pk,
                "designation": title,
                "start": start_date,
                "end": end_date,
            },
        )
        return CommandResult("clubs.assignment", assignment.pk, "appointed")

    return execute(
        actor=actor,
        action="assignment.appoint",
        operation_key=operation_key,
        payload={
            "term": term_id,
            "profile": profile_id,
            "designation": designation,
            "r": responsibilities,
            "start": start_date,
            "end": end_date,
        },
        handler=handler,
    )


def assign_advisor(
    actor,
    club_id: int,
    *,
    profile_id: int,
    start_date: date,
    end_date: date | None = None,
    operation_key: str | None,
) -> CommandResult:
    """Link a Faculty Advisor to the club they advise (FR-IAM-04)."""
    from apps.accounts.models import Profile

    def handler():
        club = _lock(Club, club_id)
        require(actor, Action.CLUBS_MANAGE, club)
        _require_open(club)
        profile = Profile.objects.filter(pk=profile_id).first()
        errors: dict[str, list[str]] = {}
        if (
            profile is None
            or not profile.is_active
            or profile.access_category != AccessCategory.FACULTY_ADVISOR
        ):
            errors["profile"] = [
                "Choose an active profile with the Faculty Advisor access category."
            ]
        if end_date and end_date < start_date:
            errors["end_date"] = ["The end date cannot be before the start date."]
        if (
            not errors
            and _overlaps(
                club.assignments.filter(
                    kind=Assignment.Kind.FACULTY_ADVISOR, profile=profile, ended_at__isnull=True
                ),
                start_date,
                end_date,
            ).exists()
        ):
            errors["profile"] = ["This advisor already has an overlapping assignment for the club."]
        if errors:
            raise ValidationFailed(field_errors=errors)
        assignment = Assignment.objects.create(
            profile=profile,
            kind=Assignment.Kind.FACULTY_ADVISOR,
            club=club,
            start_date=start_date,
            end_date=end_date,
            designation="Faculty Advisor",
            granted_by=actor,
            created_at=clock.now(),
        )
        audit.record(
            actor,
            "assignment.assign_advisor",
            assignment,
            after={"profile": profile.pk, "club": club.pk, "start": start_date, "end": end_date},
        )
        return CommandResult("clubs.assignment", assignment.pk, "assigned")

    return execute(
        actor=actor,
        action="assignment.assign_advisor",
        operation_key=operation_key,
        payload={"club": club_id, "profile": profile_id, "start": start_date, "end": end_date},
        handler=handler,
    )


def end_assignment(
    actor, assignment_id: int, *, end_date: date, reason: str, operation_key: str | None
) -> CommandResult:
    """End one assignment; the person's other assignments keep their own access (FR-IAM-04)."""

    def handler():
        assignment = _lock(Assignment, assignment_id)
        require(actor, Action.CLUBS_MANAGE, assignment.club)
        if assignment.ended_at:
            raise ConflictError("This assignment has already ended.")
        if end_date < assignment.start_date:
            raise ValidationFailed(
                field_errors={"end_date": ["The end date cannot be before the start date."]}
            )
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter a reason."]})
        before = {"end_date": assignment.end_date}
        assignment.end_date = end_date
        assignment.ended_at = clock.now()
        assignment.ended_by = actor
        assignment.end_reason = reason
        assignment.revision += 1
        assignment.save()
        audit.record(
            actor,
            "assignment.end",
            assignment,
            before=before,
            after={"end_date": end_date},
            reason=reason,
        )
        return CommandResult("clubs.assignment", assignment.pk, "ended")

    return execute(
        actor=actor,
        action="assignment.end",
        operation_key=operation_key,
        payload={"a": assignment_id, "end": end_date, "reason": reason},
        handler=handler,
    )


# --------------------------------------------------------------------------- archive corrections

CORRECTABLE = {"term": {"label"}, "assignment": {"designation", "responsibilities"}}


def correct_archive_record(
    actor,
    *,
    object_type: str,
    object_id: int,
    field: str,
    new_value: str,
    reason: str,
    based_on_revision: int,
    operation_key: str | None,
) -> CommandResult:
    """Correct a closed term or past appointment, keeping the previous value (FR-CLB-05).

    A correction against a superseded revision raises StaleRevisionError so the editor reviews the
    latest record first; the original value is preserved in ``ArchiveCorrection`` and the audit log.
    """

    def handler():
        if field not in CORRECTABLE.get(object_type, set()):
            raise ValidationFailed(field_errors={"field": ["This field cannot be corrected here."]})
        record = _lock(Term if object_type == "term" else Assignment, object_id)
        term = record if object_type == "term" else record.term
        if term is not None:
            require(actor, Action.CLUBS_CORRECT_ARCHIVE, term.club)
        if term is None or term.status != Term.Status.CLOSED:
            raise InvalidTransitionError(
                "Only records of closed terms are corrected through the archive."
            )
        if record.revision != based_on_revision:
            raise StaleRevisionError(
                current_state={"revision": record.revision, field: getattr(record, field)}
            )
        if not reason.strip():
            raise ValidationFailed(
                field_errors={"reason": ["Enter the reason for the correction."]}
            )
        if not new_value.strip():
            raise ValidationFailed(field_errors={"new_value": ["Enter the corrected value."]})
        previous = getattr(record, field)
        ArchiveCorrection.objects.create(
            object_type=object_type,
            object_id=record.pk,
            field=field,
            previous_value=previous,
            new_value=new_value,
            reason=reason,
            editor=actor,
            corrected_at=clock.now(),
            based_on_revision=based_on_revision,
        )
        setattr(record, field, new_value)
        record.revision += 1
        record.save()
        audit.record(
            actor,
            "archive.correct",
            record,
            before={field: previous},
            after={field: new_value},
            reason=reason,
            revision=record.revision,
        )
        return CommandResult(f"clubs.{object_type}", record.pk, "corrected")

    return execute(
        actor=actor,
        action="archive.correct",
        operation_key=operation_key,
        payload={
            "t": object_type,
            "id": object_id,
            "f": field,
            "v": new_value,
            "r": reason,
            "rev": based_on_revision,
        },
        handler=handler,
    )

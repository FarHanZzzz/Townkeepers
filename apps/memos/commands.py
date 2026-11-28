"""Memo commands (FR-MEM-01 to FR-MEM-13; UC-18 to UC-26).

Lock order: Memo row, then its current MemoVersion, then SignatureTask rows. Every transition
locks the memo first, so a send, a decision and a withdrawal on the same memo serialize and only
the first valid transition commits (FR-MEM-06, FR-MEM-08, FR-MEM-13). Unique constraints on
decisions and signatures are the database backstop for the same rule.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date

from django.conf import settings

from apps.platform_core import audit, clock, files
from apps.platform_core.access import (
    AccessCategory,
    Action,
    can,
    effective_actions,
    is_assigned_advisor,
)
from apps.platform_core.exceptions import (
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    StaleRevisionError,
    ValidationFailed,
)
from apps.platform_core.notifications import notify
from apps.platform_core.policy import default_approval_deadline, effective_policy, submission_target
from apps.platform_core.protocol import CommandResult, execute

from .models import (
    REVIEW_STATUSES,
    Memo,
    MemoAttachment,
    MemoDecision,
    MemoStatus,
    MemoTemplate,
    MemoVersion,
    Signature,
    SignatureTask,
    Stage,
    TemplateVersion,
)

MEMO_FIELDS = {
    "school": "School",
    "department": "Department",
    "to_line": "To",
    "through_line": "Through",
    "from_line": "From",
    "memo_date": "Memo date",
    "subject": "Subject",
    "body": "Body",
    "contact": "Contact",
}
ALWAYS_REQUIRED = ("to_line", "through_line", "from_line", "memo_date", "subject", "body")
REQUIRED_SIGNATURE_AREAS = {"advisor", "dosa"}
STAGE_FOR_STATUS = {
    MemoStatus.PENDING_ADVISOR: Stage.ADVISOR,
    MemoStatus.PENDING_ADDITIONAL: Stage.ADDITIONAL,
    MemoStatus.PENDING_DOSA: Stage.DOSA,
}
WITHDRAWABLE = (MemoStatus.DRAFT, MemoStatus.PENDING_ADVISOR)


@dataclass(frozen=True)
class MemoDraftInput:
    """Typed memo text (Appendix D). Nothing is calculated or prefilled (FR-MEM-02)."""

    school: str = ""
    department: str = ""
    to_line: str = ""
    through_line: str = ""
    from_line: str = ""
    memo_date: date | None = None
    subject: str = ""
    body: str = ""
    contact: str = ""


@dataclass(frozen=True)
class SignatureInput:
    """A drawn PNG data URL or a typed name, plus the signer's explicit attestation."""

    method: str = "drawn"
    data_url: str = ""
    typed_name: str = ""
    attest: bool = False


@dataclass(frozen=True)
class TemplateInput:
    """Template definition saved as an immutable TemplateVersion (FR-MEM-01)."""

    label: str
    instructions: str = ""
    required_fields: tuple[str, ...] = ()
    required_attachments: tuple[dict, ...] = ()
    signature_areas: tuple[str, ...] = ("advisor", "dosa")
    requires_budget: bool = False
    dosa_only: bool = False
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- helpers


def _lock_memo(memo_id: int) -> Memo:
    try:
        return (
            Memo.objects.select_for_update(of=("self",))
            .select_related("club", "event", "template_version")
            .get(pk=memo_id)
        )
    except Memo.DoesNotExist as exc:
        raise NotFoundError() from exc


def _require_author(actor, memo: Memo) -> None:
    if not can(actor, Action.MEMOS_VIEW, memo.club):
        raise NotFoundError()
    if not can(actor, Action.MEMOS_AUTHOR, memo.club):
        raise PermissionDeniedError()


def _advisors(club):
    from apps.accounts.models import Profile

    return [
        p
        for p in Profile.objects.filter(
            assignments__club=club, access_category=AccessCategory.FACULTY_ADVISOR, is_active=True
        ).distinct()
        if is_assigned_advisor(p, club)
    ]


def _eb_participants(memo: Memo):
    from apps.accounts.models import Profile

    people = [
        p
        for p in Profile.objects.filter(
            assignments__club=memo.club, access_category=AccessCategory.EB_MEMBER, is_active=True
        ).distinct()
        if can(p, Action.MEMOS_AUTHOR, memo.club)
    ]
    if memo.author.is_active and memo.author not in people:
        people.insert(0, memo.author)
    return people


def _heads():
    from apps.accounts.models import Profile

    return [
        p
        for p in Profile.objects.filter(access_category=AccessCategory.DOSA_HEAD, is_active=True)
        if Action.MEMOS_HEAD_APPROVE in effective_actions(p)
    ]


def _link(memo: Memo) -> str:
    return f"/memos/{memo.pk}/"


def _canonical(data: dict) -> str:
    return json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))


def _stale(
    memo: Memo, message: str = "This memo changed since you opened it."
) -> StaleRevisionError:
    version = memo.current_version
    last = version.decisions.select_related("actor").last() if version else None
    return StaleRevisionError(
        message,
        current_state={
            "status": memo.get_status_display(),
            "version": version.number if version else None,
            **(
                {"last_decision": f"{last.get_decision_display()} by {last.actor.full_name}"}
                if last
                else {}
            ),
        },
    )


# --------------------------------------------------------------------------- templates (FR-MEM-01)


def _validate_template(data: TemplateInput) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if not data.label.strip():
        errors["label"] = ["Enter the DoSA template label."]
    unknown = set(data.required_fields) - set(MEMO_FIELDS)
    if unknown:
        errors["required_fields"] = ["Unknown fields: " + ", ".join(sorted(unknown))]
    for item in data.required_attachments:
        if not str(item.get("key", "")).strip() or not str(item.get("label", "")).strip():
            errors["required_attachments"] = ["Each attachment needs a key and a label."]
    return errors


def create_template(actor, data: TemplateInput, *, operation_key: str | None) -> CommandResult:
    """Create an inactive template with version 1 (FR-MEM-01). Actor: ``memos.manage_templates``."""

    def handler():
        if not can(actor, Action.MEMOS_MANAGE_TEMPLATES):
            raise PermissionDeniedError()
        errors = _validate_template(data)
        if MemoTemplate.objects.filter(label__iexact=data.label.strip()).exists():
            errors["label"] = ["A template with this label already exists."]
        if errors:
            raise ValidationFailed(field_errors=errors)
        template = MemoTemplate.objects.create(
            label=data.label.strip(),
            dosa_only=data.dosa_only,
            created_by=actor,
            created_at=clock.now(),
        )
        version = _new_template_version(template, data, actor)
        audit.record(
            actor,
            "memo_template.create",
            template,
            after={"version": version.number, "dosa_only": template.dosa_only},
        )
        return CommandResult("memos.memotemplate", template.pk, "created")

    return execute(
        actor=actor,
        action="memo_template.create",
        operation_key=operation_key,
        payload=asdict(data),
        handler=handler,
    )


def _new_template_version(template: MemoTemplate, data: TemplateInput, actor) -> TemplateVersion:
    number = (
        template.versions.order_by("-number").values_list("number", flat=True).first() or 0
    ) + 1
    version = TemplateVersion.objects.create(
        template=template,
        number=number,
        label=data.label.strip(),
        instructions=data.instructions,
        required_fields=sorted(set(data.required_fields) | set(ALWAYS_REQUIRED)),
        required_attachments=[dict(a) for a in data.required_attachments],
        signature_areas=list(dict.fromkeys(data.signature_areas)),
        requires_budget=data.requires_budget,
        created_by=actor,
        created_at=clock.now(),
    )
    template.current_version = version
    template.label = version.label
    template.dosa_only = data.dosa_only
    if template.is_active and not set(version.signature_areas) >= REQUIRED_SIGNATURE_AREAS:
        template.is_active = False
    template.save()
    return version


def revise_template(
    actor, template_id: int, data: TemplateInput, *, operation_key: str | None
) -> CommandResult:
    """Save a template change as a new version; memos keep the version they used (AC-13)."""

    def handler():
        if not can(actor, Action.MEMOS_MANAGE_TEMPLATES):
            raise PermissionDeniedError()
        try:
            template = MemoTemplate.objects.select_for_update().get(pk=template_id)
        except MemoTemplate.DoesNotExist as exc:
            raise NotFoundError() from exc
        errors = _validate_template(data)
        if (
            MemoTemplate.objects.filter(label__iexact=data.label.strip())
            .exclude(pk=template.pk)
            .exists()
        ):
            errors["label"] = ["A template with this label already exists."]
        if errors:
            raise ValidationFailed(field_errors=errors)
        version = _new_template_version(template, data, actor)
        audit.record(
            actor,
            "memo_template.revise",
            template,
            after={"version": version.number, "dosa_only": template.dosa_only},
        )
        return CommandResult(
            "memos.memotemplate", template.pk, "revised", {"version": version.number}
        )

    return execute(
        actor=actor,
        action="memo_template.revise",
        operation_key=operation_key,
        payload={"t": template_id, **asdict(data)},
        handler=handler,
    )


def set_template_active(
    actor, template_id: int, *, active: bool, operation_key: str | None
) -> CommandResult:
    """Activate or deactivate a template (FR-MEM-01).

    Activation requires the Faculty Advisor and DoSA Head signature areas. Deactivation hides it
    from new drafts; drafts already started keep their template version.
    """

    def handler():
        if not can(actor, Action.MEMOS_MANAGE_TEMPLATES):
            raise PermissionDeniedError()
        try:
            template = (
                MemoTemplate.objects.select_for_update(of=("self",))
                .select_related("current_version")
                .get(pk=template_id)
            )
        except MemoTemplate.DoesNotExist as exc:
            raise NotFoundError() from exc
        if active and (
            template.current_version is None
            or not set(template.current_version.signature_areas) >= REQUIRED_SIGNATURE_AREAS
        ):
            raise ValidationFailed(
                "A template needs Faculty Advisor and DoSA Head signature areas before activation."
            )
        template.is_active = active
        template.save(update_fields=["is_active"])
        audit.record(
            actor, "memo_template.activate" if active else "memo_template.deactivate", template
        )
        return CommandResult(
            "memos.memotemplate", template.pk, "activated" if active else "deactivated"
        )

    return execute(
        actor=actor,
        action="memo_template.set_active",
        operation_key=operation_key,
        payload={"t": template_id, "active": active},
        handler=handler,
    )


# --------------------------------------------------------------------------- drafting (FR-MEM-02/03)


def create_memo(
    actor, *, event_id: int, template_id: int, operation_key: str | None
) -> CommandResult:
    """Start a draft from an active template for one of the author's club events (FR-MEM-02).

    One event-permission memo per event; a rejected memo continues as a revision of the same memo.
    """
    from apps.clubs.models import Term
    from apps.events.models import Event

    def handler():
        event = Event.objects.select_related("club").filter(pk=event_id).first()
        if event is None or event.club_id is None or not can(actor, Action.MEMOS_VIEW, event.club):
            raise NotFoundError()
        if not can(actor, Action.MEMOS_AUTHOR, event.club):
            raise PermissionDeniedError()
        if event.club.is_archived:
            raise InvalidTransitionError("This club is archived and cannot start new requests.")
        if event.status == Event.Status.CANCELLED:
            raise InvalidTransitionError("A cancelled event cannot start a memo.")
        template = (
            MemoTemplate.objects.select_related("current_version")
            .filter(pk=template_id, is_active=True)
            .first()
        )
        if template is None or template.current_version is None:
            raise ValidationFailed(field_errors={"template": ["Choose an active template."]})
        if template.dosa_only and actor.access_category != AccessCategory.DOSA_HEAD:
            raise NotFoundError()
        if (
            Memo.objects.filter(event=event, kind=Memo.Kind.ORIGINAL)
            .exclude(status=MemoStatus.WITHDRAWN)
            .exists()
        ):
            raise ConflictError(
                "This event already has an event-permission memo. Open it from Memo Management."
            )
        term = Term.objects.filter(
            club=event.club, status=Term.Status.ACTIVE, assignments__profile=actor
        ).first()
        budget = getattr(event, "budget", None) if hasattr(event, "budget") else None
        now = clock.now()
        memo = Memo.objects.create(
            club=event.club,
            event=event,
            template_version=template.current_version,
            author=actor,
            author_term=term,
            budget_version=budget.latest if budget else None,
            created_at=now,
            updated_at=now,
        )
        audit.record(
            actor,
            "memo.create",
            memo,
            after={"event": event.pk, "template_version": template.current_version_id},
        )
        return CommandResult("memos.memo", memo.pk, "created")

    return execute(
        actor=actor,
        action="memo.create",
        operation_key=operation_key,
        payload={"event": event_id, "template": template_id},
        handler=handler,
    )


def save_memo_draft(
    actor,
    memo_id: int,
    data: MemoDraftInput,
    *,
    budget_version_id: int | None,
    expected_revision: int,
    operation_key: str | None,
) -> CommandResult:
    """Save the typed draft, complete or not (FR-MEM-02, FR-COM-08).

    Only Draft memos are editable; a submitted version is read-only through both reviews.
    A newer saved revision raises StaleRevisionError so the author is warned before overwriting.
    """
    from apps.finance.models import BudgetVersion

    def handler():
        memo = _lock_memo(memo_id)
        _require_author(actor, memo)
        if memo.status != MemoStatus.DRAFT:
            raise InvalidTransitionError(
                "Only a draft can be edited. Submitted versions are read-only."
            )
        if memo.revision != expected_revision:
            raise StaleRevisionError(
                "A newer draft was saved. Review it before saving again.",
                current_state={"revision": memo.revision},
            )
        budget = None
        if budget_version_id:
            budget = BudgetVersion.objects.filter(
                pk=budget_version_id, budget__event=memo.event
            ).first()
            if budget is None:
                raise ValidationFailed(
                    field_errors={"budget_version": ["Choose a budget version of this event."]}
                )
        before = {f: getattr(memo, f) for f in MEMO_FIELDS}
        for name, value in asdict(data).items():
            setattr(memo, name, value.strip() if isinstance(value, str) else value)
        memo.budget_version = budget
        memo.revision += 1
        memo.updated_at = clock.now()
        memo.save()
        audit.record(
            actor,
            "memo.save_draft",
            memo,
            before=before,
            after=asdict(data),
            revision=memo.revision,
        )
        return CommandResult("memos.memo", memo.pk, "saved", {"revision": memo.revision})

    return execute(
        actor=actor,
        action="memo.save_draft",
        operation_key=operation_key,
        payload={"m": memo_id, "rev": expected_revision, "b": budget_version_id, **asdict(data)},
        handler=handler,
    )


def upload_memo_attachment(actor, memo_id: int, *, key: str, uploaded_file) -> MemoAttachment:
    """Attach a file to a draft (FR-MEM-03, FR-COM-06). A replacement supersedes, never deletes."""
    from django.db import transaction

    with transaction.atomic():
        memo = _lock_memo(memo_id)
        _require_author(actor, memo)
        if memo.status != MemoStatus.DRAFT:
            raise InvalidTransitionError(
                "Attachments can be changed only while the memo is a draft."
            )
        allowed = {a["key"] for a in memo.template_version.required_attachments} | {"supporting"}
        if key not in allowed:
            raise ValidationFailed(
                field_errors={"attachment_key": ["Choose an attachment type from the list."]}
            )
        stored = files.store_upload(
            uploaded_file,
            uploaded_by=actor,
            purpose="memo_attachment",
            owner_type="memo_attachment",
            owner_id=memo.pk,
            club=memo.club,
            field="file",
        )
        now = clock.now()
        memo.attachments.filter(key=key, superseded_at__isnull=True).update(superseded_at=now)
        attachment = MemoAttachment.objects.create(
            memo=memo, key=key, file=stored, uploaded_by=actor, uploaded_at=now
        )
        memo.revision += 1
        memo.updated_at = now
        memo.save(update_fields=["revision", "updated_at"])
        audit.record(
            actor,
            "memo.attach",
            memo,
            after={"key": key, "file": str(stored.key), "sha256": stored.sha256},
        )
        return attachment


def submission_problems(memo: Memo) -> dict[str, list[str]]:
    """Blocking problems for Send to Faculty Advisor (FR-MEM-03, FR-MEM-05). Empty means ready."""
    from apps.events.models import Event

    errors: dict[str, list[str]] = {}
    tv = memo.template_version
    for name in sorted(set(tv.required_fields) | set(ALWAYS_REQUIRED)):
        if not getattr(memo, name):
            errors.setdefault(name, []).append(f"{MEMO_FIELDS[name]} is required before sending.")
    current = {a.key for a in memo.attachments.filter(superseded_at__isnull=True)}
    for item in tv.required_attachments:
        if item.get("required", True) and item["key"] not in current:
            errors.setdefault("attachments", []).append(f"Attach: {item['label']}.")
    if tv.requires_budget and memo.budget_version_id is None:
        errors.setdefault("budget_version", []).append("Link the event budget version.")
    event = memo.event
    if event.club_id != memo.club_id:
        errors.setdefault("event", []).append("The linked event belongs to another club.")
    if event.status == Event.Status.CANCELLED:
        errors.setdefault("event", []).append("The linked event is cancelled.")
    if not _advisors(memo.club):
        errors.setdefault("__all__", []).append(
            "No Faculty Advisor is assigned to this club. Ask DoSA to assign one."
        )
    return errors


def send_memo_to_advisor(
    actor, memo_id: int, *, expected_revision: int, operation_key: str | None
) -> CommandResult:
    """Freeze the draft as a new version and hand it to the assigned Advisor (FR-MEM-05/06/11).

    Transaction: event snapshot, frozen version (content hash, template, budget and policy
    versions), separate handoff/deadline/event-start dates, late flag, status change, audit and
    the Advisor notice commit together. A late submission is flagged, never blocked.
    Retry safety: a repeated click finds the memo no longer in Draft (InvalidTransitionError) or
    replays the operation key, so only one transition is recorded per version.
    """
    from apps.events.commands import snapshot_event
    from apps.events.models import Event

    def handler():
        memo = _lock_memo(memo_id)
        _require_author(actor, memo)
        if memo.status != MemoStatus.DRAFT:
            raise InvalidTransitionError(
                "This memo was already sent.", current_state={"status": memo.get_status_display()}
            )
        if memo.revision != expected_revision:
            raise StaleRevisionError(
                "A newer draft was saved. Review it before sending.",
                current_state={"revision": memo.revision},
            )
        if memo.club.is_archived:
            raise InvalidTransitionError("This club is archived and cannot start new requests.")
        errors = submission_problems(memo)
        if errors:
            raise ValidationFailed(field_errors=errors)
        event = Event.objects.select_for_update().get(pk=memo.event_id)
        today = clock.local_today()
        policy = effective_policy(today)
        target = submission_target(
            event.first_date,
            is_big=event.is_big,
            standard_lead_days=policy.standard_lead_days,
            big_event_lead_months=policy.big_event_lead_months,
        )
        event_version = snapshot_event(event, actor)
        attachments = [
            {
                "key": a.key,
                "file": str(a.file.key),
                "name": a.file.original_name,
                "sha256": a.file.sha256,
            }
            for a in memo.attachments.filter(superseded_at__isnull=True).select_related("file")
        ]
        snapshot = {
            "fields": {
                name: (
                    getattr(memo, name).isoformat() if name == "memo_date" else getattr(memo, name)
                )
                for name in MEMO_FIELDS
            },
            "template": {
                "label": memo.template_version.label,
                "version": memo.template_version.number,
            },
            "event": event_version.snapshot,
            "budget_version": memo.budget_version.number if memo.budget_version_id else None,
            "attachments": attachments,
            "kind": memo.kind,
            "amends": memo.amends.reference if memo.amends_id else None,
        }
        now = clock.now()
        version = MemoVersion.objects.create(
            memo=memo,
            number=memo.next_version_number,
            snapshot=snapshot,
            content_sha256=hashlib.sha256(_canonical(snapshot).encode()).hexdigest(),
            template_version=memo.template_version,
            event_version=event_version,
            budget_version=memo.budget_version,
            policy_version=policy,
            stage=MemoStatus.PENDING_ADVISOR,
            submitted_by=actor,
            submitted_at=now,
            approval_deadline=default_approval_deadline(
                event.first_date, policy.approval_buffer_days
            ),
            event_starts_at=event.starts_at,
            submission_target=target,
            is_late=today > target,
        )
        memo.current_version = version
        memo.status = MemoStatus.PENDING_ADVISOR
        memo.revision += 1
        memo.updated_at = now
        memo.save()
        if event.status == Event.Status.DRAFT:
            event.status = Event.Status.AWAITING_APPROVALS
            event.updated_at = now
            event.save(update_fields=["status", "updated_at"])
        audit.record(
            actor,
            "memo.send_to_advisor",
            memo,
            revision=version.number,
            after={
                "version": version.number,
                "sha256": version.content_sha256,
                "late": version.is_late,
                "submission_target": target,
                "policy_version": policy.pk,
            },
        )
        late = (
            f" Submitted after the target date of {target:%d %b %Y}; reviewers may decline."
            if version.is_late
            else ""
        )
        notify(
            _advisors(memo.club),
            event_key=f"memo:{memo.pk}:v{version.number}:submitted",
            event_type="memo.submitted",
            object_type="memos.memo",
            object_id=memo.pk,
            subject=f"{memo.reference} v{version.number} awaits your confirmation",
            message=f"{actor.full_name} sent '{memo.subject}' for {event.title}.{late}",
            link=f"/memos/{memo.pk}/review/",
            email=policy.email_on_submission,
        )
        return CommandResult(
            "memos.memo", memo.pk, "sent", {"version": version.number, "late": version.is_late}
        )

    return execute(
        actor=actor,
        action="memo.send_to_advisor",
        operation_key=operation_key,
        payload={"m": memo_id, "rev": expected_revision},
        handler=handler,
    )


# --------------------------------------------------------------------------- decisions (FR-MEM-04/07/08)


def _record_signature(
    actor, memo: Memo, version: MemoVersion, stage: str, sig: SignatureInput | None
) -> Signature:
    if sig is None:
        raise ValidationFailed(
            field_errors={"signature": ["Add your e-signature before continuing."]}
        )
    if not sig.attest:
        raise ValidationFailed(
            field_errors={"attest": ["Confirm that you are signing this exact version."]}
        )
    if sig.method == "typed":
        name = sig.typed_name.strip()
        if name.casefold() != actor.full_name.strip().casefold():
            raise ValidationFailed(
                field_errors={
                    "typed_name": ["Type your full name exactly as recorded on your profile."]
                }
            )
        png = files.render_typed_signature(name)
    else:
        png = files.decode_signature_png(sig.data_url)
    stored = files.store_bytes(
        png,
        original_name=f"signature-{memo.reference}-v{version.number}-{stage}.png",
        uploaded_by=actor,
        purpose="signature",
        owner_type="memo_signature",
        owner_id=version.pk,
        club=memo.club,
        allowed_types=frozenset({"image/png"}),
        max_bytes=settings.MAX_SIGNATURE_BYTES,
        field="signature",
    )
    designation = actor.designation_display
    when = clock.local_now()
    return Signature.objects.create(
        version=version,
        stage=stage,
        signer=actor,
        designation=designation,
        image=stored,
        image_sha256=stored.sha256,
        method="typed" if sig.method == "typed" else "drawn",
        attestation=(
            f"I, {actor.full_name} ({designation}), sign version {version.number} of memo "
            f"{memo.reference} at the {Stage(stage).label} stage on {when:%d %b %Y %H:%M} (Dhaka)."
        ),
        content_sha256=version.content_sha256,
        signed_at=clock.now(),
    )


def _require_reason(reason: str, confirm_reject: bool) -> str:
    errors = {}
    if not (reason or "").strip():
        errors["reason"] = ["Enter the reason for rejection."]
    if not confirm_reject:
        errors["confirm_reject"] = ["Confirm the rejection explicitly."]
    if errors:
        raise ValidationFailed(field_errors=errors)
    return reason.strip()


def _conclude(memo: Memo, version: MemoVersion, status: str) -> None:
    now = clock.now()
    version.stage = status
    version.concluded_at = now
    version.save(update_fields=["stage", "concluded_at"])
    memo.status = status
    memo.revision += 1
    memo.updated_at = now
    memo.save(update_fields=["status", "revision", "updated_at"])


def _enter_dosa_queue(memo: Memo, version: MemoVersion) -> None:
    now = clock.now()
    version.stage = MemoStatus.PENDING_DOSA
    version.dosa_queue_entered_at = now
    version.save(update_fields=["stage", "dosa_queue_entered_at"])
    memo.status = MemoStatus.PENDING_DOSA
    memo.revision += 1
    memo.updated_at = now
    memo.save(update_fields=["status", "revision", "updated_at"])
    notify(
        _heads(),
        event_key=f"memo:{memo.pk}:v{version.number}:dosa_queue",
        event_type="memo.dosa_queue",
        object_type="memos.memo",
        object_id=memo.pk,
        subject=f"{memo.reference} v{version.number} awaits DoSA approval",
        message=f"'{memo.subject}' for {memo.event.title} has all required endorsements.",
        link=f"/memos/{memo.pk}/review/",
        email=True,
    )


def assign_additional_signers(
    actor, memo: Memo, version: MemoVersion, signer_ids: list[int]
) -> list[SignatureTask]:
    """Create signature tasks named by the Advisor before confirmation (FR-MEM-07).

    Only active designated signers can be named; each signs only the task assigned to them.
    """
    from apps.accounts.models import Profile

    if not signer_ids:
        return []
    signers = list(
        Profile.objects.filter(
            pk__in=signer_ids, is_active=True, access_category=AccessCategory.SIGNER
        )
    )
    if len(signers) != len(set(signer_ids)):
        raise ValidationFailed(
            field_errors={"additional_signers": ["Choose active designated signers only."]}
        )
    now = clock.now()
    tasks = [
        SignatureTask.objects.create(
            version=version,
            signer=s,
            role_label=s.designation_display,
            assigned_by=actor,
            assigned_at=now,
        )
        for s in signers
    ]
    audit.record(
        actor,
        "memo.assign_signers",
        memo,
        after={"version": version.number, "signers": [s.pk for s in signers]},
    )
    notify(
        signers,
        event_key=f"memo:{memo.pk}:v{version.number}:signature_task",
        event_type="memo.signature_task",
        object_type="memos.memo",
        object_id=memo.pk,
        subject=f"Your signature is requested on {memo.reference} v{version.number}",
        message=f"The Faculty Advisor asked you to sign '{memo.subject}' for {memo.event.title}.",
        link=f"/memos/{memo.pk}/review/",
        email=True,
    )
    return tasks


def decide_memo(
    actor,
    memo_id: int,
    *,
    expected_version: int,
    expected_stage: str,
    decision: str,
    signature: SignatureInput | None = None,
    reason: str = "",
    confirm_reject: bool = False,
    additional_signer_ids: list[int] | None = None,
    operation_key: str | None,
) -> CommandResult:
    """Record one reviewer decision on the current frozen version (FR-MEM-04/05/07/08, UC-20/22).

    Stages and actors: the assigned Faculty Advisor confirms (e-signature) or rejects; each named
    additional signer endorses (e-signature) or returns; the DoSA Head approves (e-signature) or
    rejects. Rejection requires a reason and explicit confirmation.
    Transaction: signature, decision, stage change, audit and notifications commit together.
    Notifications: Advisor rejection reaches the EB author and EB participants (in-app + IUB email)
    and not the Head; Head rejection or signer return also reaches the Advisor.
    Stale safety: if the version or stage differs from what the reviewer saw, StaleRevisionError
    carries the committed outcome; concurrent decisions serialize on the memo lock and the
    one-decision-per-stage constraint, so only the first commits.
    """

    def handler():
        memo = _lock_memo(memo_id)
        if not _can_view(actor, memo):
            raise NotFoundError()
        version = MemoVersion.objects.select_for_update().filter(pk=memo.current_version_id).first()
        if version is None or memo.status not in REVIEW_STATUSES:
            raise _stale(memo, "This memo is not awaiting a review decision.")
        stage = STAGE_FOR_STATUS[memo.status]
        if version.number != expected_version or stage != expected_stage:
            raise _stale(memo)
        if stage == Stage.ADVISOR:
            return _advisor_decision(actor, memo, version)
        if stage == Stage.ADDITIONAL:
            return _signer_decision(actor, memo, version)
        return _head_decision(actor, memo, version)

    def _advisor_decision(actor, memo, version):
        if not is_assigned_advisor(actor, memo.club):
            raise PermissionDeniedError(
                "Only the club's assigned Faculty Advisor can decide at this stage."
            )
        if decision == "confirm":
            sig = _record_signature(actor, memo, version, Stage.ADVISOR, signature)
            MemoDecision.objects.create(
                version=version,
                stage=Stage.ADVISOR,
                actor=actor,
                decision=MemoDecision.Decision.CONFIRM,
                signature=sig,
                decided_at=clock.now(),
            )
            tasks = assign_additional_signers(
                actor, memo, version, list(additional_signer_ids or [])
            )
            audit.record(
                actor,
                "memo.advisor_confirm",
                memo,
                revision=version.number,
                after={"version": version.number, "signers": len(tasks)},
            )
            if tasks:
                version.stage = MemoStatus.PENDING_ADDITIONAL
                version.save(update_fields=["stage"])
                memo.status = MemoStatus.PENDING_ADDITIONAL
                memo.revision += 1
                memo.updated_at = clock.now()
                memo.save(update_fields=["status", "revision", "updated_at"])
            else:
                _enter_dosa_queue(memo, version)
            return CommandResult("memos.memo", memo.pk, "confirmed", {"version": version.number})
        if decision == "reject":
            text = _require_reason(reason, confirm_reject)
            MemoDecision.objects.create(
                version=version,
                stage=Stage.ADVISOR,
                actor=actor,
                decision=MemoDecision.Decision.REJECT,
                reason=text,
                decided_at=clock.now(),
            )
            _conclude(memo, version, MemoStatus.REJECTED)
            audit.record(actor, "memo.advisor_reject", memo, revision=version.number, reason=text)
            notify(
                _eb_participants(memo),
                event_key=f"memo:{memo.pk}:v{version.number}:rejected",
                event_type="memo.rejected",
                object_type="memos.memo",
                object_id=memo.pk,
                subject=f"{memo.reference} v{version.number} was rejected by the Faculty Advisor",
                message=f"Reason: {text}",
                link=_link(memo),
                email=True,
            )
            return CommandResult("memos.memo", memo.pk, "rejected", {"version": version.number})
        raise ValidationFailed(field_errors={"decision": ["Choose Confirm or Reject."]})

    def _signer_decision(actor, memo, version):
        task = version.signature_tasks.select_for_update().filter(signer=actor).first()
        if task is None:
            raise PermissionDeniedError("Only an assigned signer can act at this stage.")
        if task.status != SignatureTask.Status.PENDING:
            raise _stale(memo, "You already acted on this version.")
        if decision == "endorse":
            sig = _record_signature(actor, memo, version, Stage.ADDITIONAL, signature)
            MemoDecision.objects.create(
                version=version,
                stage=Stage.ADDITIONAL,
                actor=actor,
                decision=MemoDecision.Decision.ENDORSE,
                signature=sig,
                decided_at=clock.now(),
            )
            task.status = SignatureTask.Status.ENDORSED
            task.save(update_fields=["status"])
            audit.record(actor, "memo.signer_endorse", memo, revision=version.number)
            if not version.signature_tasks.filter(status=SignatureTask.Status.PENDING).exists():
                _enter_dosa_queue(memo, version)
            return CommandResult("memos.memo", memo.pk, "endorsed", {"version": version.number})
        if decision == "return":
            text = _require_reason(reason, confirm_reject)
            MemoDecision.objects.create(
                version=version,
                stage=Stage.ADDITIONAL,
                actor=actor,
                decision=MemoDecision.Decision.RETURN,
                reason=text,
                decided_at=clock.now(),
            )
            task.status = SignatureTask.Status.RETURNED
            task.save(update_fields=["status"])
            _conclude(memo, version, MemoStatus.REJECTED)
            audit.record(actor, "memo.signer_return", memo, revision=version.number, reason=text)
            notify(
                _eb_participants(memo) + _advisors(memo.club),
                event_key=f"memo:{memo.pk}:v{version.number}:returned",
                event_type="memo.returned",
                object_type="memos.memo",
                object_id=memo.pk,
                subject=f"{memo.reference} v{version.number} was returned by {actor.full_name}",
                message=f"Reason: {text}",
                link=_link(memo),
                email=True,
            )
            return CommandResult("memos.memo", memo.pk, "returned", {"version": version.number})
        raise ValidationFailed(field_errors={"decision": ["Choose Endorse or Return."]})

    def _head_decision(actor, memo, version):
        if not can(actor, Action.MEMOS_HEAD_APPROVE):
            raise PermissionDeniedError("Only the DoSA Head can record the final decision.")
        if decision == "approve":
            sig = _record_signature(actor, memo, version, Stage.DOSA, signature)
            MemoDecision.objects.create(
                version=version,
                stage=Stage.DOSA,
                actor=actor,
                decision=MemoDecision.Decision.APPROVE,
                signature=sig,
                decided_at=clock.now(),
            )
            _conclude(memo, version, MemoStatus.APPROVED)
            event = memo.event
            event.memo_approved_version = version.event_version
            event.updated_at = clock.now()
            event.save(update_fields=["memo_approved_version", "updated_at"])
            from apps.events.lifecycle import refresh_event_status

            refresh_event_status(event)
            audit.record(
                actor,
                "memo.head_approve",
                memo,
                revision=version.number,
                after={"version": version.number, "event_version": version.event_version_id},
            )
            notify(
                _eb_participants(memo) + _advisors(memo.club),
                event_key=f"memo:{memo.pk}:v{version.number}:approved",
                event_type="memo.approved",
                object_type="memos.memo",
                object_id=memo.pk,
                subject=f"{memo.reference} v{version.number} was approved",
                message=f"The DoSA Head approved '{memo.subject}'. Submit the venue booking form next.",
                link=_link(memo),
            )
            return CommandResult("memos.memo", memo.pk, "approved", {"version": version.number})
        if decision == "reject":
            text = _require_reason(reason, confirm_reject)
            MemoDecision.objects.create(
                version=version,
                stage=Stage.DOSA,
                actor=actor,
                decision=MemoDecision.Decision.REJECT,
                reason=text,
                decided_at=clock.now(),
            )
            _conclude(memo, version, MemoStatus.REJECTED)
            audit.record(actor, "memo.head_reject", memo, revision=version.number, reason=text)
            notify(
                _eb_participants(memo) + _advisors(memo.club),
                event_key=f"memo:{memo.pk}:v{version.number}:rejected",
                event_type="memo.rejected",
                object_type="memos.memo",
                object_id=memo.pk,
                subject=f"{memo.reference} v{version.number} was rejected by the DoSA Head",
                message=f"Reason: {text}",
                link=_link(memo),
                email=True,
            )
            return CommandResult("memos.memo", memo.pk, "rejected", {"version": version.number})
        raise ValidationFailed(field_errors={"decision": ["Choose Approve or Reject."]})

    payload = {
        "m": memo_id,
        "v": expected_version,
        "s": expected_stage,
        "d": decision,
        "r": reason,
        "c": confirm_reject,
        "signers": sorted(additional_signer_ids or []),
        "sig": hashlib.sha256(_canonical(asdict(signature)).encode()).hexdigest()
        if signature
        else None,
    }
    return execute(
        actor=actor,
        action="memo.decide",
        operation_key=operation_key,
        payload=payload,
        handler=handler,
    )


# --------------------------------------------------------------------------- revision, withdrawal, amendment


def start_memo_revision(actor, memo_id: int, *, operation_key: str | None) -> CommandResult:
    """Reopen a rejected memo as an editable linked revision (FR-MEM-09, UC-23).

    The rejected version, its reason, dates and signatures stay in history; the next send creates
    a new version that needs fresh signatures at every stage.
    """

    def handler():
        memo = _lock_memo(memo_id)
        _require_author(actor, memo)
        if memo.status != MemoStatus.REJECTED:
            raise InvalidTransitionError("Only a rejected memo can be revised.")
        memo.status = MemoStatus.DRAFT
        memo.revision += 1
        memo.updated_at = clock.now()
        memo.save(update_fields=["status", "revision", "updated_at"])
        audit.record(
            actor, "memo.start_revision", memo, after={"next_version": memo.next_version_number}
        )
        return CommandResult("memos.memo", memo.pk, "revision_started")

    return execute(
        actor=actor,
        action="memo.start_revision",
        operation_key=operation_key,
        payload={"m": memo_id},
        handler=handler,
    )


def withdraw_memo(actor, memo_id: int, *, reason: str, operation_key: str | None) -> CommandResult:
    """Withdraw a draft or a memo pending Advisor confirmation, with a reason (FR-MEM-13).

    If a review decision commits first, the memo is no longer eligible and nothing changes.
    """
    from apps.events.models import Event

    def handler():
        memo = _lock_memo(memo_id)
        _require_author(actor, memo)
        if memo.status not in WITHDRAWABLE:
            raise InvalidTransitionError(
                "This memo can no longer be withdrawn. Approved events change through an amendment or cancellation.",
                current_state={"status": memo.get_status_display()},
            )
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter the reason for withdrawal."]})
        was_pending = memo.status == MemoStatus.PENDING_ADVISOR
        if was_pending:
            version = MemoVersion.objects.select_for_update().get(pk=memo.current_version_id)
            version.stage = MemoStatus.WITHDRAWN
            version.concluded_at = clock.now()
            version.save(update_fields=["stage", "concluded_at"])
        memo.status = MemoStatus.WITHDRAWN
        memo.withdrawn_reason = reason.strip()
        memo.revision += 1
        memo.updated_at = clock.now()
        memo.save(update_fields=["status", "withdrawn_reason", "revision", "updated_at"])
        event = Event.objects.select_for_update().get(pk=memo.event_id)
        if (
            memo.kind == Memo.Kind.ORIGINAL
            and event.status == Event.Status.AWAITING_APPROVALS
            and event.memo_approved_version_id is None
        ):
            event.status = Event.Status.DRAFT
            event.save(update_fields=["status"])
        audit.record(actor, "memo.withdraw", memo, reason=reason)
        if was_pending:
            notify(
                _advisors(memo.club),
                event_key=f"memo:{memo.pk}:withdrawn",
                event_type="memo.withdrawn",
                object_type="memos.memo",
                object_id=memo.pk,
                subject=f"{memo.reference} was withdrawn",
                message=f"Reason: {reason.strip()}",
                link=_link(memo),
            )
        return CommandResult("memos.memo", memo.pk, "withdrawn")

    return execute(
        actor=actor,
        action="memo.withdraw",
        operation_key=operation_key,
        payload={"m": memo_id, "r": reason},
        handler=handler,
    )


def start_memo_amendment(actor, memo_id: int, *, operation_key: str | None) -> CommandResult:
    """Start a linked amendment draft for an approved memo (FR-MEM-12, UC-25).

    The approved memo stays read-only and authoritative; the amendment follows all three stages.
    The draft starts from the approved text so approved and proposed details can be compared.
    """

    def handler():
        memo = _lock_memo(memo_id)
        _require_author(actor, memo)
        if memo.status != MemoStatus.APPROVED:
            raise InvalidTransitionError("Only an approved memo can be amended.")
        if memo.club.is_archived:
            raise InvalidTransitionError("This club is archived and cannot start new requests.")
        if memo.amendments.exclude(status__in=[MemoStatus.APPROVED, MemoStatus.WITHDRAWN]).exists():
            raise ConflictError("An amendment for this memo is already in progress.")
        template = memo.template_version.template
        tv = (
            template.current_version
            if template.is_active and template.current_version
            else memo.template_version
        )
        fields = memo.current_version.snapshot["fields"]
        now = clock.now()
        amendment = Memo.objects.create(
            club=memo.club,
            event=memo.event,
            template_version=tv,
            kind=Memo.Kind.AMENDMENT,
            amends=memo,
            author=actor,
            author_term=memo.author_term,
            budget_version=memo.budget_version,
            created_at=now,
            updated_at=now,
            **{
                k: (date.fromisoformat(v) if k == "memo_date" and v else v)
                for k, v in fields.items()
            },
        )
        audit.record(actor, "memo.start_amendment", amendment, after={"amends": memo.pk})
        return CommandResult("memos.memo", amendment.pk, "amendment_started")

    return execute(
        actor=actor,
        action="memo.start_amendment",
        operation_key=operation_key,
        payload={"m": memo_id},
        handler=handler,
    )


def change_approval_deadline(
    actor,
    memo_id: int,
    *,
    new_deadline: date,
    expected_deadline: date | None,
    reason: str,
    operation_key: str | None,
) -> CommandResult:
    """DoSA Head changes the approval deadline of a memo in review (FR-MEM-11).

    Original handoff and queue-entry timestamps are preserved; the audit keeps the previous value.
    A change based on a stale deadline raises StaleRevisionError.
    """

    def handler():
        memo = _lock_memo(memo_id)
        if not can(actor, Action.MEMOS_HEAD_APPROVE):
            raise PermissionDeniedError()
        if memo.status not in REVIEW_STATUSES:
            raise InvalidTransitionError("Only a memo in review has an active approval deadline.")
        version = MemoVersion.objects.select_for_update().get(pk=memo.current_version_id)
        if version.approval_deadline != expected_deadline:
            raise StaleRevisionError(
                "The deadline was changed by someone else. Review the current value.",
                current_state={"approval_deadline": version.approval_deadline},
            )
        if not reason.strip():
            raise ValidationFailed(field_errors={"reason": ["Enter the reason for the change."]})
        before = version.approval_deadline
        version.approval_deadline = new_deadline
        version.save(update_fields=["approval_deadline"])
        audit.record(
            actor,
            "memo.change_deadline",
            memo,
            before={"approval_deadline": before},
            after={"approval_deadline": new_deadline},
            reason=reason,
            revision=version.number,
        )
        return CommandResult("memos.memo", memo.pk, "deadline_changed")

    return execute(
        actor=actor,
        action="memo.change_deadline",
        operation_key=operation_key,
        payload={"m": memo_id, "new": new_deadline, "old": expected_deadline, "r": reason},
        handler=handler,
    )


def _can_view(actor, memo: Memo) -> bool:
    from .selectors import can_view_memo

    return can_view_memo(actor, memo)

"""Memo Management views (UC-18 to UC-26). Views parse input and render; commands decide."""

from __future__ import annotations

import json
import uuid

from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.events.models import Event
from apps.events.selectors import visible_events
from apps.platform_core import audit, clock
from apps.platform_core.access import AccessCategory, Action, can, effective_actions, require
from apps.platform_core.exceptions import DomainError, NotFoundError
from apps.platform_core.forms import apply_domain_error
from apps.platform_core.middleware import wants_json

from . import commands, export, selectors
from .forms import (
    AttachmentForm,
    DeadlineForm,
    DecisionForm,
    MemoDraftForm,
    NewMemoForm,
    ReasonForm,
    TemplateForm,
)
from .models import REVIEW_STATUSES, Memo, MemoStatus, MemoTemplate

STATUS_TONE = {
    MemoStatus.APPROVED: "ok",
    MemoStatus.REJECTED: "bad",
    MemoStatus.WITHDRAWN: "neutral",
    MemoStatus.DRAFT: "neutral",
}


def _flash(request, exc: DomainError):
    details = [m for msgs in exc.field_errors.values() for m in msgs]
    messages.error(request, " ".join([exc.message, *details]) if details else exc.message)
    for key, value in exc.current_state.items():
        messages.info(request, f"Current {key.replace('_', ' ')}: {value}")


def _queue(user):
    from .priority import explain, ordered_queue

    if not can(user, Action.MEMOS_HEAD_APPROVE):
        return None
    versions = ordered_queue(list(selectors.dosa_queue()[:50]))
    return [(version, explain(version)) for version in versions]


def memo_list(request):
    user = request.user
    if (
        Action.MEMOS_VIEW not in effective_actions(user)
        and user.access_category != AccessCategory.SIGNER
    ):
        require(user, Action.MEMOS_VIEW)
    memos = selectors.visible_memos(user)
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    if status == "pending":
        memos = memos.filter(status__in=REVIEW_STATUSES)
    elif status in MemoStatus.values:
        memos = memos.filter(status=status)
    if q:
        memos = memos.filter(subject__icontains=q) | memos.filter(event__title__icontains=q)
    rows = [(m, selectors.next_actor(m), STATUS_TONE.get(m.status, "warn")) for m in memos[:200]]
    is_dosa = user.access_category == AccessCategory.DOSA_HEAD
    return render(
        request,
        "memos/memo_list.html",
        {
            "rows": rows,
            "status": status,
            "q": q,
            "statuses": MemoStatus.choices,
            "can_author": Action.MEMOS_AUTHOR in effective_actions(user),
            "can_manage_templates": can(user, Action.MEMOS_MANAGE_TEMPLATES) or is_dosa,
            "queue": _queue(user),
            "can_reorder": can(user, Action.QUEUE_MANAGE),
            "today": clock.local_today(),
        },
    )


@require_POST
def queue_override(request, memo_id: int):
    from datetime import datetime

    from .priority import set_queue_override

    try:
        set_queue_override(
            request.user,
            memo_id,
            position=int(request.POST["position"]),
            reason=request.POST.get("reason", ""),
            expires_on=datetime.strptime(request.POST["expires_on"], "%Y-%m-%d").date(),
            operation_key=request.POST.get("operation_key"),
        )
        messages.success(request, "Queue order recorded. It does not approve the memo.")
    except (DomainError, KeyError, ValueError) as exc:
        messages.error(
            request, getattr(exc, "message", "Enter a position, a reason, and an expiry date.")
        )
    return redirect("memos:list")


def memo_new(request):
    require(request.user, Action.MEMOS_AUTHOR)
    events = [
        e
        for e in visible_events(request.user, Action.MEMOS_AUTHOR).exclude(
            status=Event.Status.CANCELLED
        )
        if not e.memos.filter(kind=Memo.Kind.ORIGINAL).exclude(status=MemoStatus.WITHDRAWN).exists()
    ]
    templates = MemoTemplate.objects.filter(is_active=True, current_version__isnull=False)
    if request.user.access_category != AccessCategory.DOSA_HEAD:
        templates = templates.filter(dosa_only=False)
    form = NewMemoForm(request.POST or None, events=events, templates=templates)
    if request.method == "POST" and form.is_valid():
        try:
            result = commands.create_memo(
                request.user,
                event_id=int(form.cleaned_data["event"]),
                template_id=int(form.cleaned_data["template"]),
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(request, "Draft started. Type the memo and save at any time.")
            return redirect("memos:edit", pk=result.object_id)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "memos/memo_new.html",
        {"form": form, "has_events": bool(events), "has_templates": templates.exists()},
    )


def memo_edit(request, pk):
    memo = selectors.get_memo(request.user, pk)
    require(request.user, Action.MEMOS_AUTHOR, memo.club)
    if memo.status != MemoStatus.DRAFT:
        messages.info(request, "Only a draft can be edited. Submitted versions are read-only.")
        return redirect("memos:detail", pk=memo.pk)
    budget_versions = (
        list(memo.event.budget.versions.order_by("-number"))
        if hasattr(memo.event, "budget")
        else []
    )
    required = sorted(set(memo.template_version.required_fields) | set(commands.ALWAYS_REQUIRED))
    initial = {name: getattr(memo, name) for name in commands.MEMO_FIELDS}
    initial.update(expected_revision=memo.revision, budget_version=memo.budget_version_id or "")
    form = MemoDraftForm(
        request.POST or None, initial=initial, budget_versions=budget_versions, required=required
    )
    newer = None
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            commands.save_memo_draft(
                request.user,
                memo.pk,
                commands.MemoDraftInput(**{name: data[name] for name in commands.MEMO_FIELDS}),
                budget_version_id=int(data["budget_version"]) if data["budget_version"] else None,
                expected_revision=data["expected_revision"],
                operation_key=data["operation_key"],
            )
            messages.success(request, "Draft saved.")
            return redirect("memos:edit", pk=memo.pk)
        except DomainError as exc:
            apply_domain_error(form, exc)
            if exc.code == "stale_revision":
                memo.refresh_from_db()
                newer = memo
    keys = [(a["key"], a["label"]) for a in memo.template_version.required_attachments] + [
        ("supporting", "Supporting document")
    ]
    return render(
        request,
        "memos/memo_edit.html",
        {
            "memo": memo,
            "form": form,
            "newer": newer,
            "attachment_form": AttachmentForm(keys=keys),
            "attachments": memo.attachments.select_related("file").order_by("key", "-uploaded_at"),
            "problems": commands.submission_problems(memo),
            "template_version": memo.template_version,
        },
    )


@require_POST
def memo_attach(request, pk):
    memo = selectors.get_memo(request.user, pk)
    keys = [(a["key"], a["label"]) for a in memo.template_version.required_attachments] + [
        ("supporting", "Supporting document")
    ]
    form = AttachmentForm(request.POST, request.FILES, keys=keys)
    if form.is_valid():
        try:
            commands.upload_memo_attachment(
                request.user,
                memo.pk,
                key=form.cleaned_data["attachment_key"],
                uploaded_file=form.cleaned_data["file"],
            )
            messages.success(
                request, "Attachment uploaded. Earlier files stay in the record history."
            )
        except DomainError as exc:
            _flash(request, exc)
    else:
        messages.error(request, "Choose an attachment type and a file.")
    return redirect("memos:edit", pk=memo.pk)


@require_POST
def memo_send(request, pk):
    memo = selectors.get_memo(request.user, pk)
    try:
        result = commands.send_memo_to_advisor(
            request.user,
            memo.pk,
            expected_revision=int(request.POST.get("expected_revision", 0)),
            operation_key=request.POST.get("operation_key"),
        )
        note = " It is flagged as late; reviewers may decline." if result.data.get("late") else ""
        messages.success(
            request, f"Version {result.data.get('version')} was sent to the Faculty Advisor.{note}"
        )
        return redirect("memos:detail", pk=memo.pk)
    except DomainError as exc:
        _flash(request, exc)
        return (
            redirect("memos:edit", pk=memo.pk)
            if memo.status == MemoStatus.DRAFT
            else redirect("memos:detail", pk=memo.pk)
        )


def memo_detail(request, pk):
    memo = selectors.get_memo(request.user, pk)
    user = request.user
    versions = memo.versions.prefetch_related(
        "decisions__actor", "signatures__signer", "signature_tasks__signer"
    )
    is_author = can(user, Action.MEMOS_AUTHOR, memo.club)
    current = memo.current_version
    return render(
        request,
        "memos/memo_detail.html",
        {
            "memo": memo,
            "versions": versions,
            "current": current,
            "next_actor": selectors.next_actor(memo),
            "tone": STATUS_TONE.get(memo.status, "warn"),
            "is_author": is_author,
            "can_review": selectors.user_can_review(user, memo),
            "can_withdraw": is_author and memo.status in commands.WITHDRAWABLE,
            "can_revise": is_author and memo.status == MemoStatus.REJECTED,
            "can_amend": is_author and memo.status == MemoStatus.APPROVED,
            "can_change_deadline": can(user, Action.MEMOS_HEAD_APPROVE)
            and memo.status in REVIEW_STATUSES,
            "deadline_form": DeadlineForm(
                initial={
                    "expected_deadline": current.approval_deadline if current else None,
                    "new_deadline": current.approval_deadline if current else None,
                }
            ),
            "withdraw_form": ReasonForm(),
            "amendments": memo.amendments.all(),
            "history": audit.history_for("memos.memo", memo.pk)
            if can(user, Action.AUDIT_VIEW)
            else None,
            "today": clock.local_today(),
        },
    )


def memo_review(request, pk, form=None, status=200):
    """SDS page 12 review screen for the current reviewer (Advisor, signer or Head)."""
    from apps.accounts.models import Profile

    memo = selectors.get_memo(request.user, pk)
    if not selectors.user_can_review(request.user, memo):
        messages.info(request, "This memo is not awaiting your decision.")
        return redirect("memos:detail", pk=memo.pk)
    version = memo.current_version
    stage = commands.STAGE_FOR_STATUS[memo.status]
    approve, reject = {
        "advisor": ("confirm", "reject"),
        "additional": ("endorse", "return"),
        "dosa": ("approve", "reject"),
    }[stage]
    earlier = [
        d for v in memo.versions.exclude(pk=version.pk) for d in v.decisions.all() if d.reason
    ]
    return render(
        request,
        "memos/memo_review.html",
        {
            "memo": memo,
            "version": version,
            "stage": stage,
            "approve": approve,
            "reject": reject,
            "approve_label": {
                "confirm": "Confirm and send",
                "endorse": "Endorse and sign",
                "approve": "Approve and sign",
            }[approve],
            "reject_label": "Return with reason" if reject == "return" else "Reject with reason",
            "signers": Profile.objects.filter(
                access_category=AccessCategory.SIGNER, is_active=True
            ),
            "form": form,
            "earlier": earlier,
            "operation_key": uuid.uuid4().hex,
            "budget": version.budget_version,
            "attachments": version.snapshot.get("attachments", []),
        },
        status=status,
    )


@require_POST
def memo_decisions(request, pk):
    """POST /memos/{id}/decisions: form posts redirect; JSON clients get the result or envelope."""
    if wants_json(request):
        try:
            body = json.loads(request.body or b"{}")
        except ValueError:
            body = None
        if not isinstance(body, dict):
            return JsonResponse(
                {
                    "error": {
                        "code": "validation_failed",
                        "message": "Send a JSON object.",
                        "field_errors": {},
                        "request_id": request.correlation_id,
                    }
                },
                status=422,
            )
        data = body
    else:
        data = request.POST
    form = DecisionForm(data)
    if not form.is_valid():
        if wants_json(request):
            return JsonResponse(
                {
                    "error": {
                        "code": "validation_failed",
                        "message": "Some fields need correction.",
                        "field_errors": {k: [str(e) for e in v] for k, v in form.errors.items()},
                        "request_id": request.correlation_id,
                    }
                },
                status=422,
            )
        messages.error(
            request, "The decision form was incomplete. Review the fields and try again."
        )
        return redirect("memos:review", pk=pk)
    cd = form.cleaned_data
    signature = None
    if cd["decision"] in {"confirm", "endorse", "approve"}:
        signature = commands.SignatureInput(
            method=cd["signature_method"] or "drawn",
            data_url=cd["signature_data"],
            typed_name=cd["typed_name"],
            attest=cd["attest"],
        )
    try:
        selectors.get_memo(request.user, pk)
        result = commands.decide_memo(
            request.user,
            pk,
            expected_version=cd["expected_version"],
            expected_stage=cd["expected_stage"],
            decision=cd["decision"],
            signature=signature,
            reason=cd["reason"],
            confirm_reject=cd["confirm_reject"],
            additional_signer_ids=[p.pk for p in cd["additional_signers"]],
            operation_key=cd["operation_key"],
        )
    except DomainError as exc:
        if wants_json(request):
            return JsonResponse(exc.envelope(request.correlation_id), status=exc.http_status)
        if isinstance(exc, NotFoundError):
            raise
        _flash(request, exc)
        target = "memos:review" if exc.http_status == 422 else "memos:detail"
        return redirect(target, pk=pk)
    if wants_json(request):
        return JsonResponse(
            {
                "memo": pk,
                "outcome": result.outcome,
                "version": result.data.get("version"),
                "replayed": result.replayed,
            }
        )
    messages.success(
        request,
        {
            "confirmed": "Confirmed and sent onward.",
            "endorsed": "Endorsement recorded.",
            "approved": "Memo approved.",
            "rejected": "Rejection recorded and the required people notified.",
            "returned": "Return recorded and the author and Advisor notified.",
        }.get(result.outcome, "Decision recorded."),
    )
    return redirect("memos:detail", pk=pk)


@require_POST
def memo_revise(request, pk):
    memo = selectors.get_memo(request.user, pk)
    try:
        commands.start_memo_revision(
            request.user, memo.pk, operation_key=request.POST.get("operation_key")
        )
        messages.success(
            request, "A new editable revision was started. The rejected version stays in history."
        )
        return redirect("memos:edit", pk=memo.pk)
    except DomainError as exc:
        _flash(request, exc)
        return redirect("memos:detail", pk=memo.pk)


@require_POST
def memo_withdraw(request, pk):
    memo = selectors.get_memo(request.user, pk)
    form = ReasonForm(request.POST)
    if form.is_valid():
        try:
            commands.withdraw_memo(
                request.user,
                memo.pk,
                reason=form.cleaned_data["reason"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(request, "Memo withdrawn. Its history is preserved.")
        except DomainError as exc:
            _flash(request, exc)
    else:
        messages.error(request, "Enter the reason for withdrawal.")
    return redirect("memos:detail", pk=memo.pk)


@require_POST
def memo_amend(request, pk):
    memo = selectors.get_memo(request.user, pk)
    try:
        result = commands.start_memo_amendment(
            request.user, memo.pk, operation_key=request.POST.get("operation_key")
        )
        messages.success(
            request,
            "Amendment draft started. The approved memo stays in effect until it is approved.",
        )
        return redirect("memos:edit", pk=result.object_id)
    except DomainError as exc:
        _flash(request, exc)
        return redirect("memos:detail", pk=memo.pk)


@require_POST
def memo_deadline(request, pk):
    memo = selectors.get_memo(request.user, pk)
    form = DeadlineForm(request.POST)
    if form.is_valid():
        try:
            commands.change_approval_deadline(
                request.user,
                memo.pk,
                new_deadline=form.cleaned_data["new_deadline"],
                expected_deadline=form.cleaned_data["expected_deadline"],
                reason=form.cleaned_data["reason"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(
                request, "Approval deadline changed. The original submission times are unchanged."
            )
        except DomainError as exc:
            _flash(request, exc)
    else:
        messages.error(request, "Enter a new deadline and a reason.")
    return redirect("memos:detail", pk=memo.pk)


def _version_param(request, memo):
    number = request.GET.get("version") or request.POST.get("version")
    if not number:
        return None
    version = memo.versions.filter(number=number).first()
    if version is None:
        raise Http404
    return version


def memo_preview(request, pk):
    memo = selectors.get_memo(request.user, pk)
    version = _version_param(request, memo)
    if version is None and memo.status != MemoStatus.DRAFT:
        version = memo.current_version
    return render(request, "memos/preview_a4.html", export.preview_context(memo, version))


@require_POST
def memo_export(request, pk):
    memo = selectors.get_memo(request.user, pk)
    version = _version_param(request, memo)
    try:
        record = export.export_memo_pdf(request.user, memo, version)
    except DomainError as exc:
        _flash(request, exc)
        return redirect("memos:detail", pk=memo.pk)
    return redirect("platform_core:export", pk=record.pk)


# --------------------------------------------------------------------------- templates (UC-18)


def template_list(request):
    require(request.user, Action.MEMOS_MANAGE_TEMPLATES)
    return render(
        request,
        "memos/template_list.html",
        {"templates": MemoTemplate.objects.select_related("current_version")},
    )


def _template_input(form: TemplateForm) -> commands.TemplateInput:
    cd = form.cleaned_data
    return commands.TemplateInput(
        label=cd["label"],
        instructions=cd["instructions"],
        required_fields=tuple(cd["required_fields"]),
        required_attachments=form.attachments(),
        signature_areas=form.signature_areas(),
        requires_budget=cd["requires_budget"],
        dosa_only=cd.get("dosa_only", False),
    )


def template_new(request):
    require(request.user, Action.MEMOS_MANAGE_TEMPLATES)
    form = TemplateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            result = commands.create_template(
                request.user,
                _template_input(form),
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(
                request, "Template created as inactive. Activate it to offer it to EB authors."
            )
            return redirect("memos:template_detail", pk=result.object_id)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(request, "memos/template_form.html", {"form": form, "title": "New memo template"})


def template_detail(request, pk):
    require(request.user, Action.MEMOS_MANAGE_TEMPLATES)
    template = MemoTemplate.objects.filter(pk=pk).select_related("current_version").first()
    if template is None:
        raise Http404
    cv = template.current_version
    initial = {}
    if cv:
        initial = {
            "label": cv.label,
            "instructions": cv.instructions,
            "required_fields": [f for f in cv.required_fields if f not in commands.ALWAYS_REQUIRED],
            "required_attachments": "\n".join(
                f"{a['key']}|{a['label']}|{'yes' if a.get('required', True) else 'no'}"
                for a in cv.required_attachments
            ),
            "advisor_signature": "advisor" in cv.signature_areas,
            "dosa_signature": "dosa" in cv.signature_areas,
            "requires_budget": cv.requires_budget,
            "dosa_only": template.dosa_only,
        }
    form = TemplateForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            commands.revise_template(
                request.user,
                template.pk,
                _template_input(form),
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(
                request, "A new template version was saved. Existing memos keep their version."
            )
            return redirect("memos:template_detail", pk=template.pk)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "memos/template_detail.html",
        {"template": template, "versions": template.versions.order_by("-number"), "form": form},
    )


@require_POST
def template_active(request, pk, action):
    if action not in {"activate", "deactivate"}:
        raise Http404
    try:
        commands.set_template_active(
            request.user,
            pk,
            active=action == "activate",
            operation_key=request.POST.get("operation_key"),
        )
        messages.success(request, f"Template {action}d.")
    except DomainError as exc:
        _flash(request, exc)
    return redirect("memos:template_detail", pk=pk)

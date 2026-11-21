"""Platform views: health probes, protected downloads, notifications, deliveries, policy."""

from __future__ import annotations

from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from . import clock
from .access import Action, can, require
from .commands import PolicyInput, save_policy_version
from .exceptions import DomainError
from .files import EXPORT_ACCESS, FILE_ACCESS, read_bytes
from .forms import CommandForm, apply_domain_error
from .jobs import retry_job
from .models import Export, Job, Notification, PolicyVersion, StoredFile, WorkerHeartbeat

# --------------------------------------------------------------------------- health


@login_not_required
@require_GET
def health_live(request):
    return JsonResponse({"status": "ok"})


@login_not_required
@require_GET
def health_ready(request):
    """Readiness: database reachable; worker heartbeat age reported (TR section 7, Operations)."""
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001
        checks["database"] = "unavailable"
    beat = (
        WorkerHeartbeat.objects.order_by("-last_seen").first()
        if checks["database"] == "ok"
        else None
    )
    stale = timedelta(seconds=settings.WORKER_HEARTBEAT_STALE_SECONDS)
    checks["worker"] = "ok" if beat and clock.now() - beat.last_seen < stale else "stale"
    status = 200 if checks["database"] == "ok" else 503
    return JsonResponse(
        {"status": "ok" if status == 200 else "degraded", "checks": checks}, status=status
    )


# --------------------------------------------------------------------------- protected files


def _file_response(stored: StoredFile, *, download_name: str | None = None) -> HttpResponse:
    data = read_bytes(stored)
    if data is None:
        return render_unavailable()
    response = HttpResponse(data, content_type=stored.content_type)
    name = (download_name or stored.original_name).replace('"', "")
    response["Content-Disposition"] = f'inline; filename="{name}"'
    response["Cache-Control"] = "private, no-store"
    return response


def render_unavailable() -> HttpResponse:
    return HttpResponse(
        "The original file is unavailable. Authorized record details remain on the record page.",
        status=410,
        content_type="text/plain",
    )


@require_GET
def file_download(request, key):
    """Serve a private file after a fresh permission check (FR-COM-06, TR section 2)."""
    stored = StoredFile.objects.filter(key=key, state=StoredFile.State.ACCEPTED).first()
    checker = FILE_ACCESS.get(stored.owner_type) if stored else None
    if stored is None or checker is None or not checker(request.user, stored):
        raise Http404
    return _file_response(stored)


@require_GET
def export_download(request, pk):
    export = Export.objects.select_related("file").filter(pk=pk).first()
    checker = EXPORT_ACCESS.get(export.kind) if export else None
    if export is None or checker is None or not checker(request.user, export):
        raise Http404
    return _file_response(export.file)


# --------------------------------------------------------------------------- notifications


def notification_list(request):
    notices = request.user.notifications.select_related("email_job")[:100]
    return render(request, "platform_core/notifications.html", {"notices": notices})


@require_POST
def notification_open(request, pk):
    notice = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if notice.read_at is None:
        notice.read_at = clock.now()
        notice.save(update_fields=["read_at"])
    target = (
        notice.link if url_has_allowed_host_and_scheme(notice.link, allowed_hosts=None) else "/"
    )
    return redirect(target or "dashboard")


def deliveries(request):
    """Failed or uncertain deliveries that authorized staff can inspect and retry (FR-COM-02)."""
    require(request.user, Action.NOTIFICATIONS_RETRY)
    jobs = Job.objects.filter(
        state__in=[Job.State.FAILED, Job.State.UNCERTAIN, Job.State.RETRYABLE]
    ).order_by("-updated_at")[:200]
    notices = {
        n.email_job_id: n
        for n in Notification.objects.filter(email_job__in=jobs).select_related("recipient")
    }
    rows = [(job, notices.get(job.pk)) for job in jobs]
    return render(request, "platform_core/deliveries.html", {"rows": rows})


@require_POST
def delivery_retry(request, pk):
    require(request.user, Action.NOTIFICATIONS_RETRY)
    try:
        retry_job(request.user, pk)
        messages.success(request, "The delivery was queued for another attempt.")
    except DomainError as exc:
        messages.error(request, exc.message)
    except Job.DoesNotExist as exc:
        raise Http404 from exc
    return redirect("platform_core:deliveries")


# --------------------------------------------------------------------------- workflow policy

WEEKDAYS = [
    (1, "Monday"),
    (2, "Tuesday"),
    (3, "Wednesday"),
    (4, "Thursday"),
    (5, "Friday"),
    (6, "Saturday"),
    (7, "Sunday"),
]


class PolicyForm(CommandForm):
    effective_from = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    standard_lead_days = forms.IntegerField(
        min_value=1, max_value=365, label="Workshop/classroom lead time (calendar days)"
    )
    big_event_lead_months = forms.IntegerField(
        min_value=1, max_value=12, label="Big event lead time (calendar months)"
    )
    approval_buffer_days = forms.IntegerField(
        min_value=0, max_value=60, label="Default approval deadline (days before event)"
    )
    review_window_days = forms.IntegerField(min_value=1, max_value=60, label="Review window (days)")
    working_days = forms.TypedMultipleChoiceField(
        choices=WEEKDAYS, coerce=int, widget=forms.CheckboxSelectMultiple
    )
    email_on_submission = forms.BooleanField(
        required=False, label="Email the Advisor on submission"
    )
    is_synthetic = forms.BooleanField(
        required=False, label="Values are synthetic (not yet confirmed by DoSA)"
    )
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)


def policy_settings(request):
    require(request.user, Action.SETTINGS_MANAGE)
    versions = PolicyVersion.objects.select_related("issued_by")[:50]
    current = versions[0] if versions else None
    if request.method == "POST":
        form = PolicyForm(request.POST)
        if form.is_valid():
            data = {k: v for k, v in form.cleaned_data.items() if k != "operation_key"}
            data["working_days"] = tuple(data["working_days"])
            try:
                save_policy_version(
                    request.user,
                    PolicyInput(**data),
                    operation_key=form.cleaned_data["operation_key"],
                )
                messages.success(request, "The policy version was saved.")
                return redirect("platform_core:policy")
            except DomainError as exc:
                apply_domain_error(form, exc)
    else:
        initial = {"effective_from": clock.local_today(), "is_synthetic": True}
        if current:
            initial.update(
                {
                    f: getattr(current, f)
                    for f in (
                        "standard_lead_days",
                        "big_event_lead_months",
                        "approval_buffer_days",
                        "review_window_days",
                        "working_days",
                        "email_on_submission",
                    )
                }
            )
        form = PolicyForm(initial=initial)
    today = clock.local_today()
    in_force = next((v for v in versions if v.effective_from <= today), None)
    return render(
        request,
        "platform_core/policy.html",
        {
            "form": form,
            "versions": versions,
            "in_force": in_force,
            "can_audit": can(request.user, Action.AUDIT_VIEW),
        },
    )

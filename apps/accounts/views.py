"""Account views: sign-in, profile, directory, provisioning and profile requests."""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_not_required
from django.db.models import Case, IntegerField, When
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.platform_core import audit
from apps.platform_core.access import (
    CEILING,
    AccessCategory,
    Action,
    can,
    effective_actions,
    require,
)
from apps.platform_core.exceptions import DomainError, NotFoundError
from apps.platform_core.forms import apply_domain_error
from apps.platform_core.models import Notification

from . import commands, oidc
from .dashboard import build_dashboard
from .forms import ActivationForm, DecisionForm, GrantsForm, ProfileChangeForm, ProvisionForm
from .models import Grant, Profile, ProfileChangeRequest

logger = logging.getLogger("townhall.auth")
BACKEND = "apps.accounts.backends.ActiveProfileBackend"
SIGN_IN_FAILED = (
    "Sign-in could not be completed. Use your IUB Google account, "
    "or contact DoSA if the problem continues."
)


# --------------------------------------------------------------------------- sign-in


@login_not_required
@require_GET
def sign_in(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "accounts/sign_in.html", {"demo_auth": _demo_enabled()})


@login_not_required
@require_GET
def google_start(request):
    redirect_uri = request.build_absolute_uri(reverse("accounts:google_callback"))
    try:
        return oidc.authorize_redirect(request, redirect_uri)
    except oidc.ProviderUnavailable:
        return render(
            request,
            "accounts/sign_in.html",
            {
                "error": "IUB Google sign-in is unavailable right now. Try again later.",
                "demo_auth": _demo_enabled(),
            },
            status=503,
        )


@login_not_required
@require_GET
def google_callback(request):
    """Complete sign-in. Any failure creates no session and reveals nothing (FR-IAM-01)."""
    try:
        identity = oidc.verify_callback(request)
        profile = commands.sign_in_with_identity(identity)
    except (oidc.ProviderUnavailable, commands.SignInDenied) as exc:
        logger.info("sign-in denied: %s", type(exc).__name__)
        return render(
            request,
            "accounts/sign_in.html",
            {"error": SIGN_IN_FAILED, "demo_auth": _demo_enabled()},
            status=403,
        )
    login(request, profile, backend=BACKEND)
    return redirect("dashboard")


@require_POST
def sign_out(request):
    audit.record(request.user, "session.sign_out", request.user)
    logout(request)
    messages.info(request, "You have signed out.")
    return redirect("accounts:sign_in")


def _demo_enabled() -> bool:
    return bool(settings.DEMO_AUTH) and not getattr(settings, "IS_PRODUCTION", False)


@login_not_required
def dev_login(request):
    """Development-only persona picker for active profiles."""
    if not _demo_enabled():
        raise Http404
    personas = Profile.objects.filter(is_active=True).order_by(
        Case(
            When(access_category=AccessCategory.SYSTEM_ADMIN, then=0),
            When(access_category=AccessCategory.DOSA_HEAD, then=1),
            When(access_category=AccessCategory.FACULTY_ADVISOR, then=2),
            default=3,
            output_field=IntegerField(),
        ),
        "full_name",
    )
    if request.method == "POST":
        profile = personas.filter(pk=request.POST.get("profile_id")).first()
        if profile is None:
            messages.error(request, "Choose a profile.")
        else:
            login(request, profile, backend=BACKEND)
            audit.record(profile, "session.demo_sign_in", profile)
            return redirect("dashboard")
    return render(request, "accounts/dev_login.html", {"personas": personas})


# --------------------------------------------------------------------------- dashboard and profile


def dashboard(request):
    return render(request, "accounts/dashboard.html", {"sections": build_dashboard(request.user)})


PROFILE_ROWS = [
    ("full_name", "Full name"),
    ("iub_email", "IUB sign-in address"),
    ("access_category", "Role"),
    ("designation", "Designation"),
    ("department", "Department"),
    ("major", "Major"),
    ("personal_email", "Personal email"),
    ("personal_phone", "Personal phone"),
    ("emergency_phone", "Emergency phone"),
    ("permanent_address", "Permanent address"),
    ("temporary_address", "Temporary address"),
]


def _profile_rows(profile):
    rows = []
    for field, label in PROFILE_ROWS:
        display = getattr(profile, f"get_{field}_display", None)
        value = display() if callable(display) else getattr(profile, field)
        rows.append((field, label, value or "Not recorded"))
        if field == "designation" and profile.access_category == AccessCategory.FACULTY_ADVISOR:
            from apps.clubs.models import Assignment

            club_names = list(
                profile.assignments.filter(
                    kind=Assignment.Kind.FACULTY_ADVISOR, ended_at__isnull=True
                )
                .select_related("club")
                .order_by("club__name")
                .values_list("club__name", flat=True)
                .distinct()
            )
            rows.append(
                ("affiliated_club", "Affiliated club", ", ".join(club_names) or "Not recorded")
            )
    return rows


def _direct_edit_fields(user) -> set[str]:
    if user.access_category == AccessCategory.DOSA_HEAD:
        return {f for f, _ in PROFILE_ROWS}
    if user.access_category in {AccessCategory.EB_MEMBER, AccessCategory.FACULTY_ADVISOR}:
        return set(commands.ORDINARY_FIELDS)
    return set()


def profile_view(request):
    me = request.user
    affiliations = me.assignments.select_related("club", "term").order_by("-start_date")
    direct = _direct_edit_fields(me)
    return render(
        request,
        "accounts/profile.html",
        {
            "rows": _profile_rows(me),
            "affiliations": affiliations,
            "is_dosa": me.access_category
            in {AccessCategory.DOSA_HEAD, AccessCategory.SYSTEM_ADMIN},
            "grants": sorted(Action(a).label for a in effective_actions(me)),
            "requests": me.change_requests.select_related("decided_by")[:20],
            "protected_fields": commands.PROTECTED_FIELDS,
            "direct_edit_fields": direct,
        },
    )


def profile_change(request, field):
    labels = {**commands.ORDINARY_FIELDS, **commands.PROTECTED_FIELDS}
    if field not in labels:
        raise Http404
    current = getattr(request.user, field, None)
    direct = field in _direct_edit_fields(request.user)
    if request.method == "POST":
        form = ProfileChangeForm(request.POST, field_name=field)
        if form.is_valid():
            try:
                if direct:
                    commands.update_own_profile(
                        request.user,
                        field=field,
                        proposed_value=form.cleaned_data["proposed_value"],
                        operation_key=form.cleaned_data["operation_key"],
                    )
                    messages.success(request, "Profile updated.")
                else:
                    commands.request_profile_change(
                        request.user,
                        field=field,
                        proposed_value=form.cleaned_data["proposed_value"],
                        operation_key=form.cleaned_data["operation_key"],
                    )
                    messages.success(
                        request,
                        "Your request is pending review. Your saved details stay in effect until it is decided.",
                    )
                return redirect("accounts:profile")
            except DomainError as exc:
                apply_domain_error(form, exc)
    else:
        form = ProfileChangeForm(field_name=field)
    route = "direct update" if direct else ("an account administrator" if field in commands.PROTECTED_FIELDS else "the DoSA Head")
    return render(
        request,
        "accounts/profile_change.html",
        {
            "form": form,
            "label": labels[field],
            "current": current,
            "route": route,
            "direct": direct,
        },
    )


# --------------------------------------------------------------------------- directory and provisioning


def directory(request):
    require(request.user, Action.ACCOUNTS_VIEW)
    profiles = Profile.objects.all()
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")
    if q:
        profiles = profiles.filter(full_name__icontains=q) | profiles.filter(iub_email__icontains=q)
    if category in AccessCategory.values:
        profiles = profiles.filter(access_category=category)
    if status in {"active", "inactive"}:
        profiles = profiles.filter(is_active=(status == "active"))
    return render(
        request,
        "accounts/directory.html",
        {
            "profiles": profiles.order_by("full_name")[:300],
            "q": q,
            "category": category,
            "status": status,
            "categories": AccessCategory.choices,
            "can_provision": can(request.user, Action.ACCOUNTS_PROVISION),
        },
    )


def provision(request):
    require(request.user, Action.ACCOUNTS_PROVISION)
    allow_demo = _demo_enabled()
    if request.method == "POST":
        form = ProvisionForm(request.POST, allow_demo=allow_demo)
        if form.is_valid():
            data = form.cleaned_data
            grants = None if data["use_default_grants"] else set(data["grants"])
            fields = {
                k: data.get(k, "") or ""
                for k in (
                    "iub_email",
                    "full_name",
                    "access_category",
                    "designation",
                    "department",
                    "major",
                    "personal_email",
                    "personal_phone",
                    "emergency_phone",
                    "permanent_address",
                    "temporary_address",
                )
            }
            try:
                result = commands.provision_profile(
                    request.user,
                    commands.ProfileInput(**fields, is_demo=bool(data.get("is_demo"))),
                    grants=grants,
                    operation_key=data["operation_key"],
                    club_id=data.get("club").pk if data.get("club") else None,
                    term_id=data.get("term").pk if data.get("term") else None,
                )
                messages.success(
                    request,
                    "Profile created. Sign-in instructions were queued for the IUB address.",
                )
                return redirect("accounts:profile_detail", pk=result.object_id)
            except DomainError as exc:
                apply_domain_error(form, exc)
    else:
        form = ProvisionForm(allow_demo=allow_demo)
    import json

    visible_ceilings = {c: acts for c, acts in CEILING.items() if c != AccessCategory.SIGNER}
    ceilings = {
        AccessCategory(c).label: sorted(Action(a).label for a in acts)
        for c, acts in visible_ceilings.items()
    }
    ceilings_json = json.dumps({c: sorted(acts) for c, acts in visible_ceilings.items()})
    return render(
        request,
        "accounts/provision.html",
        {"form": form, "ceilings": ceilings, "ceilings_json": ceilings_json},
    )


def profile_detail(request, pk):
    require(request.user, Action.ACCOUNTS_VIEW)
    profile = Profile.objects.filter(pk=pk).first()
    if profile is None:
        raise Http404
    active_grants = set(
        Grant.objects.filter(profile=profile, revoked_at__isnull=True).values_list(
            "action", flat=True
        )
    )
    grants_form = GrantsForm(
        initial={"grants": sorted(active_grants), "expected_revision": profile.revision}
    )
    activation_form = ActivationForm(initial={"expected_revision": profile.revision})
    invitation = (
        Notification.objects.filter(event_key=f"profile:{profile.pk}:invitation")
        .select_related("email_job")
        .first()
    )
    return render(
        request,
        "accounts/profile_detail.html",
        {
            "profile": profile,
            "rows": _profile_rows(profile),
            "grants": sorted(Action(a).label for a in active_grants),
            "grants_form": grants_form,
            "activation_form": activation_form,
            "assignments": profile.assignments.select_related("club", "term").order_by(
                "-start_date"
            ),
            "invitation": invitation,
            "can_manage_grants": can(request.user, Action.ACCOUNTS_MANAGE_GRANTS),
            "can_provision": can(request.user, Action.ACCOUNTS_PROVISION),
            "can_retry": can(request.user, Action.NOTIFICATIONS_RETRY),
            "history": audit.history_for("accounts.profile", profile.pk)
            if can(request.user, Action.AUDIT_VIEW)
            else None,
        },
    )


@require_POST
def profile_grants(request, pk):
    form = GrantsForm(request.POST)
    if form.is_valid():
        try:
            commands.set_grants(
                request.user,
                pk,
                set(form.cleaned_data["grants"]),
                expected_revision=form.cleaned_data["expected_revision"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(request, "Privileges updated. They apply to the person's next action.")
        except DomainError as exc:
            messages.error(
                request, " ".join([exc.message] + [m for v in exc.field_errors.values() for m in v])
            )
    return redirect("accounts:profile_detail", pk=pk)


@require_POST
def profile_activation(request, pk, action):
    if action not in {"deactivate", "reactivate"}:
        raise Http404
    form = ActivationForm(request.POST)
    if form.is_valid():
        try:
            commands.set_profile_active(
                request.user,
                pk,
                active=(action == "reactivate"),
                reason=form.cleaned_data["reason"],
                expected_revision=form.cleaned_data["expected_revision"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(request, f"Profile {action}d.")
        except DomainError as exc:
            messages.error(request, exc.message)
    else:
        messages.error(request, "Enter a reason before changing the profile's status.")
    return redirect("accounts:profile_detail", pk=pk)


@require_POST
def resend_invitation(request, pk):
    try:
        commands.resend_invitation(request.user, pk)
        messages.success(
            request, "The original invitation was queued for another delivery attempt."
        )
    except NotFoundError:
        raise Http404 from None
    except DomainError as exc:
        messages.error(request, exc.message)
    return redirect("accounts:profile_detail", pk=pk)


# --------------------------------------------------------------------------- profile requests


def _reviewable_requests(user):
    """Requests on routes the user may decide; raises PermissionDeniedError if there are none."""
    acts = effective_actions(user)
    routes = []
    if Action.PROFILE_REVIEW in acts:
        routes.append(ProfileChangeRequest.Route.ORDINARY)
    if Action.ACCOUNTS_MANAGE_GRANTS in acts:
        routes.append(ProfileChangeRequest.Route.PROTECTED)
    if not routes:
        require(user, Action.PROFILE_REVIEW)
    return ProfileChangeRequest.objects.filter(route__in=routes).select_related(
        "profile", "decided_by"
    )


def profile_requests(request):
    qs = _reviewable_requests(request.user)
    pending = qs.filter(status=ProfileChangeRequest.Status.PENDING)
    decided = qs.exclude(status=ProfileChangeRequest.Status.PENDING)[:50]
    return render(
        request, "accounts/profile_requests.html", {"pending": pending, "decided": decided}
    )


def profile_request_detail(request, pk):
    req = _reviewable_requests(request.user).filter(pk=pk).first()
    if req is None:
        raise Http404
    if request.method == "POST":
        form = DecisionForm(request.POST)
        if form.is_valid():
            try:
                commands.decide_profile_change(
                    request.user,
                    req.pk,
                    approve=form.cleaned_data["decision"] == "approve",
                    reason=form.cleaned_data["reason"],
                    operation_key=form.cleaned_data["operation_key"],
                )
                messages.success(request, "Decision recorded.")
                return redirect("accounts:profile_requests")
            except DomainError as exc:
                apply_domain_error(form, exc)
                req.refresh_from_db()
    else:
        form = DecisionForm()
    sensitive_hidden = (
        req.field in commands.SENSITIVE_FIELDS and req.route == ProfileChangeRequest.Route.ORDINARY
    )
    label = {**commands.ORDINARY_FIELDS, **commands.PROTECTED_FIELDS}.get(req.field, req.field)
    return render(
        request,
        "accounts/profile_request_detail.html",
        {
            "req": req,
            "form": form,
            "label": label,
            "sensitive_hidden": sensitive_hidden,
            "current_value": getattr(req.profile, req.field, "")
            if hasattr(req.profile, req.field)
            else "",
            "protected_manual": req.field
            in {"access_category", "club_assignment", "tenure", "privileges"},
        },
    )

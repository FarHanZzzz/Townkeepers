"""Club views: register, club page with organogram, terms, appointments and archive."""

from __future__ import annotations

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.platform_core import audit, clock
from apps.platform_core.access import Action, can, effective_actions, require
from apps.platform_core.exceptions import DomainError
from apps.platform_core.forms import apply_domain_error

from . import commands, selectors
from .forms import (
    AdvisorForm,
    AppointForm,
    ClubForm,
    ClubIdentityForm,
    CorrectionForm,
    EndAssignmentForm,
    InternalProfileForm,
    ReasonForm,
    TermForm,
)
from .models import ArchiveCorrection, Assignment, Term


def _flash_error(request, exc: DomainError) -> None:
    details = [m for msgs in exc.field_errors.values() for m in msgs]
    messages.error(request, " ".join([exc.message, *details]) if details else exc.message)


def club_list(request):
    if Action.CLUBS_VIEW not in effective_actions(request.user):
        require(request.user, Action.CLUBS_VIEW)
    clubs = selectors.visible_clubs(request.user)
    return render(
        request,
        "clubs/club_list.html",
        {"clubs": clubs, "can_manage": can(request.user, Action.CLUBS_MANAGE)},
    )


def club_register(request):
    require(request.user, Action.CLUBS_MANAGE)
    form = ClubForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            result = commands.register_club(
                request.user,
                name=form.cleaned_data["name"],
                short_code=form.cleaned_data["short_code"],
                institutional_profile=form.cleaned_data["institutional_profile"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(request, "Club registered.")
            return redirect("clubs:detail", pk=result.object_id)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(request, "clubs/form.html", {"form": form, "title": "Register a club"})


def club_detail(request, pk):
    club = selectors.get_club(request.user, pk)
    terms = list(club.terms.all())
    current = selectors.current_term(club)
    selected = current
    term_id = request.GET.get("term")
    if term_id:
        selected = next((t for t in terms if str(t.pk) == term_id), None)
        if selected is None:
            raise Http404
    can_manage = can(request.user, Action.CLUBS_MANAGE, club)
    return render(
        request,
        "clubs/club_detail.html",
        {
            "club": club,
            "terms": terms,
            "current": current,
            "selected": selected,
            "members": selectors.term_members(selected) if selected else [],
            "advisors": selectors.club_advisors(club),
            "can_manage": can_manage,
            "can_edit_profile": can(request.user, Action.CLUBS_EDIT_PROFILE, club)
            and not club.is_archived,
            "can_correct": can(request.user, Action.CLUBS_CORRECT_ARCHIVE, club),
            "archive_form": ReasonForm(initial={"expected_revision": club.revision}),
            "close_form": ReasonForm(),
            "history": audit.history_for("clubs.club", club.pk)
            if can(request.user, Action.AUDIT_VIEW)
            else None,
            "today": clock.local_today(),
            "notices": club.events.filter(
                publications__status="published", publications__destination="internal"
            ).distinct(),
        },
    )


def club_handover(request, pk):
    from apps.clubs.handover import handover_term

    club = selectors.get_club(request.user, pk)
    if request.method == "POST":
        try:
            handover_term(
                request.user,
                int(request.POST["term"]),
                successor_id=int(request.POST["successor"]),
                reason=request.POST.get("reason", ""),
                operation_key=request.POST.get("operation_key"),
            )
            messages.success(request, "Handover recorded. Unfinished work moved to the successor.")
        except DomainError as exc:
            messages.error(request, exc.message)
    return redirect("clubs:detail", pk=club.pk)


def club_edit_identity(request, pk):
    require(request.user, Action.CLUBS_MANAGE)
    club = selectors.get_club(request.user, pk)
    form = ClubIdentityForm(
        request.POST or None,
        initial={
            "name": club.name,
            "institutional_profile": club.institutional_profile,
            "expected_revision": club.revision,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            commands.update_club_identity(
                request.user,
                club.pk,
                name=form.cleaned_data["name"],
                institutional_profile=form.cleaned_data["institutional_profile"],
                expected_revision=form.cleaned_data["expected_revision"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(request, "Official identity updated. The club ID is unchanged.")
            return redirect("clubs:detail", pk=club.pk)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "clubs/form.html",
        {"form": form, "title": f"Official identity: {club.name}", "club": club},
    )


@require_POST
def club_archive(request, pk):
    form = ReasonForm(request.POST)
    if form.is_valid():
        try:
            commands.archive_club(
                request.user,
                pk,
                reason=form.cleaned_data["reason"],
                expected_revision=form.cleaned_data["expected_revision"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(
                request, "Club archived. Its records remain available to authorized users."
            )
        except DomainError as exc:
            _flash_error(request, exc)
    else:
        messages.error(request, "Enter a reason before archiving.")
    return redirect("clubs:detail", pk=pk)


def club_internal_profile(request, pk):
    club = selectors.get_club(request.user, pk)
    require(request.user, Action.CLUBS_EDIT_PROFILE, club)
    form = InternalProfileForm(
        request.POST or None,
        initial={
            "description": club.description,
            "internal_contacts": club.internal_contacts,
            "expected_revision": club.revision,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            commands.update_internal_profile(
                request.user,
                club.pk,
                description=form.cleaned_data["description"],
                internal_contacts=form.cleaned_data["internal_contacts"],
                expected_revision=form.cleaned_data["expected_revision"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(request, "Internal club profile updated.")
            return redirect("clubs:detail", pk=club.pk)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "clubs/form.html",
        {"form": form, "title": f"Internal profile: {club.name}", "club": club},
    )


def term_new(request, pk):
    require(request.user, Action.CLUBS_MANAGE)
    club = selectors.get_club(request.user, pk)
    form = TermForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            commands.create_term(
                request.user,
                club.pk,
                label=data["label"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                transition_approved=data["transition_approved"],
                operation_key=data["operation_key"],
            )
            messages.success(
                request, "Term recorded as upcoming. It grants no access until activated."
            )
            return redirect("clubs:detail", pk=club.pk)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "clubs/form.html",
        {"form": form, "title": f"New EB term: {club.name}", "club": club},
    )


def _term_for(request, term_pk) -> Term:
    term = Term.objects.select_related("club").filter(pk=term_pk).first()
    if term is None:
        raise Http404
    selectors.get_club(request.user, term.club_id)
    return term


@require_POST
def term_activate(request, term_pk):
    term = _term_for(request, term_pk)
    try:
        commands.activate_term(
            request.user, term.pk, operation_key=request.POST.get("operation_key")
        )
        messages.success(request, f"Term {term.label} is now active.")
    except DomainError as exc:
        _flash_error(request, exc)
    return redirect("clubs:detail", pk=term.club_id)


@require_POST
def term_close(request, term_pk):
    term = _term_for(request, term_pk)
    form = ReasonForm(request.POST)
    if form.is_valid():
        try:
            commands.close_term(
                request.user,
                term.pk,
                reason=form.cleaned_data["reason"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(
                request, f"Term {term.label} closed. Its members' access for this term has ended."
            )
        except DomainError as exc:
            _flash_error(request, exc)
    else:
        messages.error(request, "Enter a reason before closing the term.")
    return redirect("clubs:detail", pk=term.club_id)


def appoint(request, term_pk):
    require(request.user, Action.CLUBS_MANAGE)
    term = _term_for(request, term_pk)
    form = AppointForm(
        request.POST or None, initial={"start_date": max(term.start_date, clock.local_today())}
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            commands.appoint_member(
                request.user,
                term.pk,
                profile_id=data["profile"].pk,
                designation=data["designation"],
                responsibilities=data["responsibilities"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                operation_key=data["operation_key"],
            )
            messages.success(request, "Appointment recorded.")
            return redirect(f"/clubs/{term.club_id}/?term={term.pk}")
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "clubs/form.html",
        {"form": form, "title": f"Appoint to {term.club.name} {term.label}", "club": term.club},
    )


def advisor_new(request, pk):
    require(request.user, Action.CLUBS_MANAGE)
    club = selectors.get_club(request.user, pk)
    form = AdvisorForm(request.POST or None, initial={"start_date": clock.local_today()})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            commands.assign_advisor(
                request.user,
                club.pk,
                profile_id=data["profile"].pk,
                start_date=data["start_date"],
                end_date=data["end_date"],
                operation_key=data["operation_key"],
            )
            messages.success(request, "Faculty Advisor assigned.")
            return redirect("clubs:detail", pk=club.pk)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "clubs/form.html",
        {"form": form, "title": f"Assign a Faculty Advisor: {club.name}", "club": club},
    )


def assignment_end(request, assignment_pk):
    require(request.user, Action.CLUBS_MANAGE)
    assignment = (
        Assignment.objects.select_related("club", "profile").filter(pk=assignment_pk).first()
    )
    if assignment is None:
        raise Http404
    form = EndAssignmentForm(request.POST or None, initial={"end_date": clock.local_today()})
    if request.method == "POST" and form.is_valid():
        try:
            commands.end_assignment(
                request.user,
                assignment.pk,
                end_date=form.cleaned_data["end_date"],
                reason=form.cleaned_data["reason"],
                operation_key=form.cleaned_data["operation_key"],
            )
            messages.success(
                request, "Assignment ended. The person's other assignments are unchanged."
            )
            return redirect("clubs:detail", pk=assignment.club_id)
        except DomainError as exc:
            apply_domain_error(form, exc)
    return render(
        request,
        "clubs/form.html",
        {"form": form, "title": f"End assignment: {assignment}", "club": assignment.club},
    )


def archive(request):
    """Browse or search previous EB terms (FR-CLB-05, UC-08)."""
    clubs = selectors.visible_clubs(request.user)
    terms = Term.objects.filter(club__in=clubs, status=Term.Status.CLOSED).select_related("club")
    club_id = request.GET.get("club", "")
    q = request.GET.get("q", "").strip()
    if club_id.isdigit():
        terms = terms.filter(club_id=int(club_id))
    if q:
        terms = terms.filter(label__icontains=q)
    return render(
        request,
        "clubs/archive.html",
        {
            "terms": terms.order_by("club__name", "-start_date"),
            "clubs": clubs,
            "club_id": club_id,
            "q": q,
            "can_correct": can(request.user, Action.CLUBS_CORRECT_ARCHIVE),
        },
    )


def correction(request, object_type, object_pk):
    require(request.user, Action.CLUBS_CORRECT_ARCHIVE)
    if object_type not in commands.CORRECTABLE:
        raise Http404
    model = Term if object_type == "term" else Assignment
    record = model.objects.filter(pk=object_pk).first()
    if record is None:
        raise Http404
    fields = sorted(commands.CORRECTABLE[object_type])
    form = CorrectionForm(
        request.POST or None, fields=fields, initial={"based_on_revision": record.revision}
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            commands.correct_archive_record(
                request.user,
                object_type=object_type,
                object_id=record.pk,
                field=data["field"],
                new_value=data["new_value"],
                reason=data["reason"],
                based_on_revision=data["based_on_revision"],
                operation_key=data["operation_key"],
            )
            messages.success(
                request, "Correction recorded. The previous value is kept in the history."
            )
            return redirect("clubs:archive")
        except DomainError as exc:
            apply_domain_error(form, exc)
    history = ArchiveCorrection.objects.filter(object_type=object_type, object_id=record.pk)
    return render(
        request,
        "clubs/correction.html",
        {"form": form, "record": record, "object_type": object_type, "history": history},
    )

"""Account forms. Validation of rules lives in commands; forms parse and display."""

from django import forms

from apps.platform_core.access import AccessCategory, Action
from apps.platform_core.forms import CommandForm

from .models import Department, Major


class ProvisionForm(CommandForm):
    full_name = forms.CharField(max_length=150)
    iub_email = forms.EmailField(
        label="IUB email", help_text="Sign-in instructions go to this address only."
    )
    access_category = forms.ChoiceField(
        choices=[c for c in AccessCategory.choices if c[0] != AccessCategory.SIGNER]
    )
    designation = forms.CharField(
        max_length=120,
        required=False,
        help_text="Typed appointment, for example Club Treasurer. It grants no access.",
    )
    department = forms.ChoiceField(choices=Department.choices, initial=Department.NA)
    major = forms.ChoiceField(choices=Major.choices, initial=Major.NA)
    personal_email = forms.EmailField(required=False)
    personal_phone = forms.CharField(max_length=20, required=False)
    emergency_phone = forms.CharField(max_length=20, required=False)
    permanent_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    temporary_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    club = forms.ModelChoiceField(queryset=None, required=False, label="Club affiliation")
    term = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="EB term (required for EB members)",
        help_text="Select the active/upcoming term for EB member profiles.",
    )
    use_default_grants = forms.BooleanField(
        required=False,
        initial=True,
        label="Grant every module and action available to this access category",
    )
    grants = forms.MultipleChoiceField(
        choices=Action.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Or choose modules and actions",
        help_text="Used when the option above is cleared. An empty selection gives no module access.",
    )
    is_demo = forms.BooleanField(
        required=False, label="Synthetic demonstration identity (development only)"
    )

    def __init__(self, *args, allow_demo: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.clubs.models import Club, Term

        self.fields["club"].queryset = Club.objects.filter(status=Club.Status.ACTIVE).order_by("name")
        self.fields["term"].queryset = Term.objects.filter(
            status__in=[Term.Status.UPCOMING, Term.Status.ACTIVE]
        ).select_related("club").order_by("club__name", "-start_date")
        if not allow_demo:
            del self.fields["is_demo"]

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("access_category")
        club = cleaned.get("club")
        term = cleaned.get("term")
        if category in {AccessCategory.EB_MEMBER, AccessCategory.FACULTY_ADVISOR}:
            if not club:
                self.add_error("club", "A club affiliation is required for this access category.")
            if category == AccessCategory.EB_MEMBER and not term:
                self.add_error("term", "An EB term is required for EB member profiles.")
            if term and club and term.club_id != club.pk:
                self.add_error("term", "Select a term that belongs to the chosen club.")
        return cleaned


class GrantsForm(CommandForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput)
    grants = forms.MultipleChoiceField(
        choices=Action.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Modules and actions",
    )


class ActivationForm(CommandForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))


class ProfileChangeForm(CommandForm):
    proposed_value = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Proposed value"
    )

    def __init__(self, *args, field_name: str, **kwargs):
        super().__init__(*args, **kwargs)
        choices = {
            "department": Department.choices,
            "major": Major.choices,
            "access_category": AccessCategory.choices,
        }.get(field_name)
        if choices:
            self.fields["proposed_value"] = forms.ChoiceField(
                choices=choices, label="Proposed value"
            )
        elif field_name in {
            "full_name",
            "designation",
            "iub_email",
            "personal_email",
            "personal_phone",
            "emergency_phone",
        }:
            self.fields["proposed_value"] = forms.CharField(
                max_length=254, required=False, label="Proposed value"
            )


class DecisionForm(CommandForm):
    decision = forms.ChoiceField(
        choices=[("approve", "Approve"), ("decline", "Decline")], widget=forms.RadioSelect
    )
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

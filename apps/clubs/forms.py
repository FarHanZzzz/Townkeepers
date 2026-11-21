from django import forms

from apps.accounts.models import Profile
from apps.platform_core.access import AccessCategory
from apps.platform_core.forms import CommandForm

DATE = forms.DateInput(attrs={"type": "date"})


class ClubForm(CommandForm):
    name = forms.CharField(max_length=150, label="Official name")
    short_code = forms.CharField(
        max_length=20, help_text="Letters, digits or dashes, for example IUBPC."
    )
    institutional_profile = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}), required=False
    )


class ClubIdentityForm(CommandForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput)
    name = forms.CharField(max_length=150, label="Official name")
    institutional_profile = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}), required=False
    )


class ReasonForm(CommandForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput, required=False)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))


class InternalProfileForm(CommandForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)
    internal_contacts = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text="One contact per line with an email address or phone number.",
    )


class TermForm(CommandForm):
    label = forms.CharField(max_length=60, help_text="For example 2026-27.")
    start_date = forms.DateField(widget=DATE)
    end_date = forms.DateField(widget=DATE)
    transition_approved = forms.BooleanField(
        required=False, label="An overlap with the adjacent term is an approved transition period"
    )


class AppointForm(CommandForm):
    profile = forms.ModelChoiceField(queryset=Profile.objects.none(), label="Member")
    designation = forms.CharField(
        max_length=120,
        label="Position title",
        help_text="For example President, Secretary or Treasurer. The title grants no access.",
    )
    responsibilities = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    start_date = forms.DateField(widget=DATE)
    end_date = forms.DateField(widget=DATE, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profile"].queryset = Profile.objects.filter(
            access_category=AccessCategory.EB_MEMBER, is_active=True
        )


class AdvisorForm(CommandForm):
    profile = forms.ModelChoiceField(queryset=Profile.objects.none(), label="Faculty Advisor")
    start_date = forms.DateField(widget=DATE)
    end_date = forms.DateField(widget=DATE, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profile"].queryset = Profile.objects.filter(
            access_category=AccessCategory.FACULTY_ADVISOR, is_active=True
        )


class EndAssignmentForm(CommandForm):
    end_date = forms.DateField(widget=DATE)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))


class CorrectionForm(CommandForm):
    based_on_revision = forms.IntegerField(widget=forms.HiddenInput)
    field = forms.ChoiceField(choices=[])
    new_value = forms.CharField(max_length=500, label="Corrected value")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, fields=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["field"].choices = [(f, f.replace("_", " ").title()) for f in fields]

from django import forms

from apps.accounts.models import Profile
from apps.platform_core.access import AccessCategory
from apps.platform_core.forms import CommandForm

from .commands import MEMO_FIELDS


class NewMemoForm(CommandForm):
    event = forms.ChoiceField(label="Event")
    template = forms.ChoiceField(label="Memo template")

    def __init__(self, *args, events=(), templates=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event"].choices = [
            (e.pk, f"{e.title} ({e.first_date:%d %b %Y})") for e in events
        ]
        self.fields["template"].choices = [(t.pk, t.label) for t in templates]


class MemoDraftForm(CommandForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput)
    school = forms.CharField(max_length=150, required=False, help_text="If applicable.")
    department = forms.CharField(max_length=150, required=False, help_text="If applicable.")
    to_line = forms.CharField(
        max_length=300,
        required=False,
        label="To",
        help_text="Recipient and designation, for example: Head, Division of Student Activities.",
    )
    through_line = forms.CharField(
        max_length=300,
        required=False,
        label="Through",
        help_text=(
            "Advisor name and designation plus any instructed routing. "
            "A typed name here does not complete a signing task."
        ),
    )
    from_line = forms.CharField(
        max_length=300, required=False, label="From", help_text="Your name, designation and club."
    )
    memo_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    subject = forms.CharField(max_length=300, required=False)
    body = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10}),
        required=False,
        help_text="Include the event title, dates, start and end times, purpose and proposed venue.",
    )
    contact = forms.CharField(max_length=300, required=False, help_text="If supplied.")
    budget_version = forms.ChoiceField(required=False, label="Budget version")

    def __init__(self, *args, budget_versions=(), required=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["budget_version"].choices = [("", "No budget linked")] + [
            (v.pk, f"Version {v.number}") for v in budget_versions
        ]
        for name in required:
            if name in self.fields:
                self.fields[
                    name
                ].label = f"{self.fields[name].label or MEMO_FIELDS[name]} (required to send)"


class AttachmentForm(forms.Form):
    attachment_key = forms.ChoiceField(label="Attachment type")
    file = forms.FileField(help_text="PDF, PNG or JPEG.")

    def __init__(self, *args, keys=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attachment_key"].choices = list(keys)


class ReasonForm(CommandForm):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))


class DeadlineForm(CommandForm):
    expected_deadline = forms.DateField(widget=forms.HiddenInput, required=False)
    new_deadline = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label="New approval deadline"
    )
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))


class DecisionForm(forms.Form):
    """Fields of POST /memos/{id}/decisions (TECHNICAL_REQUIREMENTS.md section 2)."""

    operation_key = forms.CharField(max_length=64)
    expected_version = forms.IntegerField()
    expected_stage = forms.CharField(max_length=12)
    decision = forms.ChoiceField(
        choices=[(d, d) for d in ("confirm", "endorse", "approve", "reject", "return")]
    )
    signature_method = forms.ChoiceField(
        choices=[("drawn", "Draw"), ("typed", "Type my name")], required=False
    )
    signature_data = forms.CharField(required=False)
    typed_name = forms.CharField(max_length=150, required=False, label="Type your full name")
    attest = forms.BooleanField(required=False)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    confirm_reject = forms.BooleanField(required=False)
    additional_signers = forms.ModelMultipleChoiceField(
        queryset=Profile.objects.none(), required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["additional_signers"].queryset = Profile.objects.filter(
            access_category=AccessCategory.SIGNER, is_active=True
        )


class TemplateForm(CommandForm):
    label = forms.CharField(max_length=120, label="DoSA template label")
    instructions = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    required_fields = forms.MultipleChoiceField(
        choices=[(k, v) for k, v in MEMO_FIELDS.items()],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="To, Through, From, memo date, subject and body are always required.",
    )
    required_attachments = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text="One per line as key|label|required (yes/no), for example: agenda|Event agenda|yes",
    )
    advisor_signature = forms.BooleanField(
        required=False, initial=True, label="Faculty Advisor signature area"
    )
    dosa_signature = forms.BooleanField(
        required=False, initial=True, label="DoSA Head signature area"
    )
    requires_budget = forms.BooleanField(
        required=False, label="A budget version must be linked before sending"
    )

    def attachments(self) -> tuple[dict, ...]:
        items = []
        for line in (self.cleaned_data.get("required_attachments") or "").splitlines():
            parts = [p.strip() for p in line.split("|")]
            if not any(parts):
                continue
            key = parts[0] if parts else ""
            label = parts[1] if len(parts) > 1 else ""
            required = (parts[2].lower() if len(parts) > 2 else "yes") != "no"
            items.append({"key": key, "label": label, "required": required})
        return tuple(items)

    def signature_areas(self) -> tuple[str, ...]:
        areas = []
        if self.cleaned_data.get("advisor_signature"):
            areas.append("advisor")
        if self.cleaned_data.get("dosa_signature"):
            areas.append("dosa")
        return tuple(areas)

from django import forms

from apps.platform_core.forms import CommandForm

from .models import EventType


class EventForm(CommandForm):
    owner = forms.ChoiceField(label="Owning club")
    title = forms.CharField(max_length=200)
    event_type = forms.ChoiceField(choices=EventType.choices)
    is_big = forms.BooleanField(
        required=False, label="Designate as a Big event (one-month lead time)"
    )
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)
    contact = forms.CharField(max_length=200, required=False)
    first_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), help_text="Campus-local date."
    )
    last_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Same as the first date for a one-day event.",
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}), help_text="Asia/Dhaka time."
    )
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    proposed_venue = forms.CharField(
        max_length=200, required=False, help_text="A proposal only. It does not reserve a room."
    )
    expected_headcount = forms.IntegerField(min_value=1, required=False)
    expected_revision = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, owners=(), editing=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].choices = list(owners)
        if editing:
            del self.fields["owner"]

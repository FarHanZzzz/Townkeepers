from django import forms

from apps.platform_core.forms import CommandForm

from .models import Currency


class BudgetHeaderForm(CommandForm):
    expected_version_number = forms.IntegerField(widget=forms.HiddenInput)
    requested_amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        min_value=0,
        help_text="Optional amount requested for Advisor review. It is not an allocation or release.",
    )
    requested_currency = forms.ChoiceField(choices=Currency.choices, initial=Currency.BDT)
    purpose = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)


class BudgetLineForm(forms.Form):
    description = forms.CharField(max_length=200, required=False)
    quantity = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    unit = forms.CharField(max_length=30, required=False)
    planned_amount = forms.DecimalField(
        max_digits=14, decimal_places=2, required=False, label="Planned amount"
    )
    currency = forms.ChoiceField(choices=Currency.choices, initial=Currency.BDT)


BudgetLineFormSet = forms.formset_factory(BudgetLineForm, extra=3)


class BudgetReviewForm(CommandForm):
    decision = forms.ChoiceField(
        choices=[
            ("endorse", "Endorse for the next finance step"),
            ("return", "Return with feedback"),
        ],
        widget=forms.RadioSelect,
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Feedback"
    )

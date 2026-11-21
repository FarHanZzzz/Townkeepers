"""Form helpers shared by all modules."""

from __future__ import annotations

import uuid

from django import forms

from .exceptions import DomainError


class CommandForm(forms.Form):
    """Base form carrying a stable operation key so a resubmitted POST replays its outcome.

    The key is generated when the form is first rendered and preserved on validation errors.
    """

    operation_key = forms.CharField(widget=forms.HiddenInput, max_length=64)

    def __init__(self, *args, **kwargs):
        initial = kwargs.setdefault("initial", {})
        initial.setdefault("operation_key", uuid.uuid4().hex)
        super().__init__(*args, **kwargs)


def apply_domain_error(form: forms.Form, exc: DomainError) -> None:
    """Attach a domain error to the form fields it names, or to the form as a whole."""
    attached = False
    for field, messages in exc.field_errors.items():
        target = field if field in form.fields else None
        for message in messages:
            form.add_error(target, message)
            attached = True
    if not attached:
        form.add_error(None, exc.message)

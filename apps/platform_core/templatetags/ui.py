"""Template helpers for accessible forms and campus-local dates (NFR-USE-02, NFR-LOC-01)."""

from decimal import Decimal

from django import template
from django.utils.html import format_html

from apps.platform_core import clock

register = template.Library()


@register.filter
def a11y(bound_field):
    """Render a widget with aria-describedby (help and errors) and aria-invalid when invalid."""
    described = []
    if bound_field.help_text:
        described.append(f"{bound_field.auto_id}_help")
    attrs = {}
    if bound_field.errors:
        described.append(f"{bound_field.auto_id}_error")
        attrs["aria-invalid"] = "true"
    if described:
        attrs["aria-describedby"] = " ".join(described)
    return bound_field.as_widget(attrs=attrs)


@register.filter
def widget_kind(bound_field) -> str:
    return bound_field.field.widget.__class__.__name__


@register.filter
def local_dt(value):
    """Format an aware instant in Asia/Dhaka, e.g. '1 Dec 2026, 10:00 (Dhaka)'."""
    if not value:
        return "Not recorded"
    local = clock.to_local(value)
    return f"{local:%d %b %Y, %H:%M} (Dhaka)".lstrip("0")


@register.filter
def money(amount, currency="BDT"):
    if amount is None:
        return "Not recorded"
    return f"{currency} {Decimal(amount):,.2f}"


@register.filter
def audit_detail(value):
    """Render an audit before/after mapping as 'key: value' pairs instead of Python repr."""
    if not isinstance(value, dict) or not value:
        return value if value not in (None, {}) else "—"
    parts = []
    for key, item in value.items():
        parts.append(f"{key}: {item}")
    return "; ".join(parts)


@register.filter
def status_tone(label):
    """Map a status phrase to a badge tone class. Presentation only."""
    text = str(label or "").casefold()
    if any(word in text for word in ("fail", "reject", "overdue", "uncertain")):
        return "badge-bad"
    if any(word in text for word in ("approv", "current term", "active", "succeeded")):
        return "badge-ok"
    if any(word in text for word in ("pending", "await", "unread", "draft", "queued")):
        return "badge-warn"
    return "badge-neutral"


@register.simple_tag
def status_badge(label, tone="neutral"):
    """Status as text. Tone is a second cue; the words stay readable without colour (NFR-USE-01)."""
    return format_html('<span class="badge badge-{}">{}</span>', tone, label)

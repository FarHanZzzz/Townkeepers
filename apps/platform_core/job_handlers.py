"""Worker job handlers owned by the platform."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage

from .jobs import PermanentJobError, job_handler
from .models import Job, Notification
from .notifications import EMAIL_JOB


@job_handler(EMAIL_JOB)
def send_notification_email(job: Job) -> str:
    """Send the IUB email for one notification. Returns a provider reference."""
    try:
        notice = Notification.objects.get(pk=job.payload["notification_id"])
    except (Notification.DoesNotExist, KeyError) as exc:
        raise PermanentJobError("Notification no longer exists") from exc
    if not notice.email_address:
        raise PermanentJobError("Notification has no intended IUB address")
    body = notice.message
    if notice.link:
        body = f"{body}\n\nOpen in Amader TOWNHALL: {settings.SITE_BASE_URL}{notice.link}"
    message = EmailMessage(
        subject=f"[Amader TOWNHALL] {notice.subject}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[notice.email_address],
        headers={"X-Townhall-Notification": str(notice.pk)},
    )
    sent = message.send(fail_silently=False)
    if sent != 1:
        raise RuntimeError("Email backend did not accept the message")
    return f"notification:{notice.pk}:attempt:{job.attempts}"

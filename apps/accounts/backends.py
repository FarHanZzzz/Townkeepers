"""Session user loading. Deactivated profiles, and demo profiles outside DEMO_AUTH, lose access."""

from django.conf import settings
from django.contrib.auth.backends import BaseBackend

from .models import Profile


class ActiveProfileBackend(BaseBackend):
    """Loads the session's profile on every request.

    ``authenticate`` is not used: sessions are created only by the demonstration persona picker.
    Returning None from ``get_user`` ends access for a profile
    that was deactivated after its session started (FR-IAM-03, NFR-SEC-01).
    """

    def authenticate(self, request, **credentials):
        return None

    def get_user(self, user_id):
        try:
            profile = Profile.objects.get(pk=user_id)
        except Profile.DoesNotExist:
            return None
        if not profile.is_active:
            return None
        if profile.is_demo and not settings.DEMO_AUTH:
            return None
        return profile

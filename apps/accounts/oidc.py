"""Google OpenID Connect adapter (FR-IAM-01, TR 4.1).

Authlib keeps the one-time state and nonce in the session, validates the ID token signature
against Google's published keys, and checks issuer, audience, expiry and nonce. This module
only converts the validated claims into ``VerifiedIdentity``; profile matching is a command.
"""

from __future__ import annotations

from authlib.integrations.django_client import OAuth
from django.conf import settings

from .commands import VerifiedIdentity

_oauth = OAuth()


class ProviderUnavailable(Exception):
    """Sign-in could not be verified (not configured, cancelled, invalid or unreachable)."""


def _client():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ProviderUnavailable("IUB Google sign-in is not configured.")
    client = _oauth.create_client("google")
    if client is None:
        _oauth.register(
            name="google",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            server_metadata_url=settings.GOOGLE_OIDC_METADATA_URL,
            client_kwargs={"scope": "openid email profile", "timeout": 10},
        )
        client = _oauth.create_client("google")
    return client


def authorize_redirect(request, redirect_uri: str):
    """Redirect to Google with a session-bound state and nonce."""
    extra = {"prompt": "select_account"}
    if len(settings.IUB_ALLOWED_DOMAINS) == 1:
        extra["hd"] = settings.IUB_ALLOWED_DOMAINS[0]
    try:
        return _client().authorize_redirect(request, redirect_uri, **extra)
    except ProviderUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001  (metadata fetch failures and similar)
        raise ProviderUnavailable(str(exc)) from exc


def verify_callback(request) -> VerifiedIdentity:
    """Exchange the code and return validated claims, or raise ProviderUnavailable."""
    if request.GET.get("error"):
        raise ProviderUnavailable("Sign-in was cancelled.")
    try:
        token = _client().authorize_access_token(request)
    except ProviderUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001  (state mismatch, bad token, network errors)
        raise ProviderUnavailable(str(exc)) from exc
    claims = token.get("userinfo") or {}
    if not claims.get("sub") or not claims.get("iss"):
        raise ProviderUnavailable("The ID token was missing required claims.")
    return VerifiedIdentity(
        issuer=str(claims["iss"]),
        subject=str(claims["sub"]),
        email=str(claims.get("email", "")),
        email_verified=bool(claims.get("email_verified")),
        hosted_domain=str(claims.get("hd", "")),
    )

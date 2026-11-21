"""Request boundary: correlation IDs, sign-in requirement and domain error mapping."""

from __future__ import annotations

import re
import uuid

from django.contrib.auth.middleware import LoginRequiredMiddleware as DjangoLoginRequired
from django.http import JsonResponse
from django.shortcuts import render

from .exceptions import DomainError, NotFoundError
from .logging import correlation_id

_REQUEST_ID = re.compile(r"[A-Za-z0-9\-]{8,64}")


def wants_json(request) -> bool:
    return request.content_type == "application/json" or "application/json" in request.headers.get(
        "Accept", ""
    )


class CorrelationIdMiddleware:
    """Assign each request a correlation ID used in logs, audit entries and the response header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "")
        rid = supplied if _REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
        token = correlation_id.set(rid)
        request.correlation_id = rid
        try:
            response = self.get_response(request)
        finally:
            correlation_id.reset(token)
        response["X-Request-ID"] = rid
        return response


class LoginRequiredMiddleware(DjangoLoginRequired):
    """Every page requires a session unless marked ``login_not_required`` (NFR-SEC-01).

    Browser traffic is redirected to sign-in; JSON clients receive 401 with the error envelope.
    """

    def handle_no_permission(self, request, view_func):
        if wants_json(request):
            return JsonResponse(
                {
                    "error": {
                        "code": "unauthenticated",
                        "message": "Sign in to continue.",
                        "field_errors": {},
                        "request_id": getattr(request, "correlation_id", ""),
                    }
                },
                status=401,
            )
        return super().handle_no_permission(request, view_func)


class DomainErrorMiddleware:
    """Render uncaught domain errors with their HTTP status instead of a server error."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, DomainError):
            return None
        rid = getattr(request, "correlation_id", "")
        if wants_json(request):
            return JsonResponse(exception.envelope(rid), status=exception.http_status)
        template = (
            "errors/404.html"
            if isinstance(exception, NotFoundError)
            else "errors/domain_error.html"
        )
        return render(request, template, {"error": exception}, status=exception.http_status)

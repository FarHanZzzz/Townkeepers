"""Domain exceptions raised by commands and mapped to HTTP responses at the boundary.

Status mapping follows TECHNICAL_REQUIREMENTS.md section 2: 401 unauthenticated, 403 known
forbidden action, 404 concealed out-of-scope object, 409 current-state conflict, 422 invalid input.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for expected business failures. Never swallowed or reported as success."""

    code = "domain_error"
    http_status = 400
    default_message = "The request could not be completed."

    def __init__(
        self,
        message: str | None = None,
        *,
        field_errors: dict[str, list[str]] | None = None,
        code: str | None = None,
        current_state: dict | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.field_errors = field_errors or {}
        self.current_state = current_state or {}
        if code:
            self.code = code
        super().__init__(self.message)

    def envelope(self, request_id: str = "") -> dict:
        """Return the stable JSON error envelope."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "field_errors": self.field_errors,
                "request_id": request_id,
                **({"current_state": self.current_state} if self.current_state else {}),
            }
        }


class ValidationFailed(DomainError):
    code = "validation_failed"
    http_status = 422
    default_message = "Some fields need correction."


class PermissionDeniedError(DomainError):
    code = "forbidden"
    http_status = 403
    default_message = "You do not have permission to perform this action."


class NotFoundError(DomainError):
    """Concealed out-of-scope or missing record. The message never reveals which."""

    code = "not_found"
    http_status = 404
    default_message = "The requested record is not available."


class ConflictError(DomainError):
    code = "conflict"
    http_status = 409
    default_message = "The record changed. Review the current state before retrying."


class StaleRevisionError(ConflictError):
    code = "stale_revision"
    default_message = "A newer version was saved. Review the current version before retrying."


class InvalidTransitionError(ConflictError):
    code = "invalid_transition"
    default_message = "This action is not available in the record's current state."


class OperationKeyConflict(ConflictError):
    code = "operation_key_reused"
    default_message = "This operation key was already used for a different request."

"""Correlation ID propagation for logs (TECHNICAL_REQUIREMENTS.md section 7, Operations)."""

import contextvars
import logging

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    """Attach the current request's correlation ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get()
        return True

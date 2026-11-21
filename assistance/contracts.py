"""Pydantic contracts for /internal/v1 endpoints. Unknown fields are rejected (TR section 2).

Provider payload types live in ``assistance.providers``; these models are the wire contract and
carry only the fields each task needs (NFR-PRI-02, FR-AIS-05).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STRICT = ConfigDict(extra="forbid", str_strip_whitespace=True)
Identifier = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-:.]+$")


class ErrorBody(BaseModel):
    code: str
    message: str
    field_errors: dict[str, list[str]] = {}
    request_id: str = ""


class ErrorEnvelope(BaseModel):
    error: ErrorBody


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("timestamps must include a time zone offset")
    return value


# --------------------------------------------------------------------------- scheduling (FR-AIS-01..06)


class SchedulingCandidate(BaseModel):
    """A slot Django already screened against hard rules. Only blocked intervals, never details."""

    model_config = STRICT
    candidate_id: str = Identifier
    venue_id: int = Field(gt=0)
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=1, le=100_000)

    _aware_start = field_validator("starts_at", "ends_at")(_aware)

    @model_validator(mode="after")
    def _ordered(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class SchedulingPreferences(BaseModel):
    model_config = STRICT
    preferred_venue_ids: list[int] = Field(default_factory=list, max_length=20)
    preferred_start_hour: int | None = Field(default=None, ge=0, le=23)


class SchedulingRequest(BaseModel):
    model_config = STRICT
    request_id: str = Identifier
    duration_minutes: int = Field(ge=15, le=2880)
    expected_attendance: int = Field(ge=1, le=100_000)
    candidates: list[SchedulingCandidate] = Field(min_length=1, max_length=200)
    preferences: SchedulingPreferences = Field(default_factory=SchedulingPreferences)


class RankedCandidate(BaseModel):
    model_config = STRICT
    candidate_id: str = Identifier
    rank: int = Field(ge=1)
    reason: str = Field(max_length=200)


class SchedulingResponse(BaseModel):
    model_config = STRICT
    request_id: str
    ranked: list[RankedCandidate]
    adapter_version: str
    label: Literal["machine-suggested"] = "machine-suggested"


# --------------------------------------------------------------------------- priority (FR-AIP-01..06)


class PriorityItem(BaseModel):
    model_config = STRICT
    queue_id: str = Identifier
    approval_deadline: date | None = None
    event_start: datetime | None = None
    queue_entered_at: datetime
    review_window_hours: int = Field(ge=1, le=2000)

    _aware_times = field_validator("event_start", "queue_entered_at")(_aware)


class PriorityRequest(BaseModel):
    model_config = STRICT
    request_id: str = Identifier
    input_revision: str = Field(min_length=1, max_length=64)
    now: datetime
    items: list[PriorityItem] = Field(max_length=500)

    _aware_now = field_validator("now")(_aware)


class PriorityRow(BaseModel):
    model_config = STRICT
    queue_id: str = Identifier
    rank: int = Field(ge=1)
    explanation: str = Field(max_length=300)
    flags: list[Literal["overdue", "event_passed", "insufficient_time", "missing_deadline"]] = []


class PriorityResponse(BaseModel):
    model_config = STRICT
    request_id: str
    input_revision: str
    calculated_at: datetime
    ordered: list[PriorityRow]
    missing_deadline_ids: list[str] = []
    adapter_version: str
    label: Literal["machine-suggested"] = "machine-suggested"


# --------------------------------------------------------------------------- OCR (FR-FIN-08)

MAX_OCR_BASE64 = 14 * 1024 * 1024


class OcrRequest(BaseModel):
    model_config = STRICT
    job_id: str = Identifier
    content_type: Literal["application/pdf", "image/png", "image/jpeg"]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_base64: str = Field(min_length=4, max_length=MAX_OCR_BASE64)


class OcrField(BaseModel):
    model_config = STRICT
    value: str | None = Field(default=None, max_length=200)
    confidence: float | None = Field(default=None, ge=0, le=1)


class OcrLineItem(BaseModel):
    model_config = STRICT
    description: str = Field(max_length=200)
    amount: str | None = Field(default=None, max_length=32)


class OcrResponse(BaseModel):
    model_config = STRICT
    job_id: str
    source_sha256: str
    adapter_version: str
    fields: dict[Literal["vendor", "date", "amount", "currency", "reference"], OcrField]
    line_items: list[OcrLineItem] = Field(default_factory=list, max_length=200)
    label: Literal["unverified"] = "unverified"

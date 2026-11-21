"""FastAPI application: ``uv run uvicorn assistance.app:app --port 8001``.

Security: every /internal/v1 route requires ``Authorization: Bearer <ASSISTANCE_SERVICE_TOKEN>``.
Provider output is validated against the response contract and filtered to IDs present in the
request, so a provider can never introduce an ineligible slot or queue item (NFR-AIG-02).
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import os
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .contracts import (
    OcrRequest,
    OcrResponse,
    PriorityRequest,
    PriorityResponse,
    SchedulingRequest,
    SchedulingResponse,
)
from .providers.fake import FakeProvider


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str, field_errors: dict | None = None):
        self.status, self.code, self.message, self.field_errors = (
            status,
            code,
            message,
            field_errors or {},
        )


def _envelope(
    request: Request, status: int, code: str, message: str, field_errors=None
) -> JSONResponse:
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    return JSONResponse(
        status_code=status,
        headers={"X-Request-ID": rid},
        content={
            "error": {
                "code": code,
                "message": message,
                "field_errors": field_errors or {},
                "request_id": rid,
            }
        },
    )


def get_provider():
    return FakeProvider()


def create_app(*, token: str | None = None, provider_timeout: float | None = None) -> FastAPI:
    service_token = token if token is not None else os.environ.get("ASSISTANCE_SERVICE_TOKEN", "")
    timeout = (
        provider_timeout
        if provider_timeout is not None
        else float(os.environ.get("ASSISTANCE_PROVIDER_TIMEOUT", "4"))
    )
    app = FastAPI(
        title="Amader TOWNHALL assistance",
        version="1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.exception_handler(ServiceError)
    async def _service_error(request: Request, exc: ServiceError):
        return _envelope(request, exc.status, exc.code, exc.message, exc.field_errors)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        fields: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"] if p != "body") or "body"
            fields.setdefault(loc, []).append(err["msg"])
        return _envelope(
            request, 422, "validation_failed", "The request does not match the contract.", fields
        )

    def require_token(request: Request) -> None:
        header = request.headers.get("Authorization", "")
        supplied = header[7:] if header.startswith("Bearer ") else ""
        if not service_token or not hmac.compare_digest(supplied.encode(), service_token.encode()):
            raise ServiceError(401, "unauthenticated", "A valid service token is required.")

    async def call_provider(fn, *args):
        try:
            return await asyncio.wait_for(run_in_threadpool(fn, *args), timeout=timeout)
        except TimeoutError as exc:
            raise ServiceError(
                503, "provider_timeout", "The assistance provider did not respond in time."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ServiceError(
                503, "provider_unavailable", "The assistance provider is unavailable."
            ) from exc

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post(
        "/internal/v1/scheduling/suggest",
        response_model=SchedulingResponse,
        dependencies=[Depends(require_token)],
    )
    async def suggest(body: SchedulingRequest, provider=Depends(get_provider)):
        raw = await call_provider(provider.rank_slots, body)
        allowed = {c.candidate_id for c in body.candidates}
        try:
            response = SchedulingResponse(
                request_id=body.request_id,
                ranked=[r for r in raw if isinstance(r, dict) and r.get("candidate_id") in allowed],
                adapter_version=provider.version,
            )
        except ValidationError as exc:
            raise ServiceError(
                502, "provider_malformed", "The provider returned an invalid response."
            ) from exc
        return response

    @app.post(
        "/internal/v1/priority/suggest",
        response_model=PriorityResponse,
        dependencies=[Depends(require_token)],
    )
    async def priority(body: PriorityRequest, provider=Depends(get_provider)):
        raw = await call_provider(provider.prioritize, body)
        allowed = {i.queue_id for i in body.items}
        try:
            rows = [r for r in raw if isinstance(r, dict) and r.get("queue_id") in allowed]
            response = PriorityResponse(
                request_id=body.request_id,
                input_revision=body.input_revision,
                calculated_at=body.now,
                ordered=rows,
                missing_deadline_ids=[
                    i.queue_id for i in body.items if i.approval_deadline is None
                ],
                adapter_version=provider.version,
            )
        except ValidationError as exc:
            raise ServiceError(
                502, "provider_malformed", "The provider returned an invalid response."
            ) from exc
        return response

    @app.post(
        "/internal/v1/ocr/extract",
        response_model=OcrResponse,
        dependencies=[Depends(require_token)],
    )
    async def ocr(body: OcrRequest, provider=Depends(get_provider)):
        try:
            content = base64.b64decode(body.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ServiceError(
                422,
                "validation_failed",
                "content_base64 is not valid base64.",
                {"content_base64": ["Invalid base64."]},
            ) from exc
        if hashlib.sha256(content).hexdigest() != body.source_sha256:
            raise ServiceError(
                422,
                "digest_mismatch",
                "The content does not match source_sha256.",
                {"source_sha256": ["Digest mismatch."]},
            )
        raw = await call_provider(provider.extract, body, content)
        try:
            return OcrResponse(
                job_id=body.job_id,
                source_sha256=body.source_sha256,
                adapter_version=provider.version,
                fields=raw.get("fields", {}),
                line_items=raw.get("line_items", []),
            )
        except (ValidationError, AttributeError) as exc:
            raise ServiceError(
                502, "provider_malformed", "The provider returned an invalid response."
            ) from exc

    return app


app = create_app()

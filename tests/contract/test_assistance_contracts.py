"""FastAPI contract tests over a real HTTP server (TR section 7, AGENTS.md section 4).

Fake providers are injected through dependency overrides, which are cleared after each test.
"""

from __future__ import annotations

import base64
import hashlib
import socket
import threading
import time
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import uvicorn

from assistance.app import create_app, get_provider
from assistance.client import AssistanceClient, AssistanceUnavailable, prioritize_with_fallback
from assistance.contracts import (
    PriorityItem,
    PriorityRequest,
    SchedulingCandidate,
    SchedulingRequest,
)
from assistance.providers.fake import FakeProvider

TOKEN = "synthetic-service-token"
APP = create_app(token=TOKEN, provider_timeout=0.5)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(APP, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    APP.dependency_overrides.clear()


@pytest.fixture
def client(server_url):
    c = AssistanceClient(server_url, TOKEN, timeout=2.0)
    yield c
    c.close()


def scheduling_request() -> SchedulingRequest:
    start = datetime(2026, 12, 18, 12, tzinfo=UTC)
    return SchedulingRequest(
        request_id="req-1",
        duration_minutes=180,
        expected_attendance=40,
        candidates=[
            SchedulingCandidate(
                candidate_id="c1",
                venue_id=1,
                starts_at=start,
                ends_at=start + timedelta(hours=3),
                capacity=60,
            ),
            SchedulingCandidate(
                candidate_id="c2",
                venue_id=2,
                starts_at=start,
                ends_at=start + timedelta(hours=3),
                capacity=45,
            ),
        ],
    )


def priority_request() -> PriorityRequest:
    now = datetime(2026, 12, 1, 4, tzinfo=UTC)
    return PriorityRequest(
        request_id="p1",
        input_revision="r1",
        now=now,
        items=[
            PriorityItem(
                queue_id="m2",
                approval_deadline=date(2026, 12, 16),
                event_start=now + timedelta(days=17),
                queue_entered_at=now,
                review_window_hours=72,
            ),
            PriorityItem(
                queue_id="m1",
                approval_deadline=date(2026, 12, 16),
                event_start=now + timedelta(days=10),
                queue_entered_at=now,
                review_window_hours=72,
            ),
            PriorityItem(
                queue_id="m3",
                approval_deadline=None,
                event_start=None,
                queue_entered_at=now,
                review_window_hours=72,
            ),
            PriorityItem(
                queue_id="m0",
                approval_deadline=date(2026, 11, 30),
                event_start=now - timedelta(hours=1),
                queue_entered_at=now,
                review_window_hours=72,
            ),
        ],
    )


@pytest.mark.req("NFR-SEC-02", "FR-AIS-05")
def test_endpoints_require_the_service_token(server_url):
    body = scheduling_request().model_dump(mode="json")
    assert httpx.post(f"{server_url}/internal/v1/scheduling/suggest", json=body).status_code == 401
    wrong = httpx.post(
        f"{server_url}/internal/v1/scheduling/suggest",
        json=body,
        headers={"Authorization": "Bearer wrong"},
    )
    assert wrong.status_code == 401 and wrong.json()["error"]["code"] == "unauthenticated"
    assert httpx.get(f"{server_url}/health").json() == {"status": "ok"}


@pytest.mark.req("FR-AIS-02", "FR-AIS-03", "NFR-AIG-01")
def test_fake_provider_ranks_only_supplied_candidates_and_labels_output(client):
    result = client.suggest_slots(scheduling_request())
    assert [r.candidate_id for r in result.ranked] == ["c2", "c1"]  # least spare capacity first
    assert result.label == "machine-suggested"


@pytest.mark.req("FR-AIS-02", "NFR-AIG-02", "AC-05")
def test_provider_inventing_a_candidate_is_filtered_out(client):
    class Inventive(FakeProvider):
        def rank_slots(self, request):
            return [
                {"candidate_id": "ghost", "rank": 1, "reason": "x"},
                *super().rank_slots(request),
            ]

    APP.dependency_overrides[get_provider] = Inventive
    assert "ghost" not in {
        r.candidate_id for r in client.suggest_slots(scheduling_request()).ranked
    }


@pytest.mark.req("FR-AIS-06", "AC-05")
def test_malformed_provider_output_becomes_502_and_client_falls_back(client, server_url):
    class Broken(FakeProvider):
        def rank_slots(self, request):
            return [{"candidate_id": "c1", "rank": 0, "reason": "x" * 500}]

    APP.dependency_overrides[get_provider] = Broken
    raw = httpx.post(
        f"{server_url}/internal/v1/scheduling/suggest",
        json=scheduling_request().model_dump(mode="json"),
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert raw.status_code == 502 and raw.json()["error"]["code"] == "provider_malformed"
    with pytest.raises(AssistanceUnavailable):
        client.suggest_slots(scheduling_request())


@pytest.mark.req("FR-AIS-06", "FR-AIP-06")
def test_provider_timeout_returns_503(client):
    class Slow(FakeProvider):
        def rank_slots(self, request):
            time.sleep(1.5)
            return super().rank_slots(request)

    APP.dependency_overrides[get_provider] = Slow
    with pytest.raises(AssistanceUnavailable, match="503 provider_timeout"):
        client.suggest_slots(scheduling_request())


@pytest.mark.req("FR-AIS-06", "FR-AIP-06")
def test_stopped_service_raises_unavailable_and_priority_falls_back_to_deadline_order():
    dead = AssistanceClient(f"http://127.0.0.1:{_free_port()}", TOKEN, timeout=0.5)
    with pytest.raises(AssistanceUnavailable):
        dead.suggest_slots(scheduling_request())
    rows, fallback = prioritize_with_fallback(dead, priority_request())
    assert fallback is True
    assert [r["queue_id"] for r in rows] == ["m0", "m1", "m2", "m3"]
    assert rows[0]["flags"] == ["overdue", "event_passed"] and rows[-1]["flags"] == [
        "missing_deadline"
    ]


@pytest.mark.req("FR-AIP-01", "FR-AIP-02", "FR-AIP-03", "AC-06")
def test_priority_uses_deadline_then_event_start_and_reports_missing_deadlines(client):
    result = client.prioritize(priority_request())
    assert [r.queue_id for r in result.ordered] == ["m0", "m1", "m2", "m3"]
    assert result.missing_deadline_ids == ["m3"] and result.input_revision == "r1"
    assert "days remaining" in result.ordered[1].explanation


@pytest.mark.req("NFR-PRI-02")
def test_unknown_fields_are_rejected_with_a_422_envelope(server_url):
    body = scheduling_request().model_dump(mode="json")
    body["memo_body"] = "private memo text must not be sent"
    response = httpx.post(
        f"{server_url}/internal/v1/scheduling/suggest",
        json=body,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 422
    assert "memo_body" in response.json()["error"]["field_errors"]


@pytest.mark.req("FR-FIN-08", "NFR-AIG-01", "NFR-PRI-02")
def test_ocr_checks_the_source_digest_and_labels_fields_unverified(server_url):
    content = b"\x89PNG\r\n\x1a\nsynthetic receipt"
    good = {
        "job_id": "j1",
        "content_type": "image/png",
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "content_base64": base64.b64encode(content).decode(),
    }
    headers = {"Authorization": f"Bearer {TOKEN}"}
    ok = httpx.post(f"{server_url}/internal/v1/ocr/extract", json=good, headers=headers)
    assert ok.status_code == 200 and ok.json()["label"] == "unverified"
    bad = {**good, "source_sha256": "0" * 64}
    mismatch = httpx.post(f"{server_url}/internal/v1/ocr/extract", json=bad, headers=headers)
    assert mismatch.status_code == 422 and mismatch.json()["error"]["code"] == "digest_mismatch"

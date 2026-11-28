"""Browser journey: EB author, Faculty Advisor and DoSA Head through rejection and resubmission.

Requires ``uv run playwright install chromium``. Runs against Django's live server with the
development-only demo sign-in (synthetic identities only).
"""

from __future__ import annotations

import os

import pytest

from apps.accounts.models import Profile
from apps.memos.models import Memo, MemoStatus
from tests import memo_helpers as h

os.environ.setdefault(
    "DJANGO_ALLOW_ASYNC_UNSAFE", "true"
)  # ORM setup runs beside Playwright's loop

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def sign_in(page, base, name):
    page.goto(f"{base}/dev/login/")
    page.get_by_label(name, exact=False).check()
    page.get_by_role("button", name="Sign in as selected profile").click()
    page.wait_for_url(f"{base}/")


def sign_out(page):
    page.get_by_role("button", name="Sign out").click()


def type_signature(page, full_name, version):
    page.get_by_label("Type my name instead").check()
    page.get_by_label("Full name as recorded on your profile").fill(full_name)
    page.get_by_label(f"I confirm I am signing version {version}").check()


def draw_signature(page, version):
    canvas = page.locator("canvas.signature-pad")
    canvas.scroll_into_view_if_needed()
    box = canvas.bounding_box()
    page.mouse.move(box["x"] + 20, box["y"] + 60)
    page.mouse.down()
    for dx, dy in [(80, 20), (140, 90), (220, 30), (300, 70)]:
        page.mouse.move(box["x"] + dx, box["y"] + dy, steps=6)
    page.mouse.up()
    page.get_by_label(f"I confirm I am signing version {version}").check()


@pytest.mark.req(
    "AC-01",
    "AC-16",
    "FR-MEM-04",
    "FR-MEM-06",
    "FR-MEM-08",
    "FR-MEM-09",
    "UC-19",
    "UC-21",
    "UC-22",
    "UC-23",
)
def test_eb_advisor_head_journey_with_rejection_and_resubmission(
    live_server, page, world, head, initial_policy
):
    Profile.objects.filter(pk__in=[world.president_a.pk, world.advisor_a.pk, head.pk]).update(
        is_demo=True
    )
    memo = h.ready_memo(world, head)
    base = live_server.url
    page.on("dialog", lambda dialog: dialog.accept())

    # EB author reviews the draft and sends it to the Faculty Advisor.
    sign_in(page, base, "Ayesha President")
    page.goto(f"{base}/memos/{memo.pk}/edit/")
    page.get_by_role("button", name="Send to Faculty Advisor").click()
    page.wait_for_url(f"{base}/memos/{memo.pk}/")
    assert page.get_by_text("Pending Advisor Confirmation").first.is_visible()
    sign_out(page)

    # Faculty Advisor confirms with a typed signature (keyboard-accessible path).
    sign_in(page, base, "Dr Advisor A")
    page.goto(f"{base}/memos/{memo.pk}/review/")
    type_signature(page, "Dr Advisor A", 1)
    page.get_by_role("button", name="Confirm and send").click()
    page.wait_for_url(f"{base}/memos/{memo.pk}/")
    sign_out(page)

    # DoSA Head rejects with a reason through the dialog.
    sign_in(page, base, "Synthetic DoSA Head")
    page.goto(f"{base}/memos/{memo.pk}/review/")
    page.get_by_role("button", name="Reject with reason").first.click()
    dialog = page.locator("#reject-dialog")
    dialog.get_by_label("Reason").fill("State the expected headcount in the body.")
    dialog.get_by_label("I confirm rejecting version 1.").check()
    dialog.get_by_role("button", name="Reject with reason").click()
    page.wait_for_url(f"{base}/memos/{memo.pk}/")
    assert page.get_by_text("State the expected headcount in the body.").first.is_visible()
    sign_out(page)

    # EB author starts a revision, edits and resends.
    sign_in(page, base, "Ayesha President")
    page.goto(f"{base}/memos/{memo.pk}/")
    page.get_by_role("button", name="Start a revision").click()
    page.wait_for_url(f"{base}/memos/{memo.pk}/edit/")
    page.get_by_label("Body", exact=False).fill(
        "Revised request: 40 expected participants in a department classroom."
    )
    page.get_by_role("button", name="Save draft").click()
    page.get_by_role("button", name="Send to Faculty Advisor").click()
    page.wait_for_url(f"{base}/memos/{memo.pk}/")
    sign_out(page)

    # Advisor confirms version 2; Head approves with a drawn signature.
    sign_in(page, base, "Dr Advisor A")
    page.goto(f"{base}/memos/{memo.pk}/review/")
    type_signature(page, "Dr Advisor A", 2)
    page.get_by_role("button", name="Confirm and send").click()
    page.wait_for_url(f"{base}/memos/{memo.pk}/")
    sign_out(page)

    sign_in(page, base, "Synthetic DoSA Head")
    page.goto(f"{base}/memos/{memo.pk}/review/")
    draw_signature(page, 2)
    page.get_by_role("button", name="Approve and sign").click()
    page.wait_for_url(f"{base}/memos/{memo.pk}/")
    assert page.get_by_text("Memo approved.").is_visible()

    memo = Memo.objects.get(pk=memo.pk)
    assert memo.status == MemoStatus.APPROVED and memo.current_version.number == 2
    methods = sorted(s.method for s in memo.current_version.signatures.all())
    assert methods == ["drawn", "typed"]

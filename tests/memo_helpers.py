"""Helpers for memo workflow tests. All content is synthetic."""

from __future__ import annotations

import base64
import io
from datetime import date, time

from PIL import Image, ImageDraw

from apps.events.commands import EventInput, create_event
from apps.memos import commands as mc
from apps.memos.models import Memo
from tests.factories import key


def signature_png() -> str:
    img = Image.new("RGBA", (320, 110), (255, 255, 255, 0))
    ImageDraw.Draw(img).line(
        [(10, 80), (90, 20), (170, 90), (300, 30)], fill=(20, 30, 80, 255), width=4
    )
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def signed() -> mc.SignatureInput:
    return mc.SignatureInput(method="drawn", data_url=signature_png(), attest=True)


def make_template(
    head, *, label="Event permission memo", attachments=(), requires_budget=False
) -> int:
    template_id = mc.create_template(
        head,
        mc.TemplateInput(
            label=label, required_attachments=tuple(attachments), requires_budget=requires_budget
        ),
        operation_key=key(),
    ).object_id
    mc.set_template_active(head, template_id, active=True, operation_key=key())
    return template_id


def make_event(world, *, first_date=date(2026, 12, 18), is_big=False, author=None) -> int:
    return create_event(
        author or world.president_a,
        club_id=world.club_a.pk,
        data=EventInput(
            title="Synthetic Programming Workshop",
            event_type="workshop",
            first_date=first_date,
            last_date=first_date,
            start_time=time(18),
            end_time=time(21),
            is_big=is_big,
            proposed_venue="Department classroom",
            expected_headcount=40,
        ),
        operation_key=key(),
    ).object_id


def fill(memo: Memo, author, **overrides) -> None:
    data = dict(
        to_line="Head, Division of Student Activities",
        through_line="Dr Advisor A, Faculty Advisor, Synthetic Programming Club",
        from_line="Ayesha President, President, Synthetic Programming Club",
        memo_date=date(2026, 12, 1),
        subject="Request for permission to hold a programming workshop",
        body="The club requests permission to hold a workshop on 18 December 2026 from 6:00 p.m. to 9:00 p.m. "
        "in a department classroom for 40 participants.",
    )
    data.update(overrides)
    memo.refresh_from_db()
    mc.save_memo_draft(
        author,
        memo.pk,
        mc.MemoDraftInput(**data),
        budget_version_id=memo.budget_version_id,
        expected_revision=memo.revision,
        operation_key=key(),
    )


def ready_memo(
    world, head, *, template_id=None, first_date=date(2026, 12, 18), is_big=False
) -> Memo:
    template_id = template_id or make_template(head)
    event_id = make_event(world, first_date=first_date, is_big=is_big)
    memo_id = mc.create_memo(
        world.president_a, event_id=event_id, template_id=template_id, operation_key=key()
    ).object_id
    memo = Memo.objects.get(pk=memo_id)
    fill(memo, world.president_a)
    memo.refresh_from_db()
    return memo


def send(world, memo: Memo):
    memo.refresh_from_db()
    return mc.send_memo_to_advisor(
        world.president_a, memo.pk, expected_revision=memo.revision, operation_key=key()
    )


def decide(
    actor,
    memo: Memo,
    decision: str,
    *,
    reason="",
    confirm_reject=False,
    signers=None,
    sig=True,
    op=None,
):
    memo.refresh_from_db()
    stage = mc.STAGE_FOR_STATUS[memo.status]
    return mc.decide_memo(
        actor,
        memo.pk,
        expected_version=memo.current_version.number,
        expected_stage=stage,
        decision=decision,
        signature=signed() if sig and decision in {"confirm", "endorse", "approve"} else None,
        reason=reason,
        confirm_reject=confirm_reject,
        additional_signer_ids=signers or [],
        operation_key=op or key(),
    )

"""AC-13 Memo template versioning (PRD Appendix B)."""

import pytest

from apps.memos import commands as mc
from apps.memos.models import Memo, MemoTemplate
from apps.platform_core.exceptions import ValidationFailed
from tests import factories as f
from tests import memo_helpers as h


@pytest.mark.req("AC-13", "FR-MEM-01", "UC-18")
@pytest.mark.django_db
def test_ac13_submitted_memo_keeps_its_template_version_after_revision_and_deactivation(
    world, head, frozen_clock
):
    # The Head creates an active template with required fields, attachments and both signature areas.
    tid = h.make_template(
        head, attachments=[{"key": "agenda", "label": "Agenda", "required": False}]
    )
    template = MemoTemplate.objects.get(pk=tid)
    v1 = template.current_version
    assert set(v1.signature_areas) == {"advisor", "dosa"} and "body" in v1.required_fields

    # An EB author submits using that version.
    memo = h.ready_memo(world, head, template_id=tid)
    h.send(world, memo)

    # Staff revise, then deactivate, the template.
    mc.revise_template(
        head,
        tid,
        mc.TemplateInput(label="Event permission memo", requires_budget=True),
        operation_key=f.key(),
    )
    mc.set_template_active(head, tid, active=False, operation_key=f.key())

    # The submitted memo retains its original template version.
    memo = Memo.objects.get(pk=memo.pk)
    assert memo.template_version_id == v1.pk and memo.current_version.template_version_id == v1.pk
    assert MemoTemplate.objects.get(pk=tid).current_version.number == 2

    # New drafts cannot select the deactivated template.
    event_id = h.make_event(world)
    with pytest.raises(ValidationFailed):
        mc.create_memo(world.president_a, event_id=event_id, template_id=tid, operation_key=f.key())

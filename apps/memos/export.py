"""A4 memo preview context and PDF export (FR-MEM-13, Appendix D)."""

from __future__ import annotations

import base64
import io

from django.template.loader import render_to_string

from apps.platform_core import audit, clock, files
from apps.platform_core.exceptions import DomainError, NotFoundError
from apps.platform_core.models import Export

from .models import Memo, MemoStatus, Signature, Stage
from .selectors import can_view_memo

BLOCK_ORDER = [
    (Stage.ADVISOR, "Faculty Advisor"),
    (Stage.ADDITIONAL, None),
    (Stage.DOSA, "Head, DoSA"),
]


class ExportFailed(DomainError):
    code = "export_failed"
    http_status = 500
    default_message = "The export could not be produced. No file was created."


def _fields_for(memo: Memo, version) -> dict:
    if version is not None:
        return dict(version.snapshot["fields"])
    return {
        name: getattr(memo, name)
        for name in (
            "school",
            "department",
            "to_line",
            "through_line",
            "from_line",
            "memo_date",
            "subject",
            "body",
            "contact",
        )
    }


def _signature_blocks(version, *, embed: bool) -> list[dict]:
    """Recorded signatures only, in Advisor, additional, Head order. Unsigned blocks stay empty."""
    if version is None:
        return []
    blocks = []
    signatures = {
        (s.stage, s.signer_id): s for s in version.signatures.select_related("signer", "image")
    }
    ordered: list[Signature] = []
    for stage, _label in BLOCK_ORDER:
        ordered.extend(s for (st, _), s in signatures.items() if st == stage)
    for sig in ordered:
        data_uri = ""
        if embed:
            raw = files.read_bytes(sig.image)
            data_uri = "data:image/png;base64," + base64.b64encode(raw).decode() if raw else ""
        label = dict(BLOCK_ORDER).get(sig.stage) or sig.designation
        blocks.append({"label": label, "signature": sig, "data_uri": data_uri})
    return blocks


def preview_context(memo: Memo, version=None, *, embed: bool = False) -> dict:
    """Context for the A4 rendering. Drafts are labelled Draft and show no signatures."""
    is_draft = version is None
    if is_draft:
        status_label = "Draft"
    elif version.stage == MemoStatus.APPROVED:
        status_label = "Approved"
    else:
        status_label = MemoStatus(version.stage).label
    fields = _fields_for(memo, version)
    return {
        "memo": memo,
        "version": version,
        "fields": fields,
        "is_draft": is_draft,
        "status_label": status_label,
        "blocks": _signature_blocks(version, embed=embed),
        "template_label": (version.template_version if version else memo.template_version).label,
        "generated_at": clock.now(),
    }


def export_memo_pdf(actor, memo: Memo, version=None) -> Export:
    """Render the exact version (or the current draft) to an A4 PDF in private storage.

    A failed render raises ExportFailed and stores nothing, so no completed export is reported.
    """
    from xhtml2pdf import pisa

    if not can_view_memo(actor, memo):
        raise NotFoundError()
    html = render_to_string("memos/export_a4.html", preview_context(memo, version, embed=True))
    buffer = io.BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err or not buffer.getvalue().startswith(b"%PDF-"):
        raise ExportFailed()
    suffix = f"v{version.number}" if version else "draft"
    stored = files.store_bytes(
        buffer.getvalue(),
        original_name=f"{memo.reference}-{suffix}.pdf",
        uploaded_by=actor,
        purpose="export",
        owner_type="memo_export",
        owner_id=memo.pk,
        club=memo.club,
        allowed_types=frozenset({"application/pdf"}),
    )
    export = Export.objects.create(
        kind="memo",
        object_type="memos.memo",
        object_id=str(memo.pk),
        requested_by=actor,
        file=stored,
        scope={"version": version.number if version else None},
        created_at=clock.now(),
    )
    audit.record(
        actor, "memo.export", memo, after={"export": export.pk, "version": export.scope["version"]}
    )
    return export

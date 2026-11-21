"""File and export access for memo evidence. Every download rechecks memo visibility."""

from apps.platform_core.files import register_export_access, register_file_access

from .models import Memo, MemoVersion
from .selectors import can_view_memo


@register_file_access("memo_attachment")
def memo_attachment_access(user, stored) -> bool:
    memo = Memo.objects.filter(pk=stored.owner_id).first()
    return memo is not None and can_view_memo(user, memo)


@register_file_access("memo_signature")
def memo_signature_access(user, stored) -> bool:
    version = MemoVersion.objects.select_related("memo").filter(pk=stored.owner_id).first()
    return version is not None and can_view_memo(user, version.memo)


@register_export_access("memo")
def memo_export_access(user, export) -> bool:
    memo = Memo.objects.filter(pk=export.object_id).first()
    return memo is not None and can_view_memo(user, memo)

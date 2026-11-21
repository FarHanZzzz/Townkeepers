"""Private upload storage with content sniffing, size limits and digests (FR-COM-06, TR 4.5).

Bytes are written under ``PRIVATE_MEDIA_ROOT`` by a generated key, never by the uploaded name, and
are served only through permission-checked views. Accepted files are immutable; a replacement is a
new ``StoredFile`` so earlier evidence remains in history.
"""

from __future__ import annotations

import base64
import hashlib
import io
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from django.conf import settings

from . import clock
from .exceptions import ValidationFailed
from .models import StoredFile

SIGNATURES = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
}
EVIDENCE_TYPES = frozenset(SIGNATURES)

# owner_type -> callable(profile, stored_file) -> bool. Registered by owning apps.
FILE_ACCESS: dict[str, Callable] = {}
EXPORT_ACCESS: dict[str, Callable] = {}


def register_file_access(owner_type: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        FILE_ACCESS[owner_type] = fn
        return fn

    return decorator


def register_export_access(kind: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        EXPORT_ACCESS[kind] = fn
        return fn

    return decorator


def sniff(data: bytes) -> str | None:
    """Identify the actual content type from leading bytes; ignore the client's claim."""
    for content_type, prefixes in SIGNATURES.items():
        if any(data.startswith(p) for p in prefixes):
            return content_type
    return None


def path_for(stored: StoredFile) -> Path:
    key = str(stored.key)
    return Path(settings.PRIVATE_MEDIA_ROOT) / key[:2] / key


def _write(stored: StoredFile, data: bytes) -> None:
    target = path_for(stored)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def store_bytes(
    data: bytes,
    *,
    original_name: str,
    uploaded_by,
    purpose: str,
    owner_type: str = "",
    owner_id="",
    club=None,
    allowed_types: frozenset[str] = EVIDENCE_TYPES,
    max_bytes: int | None = None,
    field: str = "file",
) -> StoredFile:
    """Validate and store bytes. Raises ValidationFailed without storing anything on rejection."""
    limit = max_bytes or settings.MAX_UPLOAD_BYTES
    if not data:
        raise ValidationFailed(field_errors={field: ["The file is empty."]})
    if len(data) > limit:
        raise ValidationFailed(
            field_errors={field: [f"The file is larger than {limit // 1024} KB."]}
        )
    content_type = sniff(data)
    if content_type not in allowed_types:
        allowed = ", ".join(sorted(t.split("/")[1].upper() for t in allowed_types))
        raise ValidationFailed(field_errors={field: [f"Unsupported file type. Use {allowed}."]})
    stored = StoredFile(
        original_name=Path(original_name).name[:255] or "upload",
        content_type=content_type,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        state=StoredFile.State.STAGED,
        purpose=purpose,
        owner_type=owner_type,
        owner_id=str(owner_id),
        club=club,
        uploaded_by=uploaded_by,
        created_at=clock.now(),
    )
    _write(stored, data)
    stored.state = StoredFile.State.ACCEPTED
    stored.save()
    return stored


def store_upload(uploaded_file, **kwargs) -> StoredFile:
    """Store a Django ``UploadedFile`` after reading at most the size limit plus one byte."""
    limit = kwargs.get("max_bytes") or settings.MAX_UPLOAD_BYTES
    data = uploaded_file.read(limit + 1)
    return store_bytes(data, original_name=uploaded_file.name, **kwargs)


def read_bytes(stored: StoredFile) -> bytes | None:
    """Return the file bytes if present and matching the recorded digest, else None."""
    target = path_for(stored)
    if not target.exists():
        return None
    data = target.read_bytes()
    if hashlib.sha256(data).hexdigest() != stored.sha256:
        return None
    return data


def decode_signature_png(data_url: str, *, field: str = "signature") -> bytes:
    """Decode a drawn signature submitted as a PNG data URL and verify it is a real PNG image."""
    prefix = "data:image/png;base64,"
    if not data_url or not data_url.startswith(prefix):
        raise ValidationFailed(field_errors={field: ["Add your e-signature before continuing."]})
    try:
        raw = base64.b64decode(data_url[len(prefix) :], validate=True)
    except ValueError as exc:
        raise ValidationFailed(field_errors={field: ["The signature could not be read."]}) from exc
    if len(raw) > settings.MAX_SIGNATURE_BYTES or sniff(raw) != "image/png":
        raise ValidationFailed(field_errors={field: ["The signature could not be read."]})
    from PIL import Image

    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
            width, height = img.size
    except Exception as exc:  # noqa: BLE001
        raise ValidationFailed(field_errors={field: ["The signature could not be read."]}) from exc
    if width < 50 or height < 20 or width > 2000 or height > 1000:
        raise ValidationFailed(field_errors={field: ["The signature image size is not supported."]})
    return raw


def render_typed_signature(name: str) -> bytes:
    """Render a typed-name signature PNG, the keyboard-accessible alternative to drawing."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (600, 160), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Oblique.ttf", 44)
    except OSError:
        font = ImageFont.load_default(size=44)
    draw.text((20, 50), name[:40], fill=(20, 30, 80, 255), font=font)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def purge_expired_staged() -> int:
    """Delete staged uploads older than the retention window. Accepted files are never purged."""
    cutoff = clock.now() - timedelta(hours=settings.STAGED_UPLOAD_RETENTION_HOURS)
    stale = StoredFile.objects.filter(state=StoredFile.State.STAGED, created_at__lt=cutoff)
    count = 0
    for stored in stale:
        path_for(stored).unlink(missing_ok=True)
        stored.delete()
        count += 1
    return count

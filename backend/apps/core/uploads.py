"""Safe handling of files teachers upload.

Files get random names (no guessable or hostile paths), only common document and media
types are accepted, and the first bytes must match the extension so an HTML page can't be
uploaded as "notes.pdf". nginx serves them with headers that stop them running scripts.
"""

import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

_ZIP = (b"PK\x03\x04",)
SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),
    ".mp3": (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
    ".mp4": (),  # checked separately: "ftyp" at byte 4
    ".docx": _ZIP,
    ".pptx": _ZIP,
    ".xlsx": _ZIP,
    ".odt": _ZIP,
    ".odp": _ZIP,
    ".ods": _ZIP,
}
ALLOWED_EXTENSIONS = sorted(SIGNATURES)


@deconstructible
class RandomName:
    """upload_to callable: <folder>/<random hex><original extension>."""

    def __init__(self, folder):
        self.folder = folder

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        return f"{self.folder}/{uuid.uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, RandomName) and other.folder == self.folder


def _matches(ext, head):
    if ext == ".mp4":
        return head[4:8] == b"ftyp"
    if ext == ".webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return any(head.startswith(sig) for sig in SIGNATURES[ext])


def validate_upload(file):
    ext = os.path.splitext(file.name or "")[1].lower()
    if ext not in SIGNATURES:
        raise ValidationError(f"Upload a PDF, image, audio/video or office document ({', '.join(ALLOWED_EXTENSIONS)}).")
    limit = settings.UPLOAD_MAX_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f"Files can be at most {settings.UPLOAD_MAX_MB} MB.")
    position = file.tell() if hasattr(file, "tell") else 0
    file.seek(0)
    head = file.read(16)
    file.seek(position)
    if not _matches(ext, head):
        raise ValidationError("The file's contents don't match its type. Re-save it and try again.")
    return file

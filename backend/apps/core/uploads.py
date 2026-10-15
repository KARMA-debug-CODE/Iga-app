"""Safe handling of uploaded files.

Each upload field lists the kinds of file it takes (SafeFileField(kinds=...)). A file is accepted only when
its extension is on that list AND its contents really are that kind of file, checked by parsing, not only
the name or the first bytes:

- images are opened and re-encoded with Pillow, which drops metadata (a phone photo's GPS position,
  comments) and anything hidden around the picture (an HTML page or a ZIP glued to a PNG). Without
  Pillow, images are refused rather than stored unchecked;
- PDFs must start and end like a PDF and hold no scripts, launch actions, embedded files or forms that
  send data (also looked for inside compressed object streams); password-protected PDFs can't be
  checked, so they are refused;
- office documents must be real ZIP packages of that format, without macros or ActiveX controls;
- MP3 and MP4 files must have the frame or box structure of their format from start to end.

HTML, SVG, scripts and every other type are refused. Each kind has a size limit. Files get random names,
and nginx serves them with headers that stop them running scripts (frontend/nginx.conf).
"""

import io
import os
import re
import uuid
import zipfile
import zlib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import FieldFile
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property
from django.utils.translation import gettext as _

try:  # Pillow re-encodes images; without it, images are refused (see _check_image).
    from PIL import Image, ImageOps, ImageSequence
except ImportError:  # pragma: no cover - Pillow is in requirements.txt
    Image = None

EXTENSIONS = {
    "pdf": (".pdf",),
    "image": (".png", ".jpg", ".jpeg", ".gif", ".webp"),
    "office": (".docx", ".pptx", ".xlsx", ".odt", ".odp", ".ods"),
    "audio": (".mp3",),
    "video": (".mp4",),
}
KIND_OF = {ext: kind for kind, exts in EXTENSIONS.items() for ext in exts}
# What teachers may share as a resource, and what a past paper or marking guide may be.
RESOURCE_KINDS = ("pdf", "image", "office", "audio", "video")
PAPER_KINDS = ("pdf",)

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
IMAGE_FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".gif": "GIF", ".webp": "WEBP"}


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


def _mismatch():
    return ValidationError(_("The file's contents don't match its type. Re-save it and try again."))


def _read_all(file):
    file.seek(0)
    data = file.read()
    file.seek(0)
    return data


def _limit_mb(kind):
    if kind == "image":
        return min(settings.UPLOAD_IMAGE_MAX_MB, settings.UPLOAD_MAX_MB)
    return settings.UPLOAD_MAX_MB


# --- Images ---------------------------------------------------------------

# Only what a re-encoded picture needs; everything else in Image.info (EXIF, XMP, ICC, comments) is dropped.
_KEEP_INFO = ("transparency", "duration", "loop", "background")
MAX_FRAMES = 500


def _check_image(file, ext):
    """Decode the whole picture and return it re-encoded, without metadata or extra bytes."""
    if Image is None:
        raise ValidationError(_("Images can't be checked on this server, so they can't be uploaded. Upload a PDF instead."))
    max_pixels = settings.UPLOAD_IMAGE_MAX_PIXELS
    try:
        file.seek(0)
        image = Image.open(file)
        if image.format != IMAGE_FORMATS[ext]:
            raise _mismatch()
        frames = getattr(image, "n_frames", 1)
        if image.width * image.height * min(frames, MAX_FRAMES) > max_pixels or frames > MAX_FRAMES:
            raise ValidationError(
                _("The image is too large: at most %(pixels)s million pixels.") % {"pixels": max_pixels // 1_000_000}
            )
        for frame in ImageSequence.Iterator(image):
            frame.load()  # decodes every frame: a truncated or corrupt file fails here
        image.seek(0)
        out = io.BytesIO()
        fmt = IMAGE_FORMATS[ext]
        if fmt == "JPEG":
            clean = ImageOps.exif_transpose(image)  # keep the photo upright once its EXIF is gone
            if clean.mode not in ("RGB", "L"):
                clean = clean.convert("RGB")
            clean.info = {}
            clean.save(out, "JPEG", quality=90)
        elif fmt == "PNG":
            clean = image if image.mode in ("1", "L", "LA", "P", "RGB", "RGBA") else image.convert("RGBA")
            clean.info = {k: v for k, v in image.info.items() if k in _KEEP_INFO}
            clean.save(out, "PNG")
        else:  # GIF and WebP, possibly animated
            frames_out, durations = [], []
            for frame in ImageSequence.Iterator(image):
                durations.append(frame.info.get("duration", 100))
                converted = frame.convert("RGBA")
                converted.info = {}
                frames_out.append(converted)
            first = frames_out[0]
            options = {"save_all": len(frames_out) > 1, "append_images": frames_out[1:]}
            if len(frames_out) > 1:
                options.update(duration=durations, loop=image.info.get("loop", 0))
            if fmt == "WEBP":
                options.update(quality=90)
            first.save(out, fmt, **options)
    except ValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError(
            _("The image is too large: at most %(pixels)s million pixels.") % {"pixels": max_pixels // 1_000_000}
        )
    except Exception:  # Pillow raises many kinds of errors for broken or hostile files
        raise _mismatch()
    finally:
        file.seek(0)
    return out.getvalue()


# --- PDF ------------------------------------------------------------------

# Names that make a PDF run code, open other programs or files, carry files, or send data somewhere.
PDF_FORBIDDEN = {
    b"JavaScript",
    b"JS",
    b"Launch",
    b"EmbeddedFile",
    b"EmbeddedFiles",
    b"RichMedia",
    b"XFA",
    b"ImportData",
    b"SubmitForm",
    b"GoToE",
}
_PDF_NAME = re.compile(rb"/([A-Za-z0-9#_.+-]+)")
_PDF_HEX = re.compile(rb"#([0-9A-Fa-f]{2})")
_PDF_STREAM = re.compile(rb"stream\r?\n")
# Decompressing every stream of a big PDF has a ceiling, so a crafted file can't use the server's memory.
PDF_INFLATE_BUDGET = 256 * 1024 * 1024


def _pdf_names(data):
    for match in _PDF_NAME.finditer(data):
        name = match.group(1)
        yield _PDF_HEX.sub(lambda m: bytes([int(m.group(1), 16)]), name) if b"#" in name else name


def _inflated(view, start, budget):
    """Yield the decompressed pieces of the Flate stream starting at `start`, at most `budget` bytes in all.
    Input is fed 64 KB at a time, so a stream costs only its own length, however big the file is."""
    inflater, position = zlib.decompressobj(), start
    while not inflater.eof and position < len(view):
        pending = view[position : position + 65536]
        position += len(pending)
        while pending:
            try:
                piece = inflater.decompress(pending, 1 << 20)
            except zlib.error:
                return  # not (or no longer) Flate data: images and fonts use other codecs
            budget -= len(piece)
            if budget < 0:
                raise ValidationError(_("This document is too large when unpacked."))
            yield piece
            pending = inflater.unconsumed_tail


def _check_pdf(file):
    data = _read_all(file)
    if not re.match(rb"%PDF-[12]\.\d", data[:8]) or b"%%EOF" not in data[-2048:]:
        raise _mismatch()
    for name in _pdf_names(data):
        if name == b"Encrypt":
            raise ValidationError(_("Password-protected PDFs can't be checked. Remove the password and try again."))
        if name in PDF_FORBIDDEN:
            raise _forbidden_pdf()
    # Object streams hide dictionaries inside compressed data: look inside every Flate-compressed stream.
    view, remaining = memoryview(data), PDF_INFLATE_BUDGET
    for match in _PDF_STREAM.finditer(data):
        carry = b""
        for piece in _inflated(view, match.end(), remaining):  # raises once the whole file passes the budget
            remaining -= len(piece)
            if any(name in PDF_FORBIDDEN for name in _pdf_names(carry + piece)):
                raise _forbidden_pdf()
            carry = piece[-64:]  # a name cut in two by the piece boundary


def _forbidden_pdf():
    return ValidationError(
        _("This PDF contains scripts, embedded files or actions, which are not allowed. Print it to a new PDF and try again.")
    )


# --- Office documents -----------------------------------------------------

OOXML_MAIN_PART = {".docx": "word/document.xml", ".pptx": "ppt/presentation.xml", ".xlsx": "xl/workbook.xml"}
ODF_MIMETYPE = {
    ".odt": b"application/vnd.oasis.opendocument.text",
    ".odp": b"application/vnd.oasis.opendocument.presentation",
    ".ods": b"application/vnd.oasis.opendocument.spreadsheet",
}
ZIP_MAX_ENTRIES = 5000
ZIP_MAX_UNPACKED = 300 * 1024 * 1024
_MACRO = re.compile(r"(^|/)(vbaProject\.bin|vbaData\.xml|activeX|Basic/|Scripts/)", re.IGNORECASE)


def _check_office(file, ext):
    try:
        file.seek(0)
        with zipfile.ZipFile(file) as package:
            entries = package.infolist()
            if not entries or min(e.header_offset for e in entries) != 0:
                raise _mismatch()  # something other than the package sits in front of it
            if len(entries) > ZIP_MAX_ENTRIES or sum(e.file_size for e in entries) > ZIP_MAX_UNPACKED:
                raise ValidationError(_("This document is too large when unpacked."))
            names = {e.filename for e in entries}
            if any(_MACRO.search(name) for name in names):
                raise _macros()
            if ext in OOXML_MAIN_PART:
                if "[Content_Types].xml" not in names or OOXML_MAIN_PART[ext] not in names:
                    raise _mismatch()
                content_types = package.read("[Content_Types].xml")
                if b"macroEnabled" in content_types or b"vbaProject" in content_types:
                    raise _macros()
            else:
                if "mimetype" not in names or package.read("mimetype").strip() != ODF_MIMETYPE[ext]:
                    raise _mismatch()
                if "content.xml" not in names:
                    raise _mismatch()
    except ValidationError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, KeyError, OSError, EOFError, NotImplementedError):
        raise _mismatch()
    finally:
        file.seek(0)


def _macros():
    return ValidationError(
        _("Documents with macros or ActiveX controls are not allowed. Save it as a normal document and try again.")
    )


# --- Audio and video ------------------------------------------------------

# MPEG audio layer III: bitrates (kbit/s) by version, and sample rates (Hz).
_MP3_BITRATES = {
    1: (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
    2: (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}
_MP3_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}


def _mp3_frame_length(header):
    if len(header) < 4 or header[0] != 0xFF or header[1] & 0xE0 != 0xE0:
        return None
    version = (header[1] >> 3) & 3  # 3 = MPEG-1, 2 = MPEG-2, 0 = MPEG-2.5
    layer = (header[1] >> 1) & 3  # 1 = layer III
    bitrate_index, rate_index, padding = header[2] >> 4, (header[2] >> 2) & 3, (header[2] >> 1) & 1
    if version == 1 or layer != 1 or bitrate_index in (0, 15) or rate_index == 3:
        return None
    bitrate = _MP3_BITRATES[1 if version == 3 else 2][bitrate_index] * 1000
    rate = _MP3_RATES[version][rate_index]
    return (144 if version == 3 else 72) * bitrate // rate + padding


def _check_mp3(file):
    data = _read_all(file)
    position = 0
    if data[:3] == b"ID3":
        major, flags, size = data[3], data[5], data[6:10]
        if major not in (2, 3, 4) or len(size) < 4 or any(b & 0x80 for b in size):
            raise _mismatch()
        position = 10 + ((size[0] << 21) | (size[1] << 14) | (size[2] << 7) | size[3]) + (10 if flags & 0x10 else 0)
    # Three frames in a row must follow (the tag may be padded with zero bytes).
    while position < len(data) and data[position] == 0:
        position += 1
    for _frame in range(3):
        length = _mp3_frame_length(data[position : position + 4])
        if not length:
            raise _mismatch()
        position += length
        if position >= len(data):
            break


MP4_FIRST_BOX = b"ftyp"


def _check_mp4(file):
    """The top-level boxes must chain from the start to the very end, beginning with ftyp and holding moov."""
    file.seek(0, os.SEEK_END)
    total = file.tell()
    position, types = 0, []
    try:
        while position < total:
            file.seek(position)
            header = file.read(16)
            if len(header) < 8:
                raise _mismatch()
            size, box = int.from_bytes(header[:4], "big"), header[4:8]
            if not all(0x20 <= c < 0x7F for c in box):
                raise _mismatch()
            if size == 1:
                if len(header) < 16:
                    raise _mismatch()
                size = int.from_bytes(header[8:16], "big")
            elif size == 0:
                size = total - position
            if size < 8 or position + size > total:
                raise _mismatch()
            types.append(box)
            position += size
    finally:
        file.seek(0)
    if not types or types[0] != MP4_FIRST_BOX or b"moov" not in types:
        raise _mismatch()


# --- The check every upload goes through ----------------------------------


def check(file, kinds=RESOURCE_KINDS):
    """Validate an uploaded file for a field taking `kinds`. Returns cleaned bytes for images, else None."""
    upload = file.file if isinstance(file, FieldFile) else file  # a FieldFile wraps the upload
    ext = os.path.splitext(getattr(file, "name", "") or "")[1].lower()
    kind = KIND_OF.get(ext)
    if kind not in kinds:
        allowed = sorted(e for k in kinds for e in EXTENSIONS[k])
        if tuple(kinds) == RESOURCE_KINDS:
            raise ValidationError(
                _("Upload a PDF, image, audio/video or office document (%(types)s).") % {"types": ", ".join(allowed)}
            )
        raise ValidationError(_("Only these file types can be uploaded here: %(types)s.") % {"types": ", ".join(allowed)})
    limit = _limit_mb(kind)
    if file.size > limit * 1024 * 1024:
        raise ValidationError(_("Files can be at most %(mb)s MB.") % {"mb": limit})
    upload.seek(0)
    head = upload.read(16)
    upload.seek(0)
    if not _matches(ext, head):
        raise _mismatch()
    if kind == "image":
        return _check_image(upload, ext)
    if kind == "pdf":
        _check_pdf(upload)
    elif kind == "office":
        _check_office(upload, ext)
    elif ext == ".mp3":
        _check_mp3(upload)
    elif ext == ".mp4":
        _check_mp4(upload)
    return None


@deconstructible
class UploadValidator:
    """Model field validator: `check` for a field that takes the given kinds of file."""

    def __init__(self, kinds):
        self.kinds = tuple(kinds)

    def __call__(self, value):
        if getattr(value, "_committed", False):
            return  # already stored: only new uploads are checked
        upload = value.file if isinstance(value, FieldFile) else value
        cleaned = check(value, self.kinds)
        # Remember the result so saving doesn't check (and re-encode) the same upload twice.
        try:
            upload._iga_checked = (self.kinds, cleaned)
        except AttributeError:
            pass

    def __eq__(self, other):
        return isinstance(other, UploadValidator) and other.kinds == self.kinds


def validate_upload(file):
    """Kept for migrations that name it: the resource rules."""
    check(file, RESOURCE_KINDS)
    return file


class SafeFileField(models.FileField):
    """A FileField that only stores files passing `check` for its `kinds`, images re-encoded.

    The check runs as a validator (forms, the admin, DRF serializers) and again when the instance is saved,
    so a code path that skips validation can't store an unchecked file."""

    def __init__(self, *args, kinds=RESOURCE_KINDS, **kwargs):
        self.kinds = tuple(kinds)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["kinds"] = self.kinds
        return name, path, args, kwargs

    @cached_property
    def validators(self):
        return [*self.default_validators, *self._validators, UploadValidator(self.kinds)]

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        if file and not file._committed:
            upload = file.file
            checked = getattr(upload, "_iga_checked", None)
            cleaned = checked[1] if checked and checked[0] == self.kinds else check(file, self.kinds)
            if cleaned is not None:
                file.file = ContentFile(cleaned, name=file.name)
        return super().pre_save(model_instance, add)

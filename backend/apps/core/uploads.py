"""Safe handling of uploaded files.

Each upload field lists the kinds of file it takes (SafeFileField(kinds=...)). A file is accepted only when
its extension is on that list AND its contents really are that kind of file, checked by parsing, not only
the name or the first bytes:

- images are opened and re-encoded with Pillow, which drops metadata (a phone photo's GPS position,
  comments) and anything hidden around the picture (an HTML page or a ZIP glued to a PNG). Without
  Pillow, images are refused rather than stored unchecked;
- PDFs are parsed (pypdf) and every object in them is read, including those packed in compressed
  object streams: none may hold scripts, launch actions, embedded files or forms that send data.
  Password-protected PDFs can't be checked, so they are refused. Without pypdf, PDFs are refused;
- office documents must be real ZIP packages of that format, without macros or ActiveX controls;
- MP3 and MP4 files must have the frame or box structure of their format from start to end.

HTML, SVG, scripts and every other type are refused. Each kind has a size limit. Files get random names,
and nginx serves them with headers that stop them running scripts (frontend/nginx.conf).
"""

import io
import logging
import os
import re
import uuid
import zipfile

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
try:  # pypdf reads every object of a PDF; without it, PDFs are refused (see _check_pdf).
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject, StreamObject, read_object
except ImportError:  # pragma: no cover - pypdf is in requirements.txt
    PdfReader = None
# pypdf warns about every oddity of a damaged file; uploads are checked here, the log needn't list them.
logging.getLogger("pypdf").setLevel(logging.ERROR)

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

# Names that make a PDF run code, open other programs or files, carry files, or send data somewhere,
# as dictionary keys (/JS, /EF ...) or values (/S /JavaScript, /Type /EmbeddedFile ...).
PDF_FORBIDDEN = {
    "/JavaScript",
    "/JS",
    "/Launch",
    "/EmbeddedFile",
    "/EmbeddedFiles",
    "/EF",
    "/RichMedia",
    "/XFA",
    "/ImportData",
    "/SubmitForm",
    "/GoToE",
}
# Every "<number> <number> obj" written in the file, as a viewer repairing a damaged file finds them.
_PDF_OBJECT = re.compile(rb"(?<![0-9])(\d{1,10})[ \t\r\n\f\x00]+(\d{1,5})[ \t\r\n\f\x00]+obj(?![A-Za-z0-9])")
_PDF_SPACE = b" \t\r\n\f\x00"
# Ceilings, so a crafted file can't keep a server process busy or use its memory.
PDF_MAX_OBJECTS = 200_000
PDF_UNPACK_BUDGET = 256 * 1024 * 1024


class _ActivePdf(Exception):
    pass


def _pdf_walk(obj):
    """Raise _ActivePdf if this object (with the dictionaries and arrays written inside it) names a forbidden thing."""
    stack = [obj]
    while stack:
        item = stack.pop()
        if isinstance(item, DictionaryObject):  # streams' dictionaries too
            for key, value in item.items():
                if key in PDF_FORBIDDEN:
                    raise _ActivePdf
                stack.append(value)
        elif isinstance(item, ArrayObject):
            stack.extend(item)
        elif isinstance(item, NameObject) and item in PDF_FORBIDDEN:
            raise _ActivePdf


def _pdf_object_at(data, position, reader):
    while position < len(data) and data[position] in _PDF_SPACE:
        position += 1
    stream = io.BytesIO(data)
    stream.seek(position)
    return read_object(stream, reader)


def _pdf_stream_members(stream_object, data, reader):
    """The objects packed in a compressed object stream (/Type /ObjStm) whose unpacked bytes are `data`."""
    count, first = int(stream_object["/N"]), int(stream_object["/First"])
    header = data[:first].split()
    for index in range(1, min(len(header), 2 * count), 2):
        yield _pdf_object_at(data, first + int(header[index]), reader)


def _check_pdf(file):
    """Parse the PDF and refuse it if any object in it holds scripts, launch actions, embedded files or
    forms that send data. Every object is read: those the cross-reference table points to, those a viewer
    would find by scanning a damaged file, and those packed inside compressed object streams (any filter).
    Only the PDF's structure is read, never its images or page contents, so a scanned paper doesn't trip
    over bytes that happen to spell /JS."""
    data = _read_all(file)
    if not re.match(rb"%PDF-[12]\.\d", data[:8]):
        raise _mismatch()
    if PdfReader is None:
        raise ValidationError(_("PDFs can't be checked on this server, so they can't be uploaded."))
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise ValidationError(_("Password-protected PDFs can't be checked. Remove the password and try again."))
        if len(reader.pages) < 1:
            raise _mismatch()
        _pdf_walk(reader.trailer)
        seen, budget = 0, PDF_UNPACK_BUDGET
        for match in _PDF_OBJECT.finditer(data):
            seen += 1
            if seen > PDF_MAX_OBJECTS:
                raise ValidationError(_("This document is too large when unpacked."))
            try:
                obj = _pdf_object_at(data, match.end(), reader)
            except (PyPdfError, ValueError, KeyError, TypeError, IndexError):
                continue  # not an object after all (bytes inside an image that look like one)
            _pdf_walk(obj)
            if isinstance(obj, StreamObject) and "/N" in obj and "/First" in obj:
                try:
                    unpacked = obj.get_data()  # any filter; pypdf also caps what one stream may unpack to
                    budget -= len(unpacked)
                    if budget < 0:
                        raise ValidationError(_("This document is too large when unpacked."))
                    for member in _pdf_stream_members(obj, unpacked, reader):
                        seen += 1
                        if seen > PDF_MAX_OBJECTS:
                            raise ValidationError(_("This document is too large when unpacked."))
                        _pdf_walk(member)
                except (PyPdfError, ValueError, KeyError, TypeError, IndexError):
                    if obj.get("/Type") == "/ObjStm":
                        raise _mismatch() from None  # an object stream we can't read could hide anything
    except _ActivePdf:
        raise ValidationError(
            _("This PDF contains scripts, embedded files or actions, which are not allowed. Print it to a new PDF and try again.")
        ) from None
    except ValidationError:
        raise
    except Exception:  # pypdf raises many kinds of errors for broken or hostile files
        raise _mismatch() from None
    finally:
        file.seek(0)


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


def check(file, kinds=RESOURCE_KINDS, name=None):
    """Validate a file for a field taking `kinds` (its name is `name`, or the file's own). Returns the
    cleaned bytes to store instead for images, else None."""
    upload = file.file if isinstance(file, FieldFile) else file  # a FieldFile wraps the upload
    ext = os.path.splitext(name or getattr(file, "name", "") or "")[1].lower()
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


def _remember(upload, kinds, cleaned):
    try:
        upload._iga_checked = (tuple(kinds), cleaned)
    except AttributeError:
        pass


def _checked(upload, kinds):
    """The result of an earlier check of this very upload for these kinds, or None."""
    done = getattr(upload, "_iga_checked", None)
    return done if done and done[0] == tuple(kinds) else None


@deconstructible
class UploadValidator:
    """Model field validator: `check` for a field that takes the given kinds of file."""

    def __init__(self, kinds):
        self.kinds = tuple(kinds)

    def __call__(self, value):
        if getattr(value, "_committed", False):
            return  # already stored: only new uploads are checked
        upload = value.file if isinstance(value, FieldFile) else value
        # Remember the result so saving doesn't check (and re-encode) the same upload twice.
        _remember(upload, self.kinds, check(value, self.kinds))

    def __eq__(self, other):
        return isinstance(other, UploadValidator) and other.kinds == self.kinds


def validate_upload(file):
    """Kept for migrations that name it: the resource rules."""
    check(file, RESOURCE_KINDS)
    return file


class SafeFieldFile(FieldFile):
    """Every way of storing a file in a SafeFileField ends here (a form or serializer saving the model,
    or code calling instance.field.save(name, content)), so nothing reaches the storage unchecked."""

    def save(self, name, content, save=True):
        done = _checked(content, self.field.kinds)
        cleaned = done[1] if done else check(content, self.field.kinds, name=name)
        if cleaned is not None:
            content = ContentFile(cleaned, name=name)
        super().save(name, content, save)


class SafeFileField(models.FileField):
    """A FileField that only stores files passing `check` for its `kinds`, images re-encoded.

    The check runs as a validator (forms, the admin, DRF serializers, for a clear error message) and again
    when the file is written to the storage, so a code path that skips validation can't store an unchecked
    file."""

    attr_class = SafeFieldFile

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

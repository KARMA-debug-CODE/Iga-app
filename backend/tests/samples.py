"""Small, real files of each kind the app accepts, built in memory for upload tests."""

import io
import zipfile

from PIL import Image

PAGE = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"


def pdf(*extra, catalog=b"", trailer=b"", raw=b""):
    """A one-page PDF with a correct cross-reference table. `extra` objects are numbered from 4;
    `catalog` is added to the document catalog, `trailer` to the trailer, and `raw` bytes are written
    after the objects without being listed in the table."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R " + catalog + b">>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", PAGE]
    objects += list(extra)
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    out += raw
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R " % (len(objects) + 1) + trailer + b">>\n"
    out += b"startxref\n%d\n%%%%EOF\n" % xref
    return bytes(out)


def stream(dictionary, data):
    return b"<< " + dictionary + b" /Length %d >>\nstream\n" % len(data) + data + b"\nendstream"


def object_stream(members, encode=None, filter_name=b""):
    """A compressed object stream (/Type /ObjStm) holding `members` {number: body}."""
    header, body = [], b""
    for number, member in members.items():
        header.append(b"%d %d" % (number, len(body)))
        body += member + b"\n"
    head = b" ".join(header) + b"\n"
    data = head + body
    if encode:
        data = encode(data)
    first = len(head)
    dictionary = b"/Type /ObjStm /N %d /First %d" % (len(members), first)
    if filter_name:
        dictionary += b" /Filter " + filter_name
    return stream(dictionary, data)


def image(fmt="PNG", size=(32, 24), color=(200, 30, 30), **save):
    picture = Image.new("RGB", size, color)
    out = io.BytesIO()
    picture.save(out, fmt, **save)
    return out.getvalue()


def jpeg_with_gps():
    """A photo carrying EXIF with a GPS position and a camera comment, as phones write them."""
    picture = Image.new("RGB", (40, 30), (10, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # Make
    exif[0x9286] = "secret comment"  # UserComment
    exif[0x8825] = {1: "S", 2: (1.0, 57.0, 0.0), 3: "E", 4: (30.0, 3.0, 0.0)}  # GPS: Kigali
    out = io.BytesIO()
    picture.save(out, "JPEG", exif=exif.tobytes())
    return out.getvalue()


def docx(extra=None, content_types=b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr(
            "[Content_Types].xml",
            b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            b'<Override PartName="/word/document.xml" ContentType="' + content_types + b'"/></Types>',
        )
        package.writestr("word/document.xml", b'<?xml version="1.0"?><w:document/>')
        for name, data in (extra or {}).items():
            package.writestr(name, data)
    return out.getvalue()


def odt():
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as package:
        package.writestr("mimetype", b"application/vnd.oasis.opendocument.text")
        package.writestr("content.xml", b'<?xml version="1.0"?><office:document-content/>')
    return out.getvalue()


def mp3(frames=5):
    # MPEG-1 layer III, 128 kbit/s, 44.1 kHz: 417-byte frames.
    frame = b"\xff\xfb\x90\x00" + b"\x00" * 413
    return b"ID3\x03\x00\x00\x00\x00\x00\x00" + frame * frames


def mp4():
    ftyp = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
    moov = b"\x00\x00\x00\x08moov"
    mdat = b"\x00\x00\x00\x10mdat" + b"\x00" * 8
    return ftyp + moov + mdat

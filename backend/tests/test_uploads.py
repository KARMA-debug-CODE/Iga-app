"""Uploads are checked by their real contents, per field (apps/core/uploads.py)."""

import base64
import binascii
import io
import random
import zlib

import pytest
from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import RequestFactory
from PIL import Image
from pypdf import PdfWriter
from pypdf.actions import JavaScript

from apps.assessments.models import ExamPaper
from apps.core import uploads
from apps.curriculum.models import Resource

from . import samples

pytestmark = pytest.mark.django_db

HTML = b"<html><body><script>alert(document.domain)</script></body></html>"


@pytest.fixture(autouse=True)
def _media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path


def upload(client, subject, name, content):
    return client.post(
        "/api/resources/",
        {"subject": subject.id, "kind": "notes", "title": "Notes", "file": SimpleUploadedFile(name, content)},
        format="multipart",
    )


def stored_bytes():
    resource = Resource.objects.get()
    with resource.file.open("rb") as handle:
        return handle.read()


def test_pdf_upload_gets_a_random_name(client_for, teacher, subject):
    response = upload(client_for(teacher), subject, "../../etc/My Notes.PDF", samples.pdf())
    assert response.status_code == 201, response.data
    stored = Resource.objects.get().file.name
    assert stored.startswith("resources/") and stored.endswith(".pdf")
    assert "Notes" not in stored and ".." not in stored


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("page.html", HTML),
        ("page.htm", HTML),
        ("image.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'),
        ("drawing.svgz", b"\x1f\x8b\x08\x00"),
        ("notes.xhtml", HTML),
        ("script.js", b"alert(1)"),
        ("setup.exe", b"MZ\x90\x00"),
        ("notes.txt", b"plain"),
        ("archive.zip", samples.docx()),
        ("macro.docm", samples.docx()),
        ("notes", samples.pdf()),  # no extension
        ("notes.pdf.html", HTML),  # only the last extension counts
    ],
)
def test_types_outside_the_allowlist_are_refused(client_for, teacher, subject, name, content):
    response = upload(client_for(teacher), subject, name, content)
    assert response.status_code == 400
    assert not Resource.objects.exists()


@pytest.mark.parametrize(
    ("name", "content"),
    [
        # Polyglots: the right first bytes for the extension, then an HTML page.
        ("photo.png", b"\x89PNG\r\n\x1a\n" + HTML),
        ("photo.jpg", b"\xff\xd8\xff\xe0" + HTML),
        ("photo.gif", b"GIF89a" + HTML),
        ("photo.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 " + HTML),
        ("notes.docx", b"PK\x03\x04" + HTML),
        ("notes.xlsx", b"PK\x03\x04" + HTML),
        ("clip.mp4", b"\x00\x00\x00\x18ftyp" + HTML),
        ("song.mp3", b"ID3" + HTML),
        ("song.mp3", b"\xff\xfb" + HTML),
        ("paper.pdf", b"%PDF-1.4\n" + HTML),
        # Mislabelled: a real file of another kind.
        ("notes.pdf", HTML),
        ("photo.png", samples.image("GIF")),
        ("photo.jpg", samples.image("PNG")),
        ("photo.gif", samples.image("JPEG")),
        ("notes.pdf", samples.image("PNG")),
        ("notes.docx", samples.odt()),
        ("notes.odt", samples.docx()),
        ("notes.pptx", samples.docx()),  # a Word document named as a slide deck
        ("clip.mp4", samples.mp3()),
        ("song.mp3", samples.mp4()),
        # An HTML page in front of a real file.
        ("photo.png", HTML + samples.image("PNG")),
        ("notes.pdf", HTML + samples.pdf()),
        ("notes.docx", HTML + samples.docx()),
    ],
)
def test_polyglot_and_mislabelled_files_are_refused(client_for, teacher, subject, name, content):
    response = upload(client_for(teacher), subject, name, content)
    assert response.status_code == 400, name
    assert not Resource.objects.exists()


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("notes.pdf", samples.pdf()),
        ("photo.png", samples.image("PNG")),
        ("photo.jpg", samples.image("JPEG")),
        ("photo.jpeg", samples.image("JPEG")),
        ("photo.gif", samples.image("GIF")),
        ("photo.webp", samples.image("WEBP")),
        ("notes.docx", samples.docx()),
        ("notes.odt", samples.odt()),
        ("song.mp3", samples.mp3()),
        ("clip.mp4", samples.mp4()),
    ],
)
def test_real_files_of_each_allowed_kind_are_accepted(client_for, teacher, subject, name, content):
    response = upload(client_for(teacher), subject, name, content)
    assert response.status_code == 201, (name, response.data)
    assert Resource.objects.get().file.name.endswith(name[name.rindex(".") :])


# --- Images are re-encoded --------------------------------------------------


def test_photo_metadata_is_removed(client_for, teacher, subject):
    original = samples.jpeg_with_gps()
    assert Image.open(io.BytesIO(original)).getexif()  # the test photo really carries EXIF
    response = upload(client_for(teacher), subject, "photo.jpg", original)
    assert response.status_code == 201, response.data
    stored = stored_bytes()
    picture = Image.open(io.BytesIO(stored))
    assert picture.format == "JPEG" and picture.size == (40, 30)
    assert not picture.getexif()
    assert b"secret comment" not in stored and b"PhoneMaker" not in stored and b"Exif" not in stored


def test_payload_glued_to_a_real_image_is_dropped(client_for, teacher, subject):
    # A valid PNG with an HTML page and a ZIP archive after its end, and a text chunk inside it.
    png = samples.image("PNG")
    text_chunk = b"tEXt" + b"Comment\x00<script>alert(1)</script>"
    chunk = len(text_chunk[4:]).to_bytes(4, "big") + text_chunk + binascii.crc32(text_chunk).to_bytes(4, "big")
    crafted = png[:33] + chunk + png[33:] + HTML + samples.docx()
    assert Image.open(io.BytesIO(crafted)).info.get("Comment")
    response = upload(client_for(teacher), subject, "photo.png", crafted)
    assert response.status_code == 201, response.data
    stored = stored_bytes()
    assert b"<script>" not in stored and b"PK\x03\x04" not in stored
    assert stored.endswith(b"IEND\xaeB`\x82")
    assert Image.open(io.BytesIO(stored)).size == (32, 24)


def test_animated_gif_keeps_its_frames(client_for, teacher, subject):
    frames = [Image.new("RGB", (16, 16), color) for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    out = io.BytesIO()
    frames[0].save(out, "GIF", save_all=True, append_images=frames[1:], duration=200, loop=0, comment=b"hidden")
    response = upload(client_for(teacher), subject, "anim.gif", out.getvalue())
    assert response.status_code == 201, response.data
    stored = stored_bytes()
    assert Image.open(io.BytesIO(stored)).n_frames == 3
    assert b"hidden" not in stored


def test_decompression_bomb_is_refused(client_for, teacher, subject, settings):
    settings.UPLOAD_IMAGE_MAX_PIXELS = 4_000_000
    out = io.BytesIO()
    Image.new("L", (3000, 3000)).save(out, "PNG")  # 9 million pixels in a few kilobytes
    assert len(out.getvalue()) < 100_000
    response = upload(client_for(teacher), subject, "big.png", out.getvalue())
    assert response.status_code == 400
    assert "million pixels" in str(response.data)


def test_truncated_image_is_refused(client_for, teacher, subject):
    response = upload(client_for(teacher), subject, "cut.jpg", samples.image("JPEG", size=(200, 200))[:300])
    assert response.status_code == 400


def test_images_have_their_own_size_limit(client_for, teacher, subject, settings):
    settings.UPLOAD_IMAGE_MAX_MB = 1
    settings.UPLOAD_MAX_MB = 20
    noise = Image.frombytes("RGB", (700, 700), random.Random(1).randbytes(700 * 700 * 3))
    out = io.BytesIO()
    noise.save(out, "PNG")
    assert len(out.getvalue()) > 1024 * 1024
    response = upload(client_for(teacher), subject, "big.png", out.getvalue())
    assert response.status_code == 400
    assert "1 MB" in str(response.data)
    # A PDF of the same size is fine: the general limit applies to it.
    padded = samples.pdf(samples.stream(b"/Type /XObject /Subtype /Image", b"\x00" * len(out.getvalue())))
    assert upload(client_for(teacher), subject, "big.pdf", padded).status_code == 201


def test_upload_size_limit(client_for, teacher, subject, settings):
    settings.UPLOAD_MAX_MB = 1
    big = samples.pdf(samples.stream(b"/Type /XObject /Subtype /Image", b"0" * (1024 * 1024 + 1)))
    response = upload(client_for(teacher), subject, "big.pdf", big)
    assert response.status_code == 400


# --- PDFs -------------------------------------------------------------------

JS_ACTION = b"<< /S /JavaScript /JS (app.alert\\(1\\)) >>"


def _flate_object_stream_pdf(members):
    return samples.pdf(samples.object_stream(members, zlib.compress, b"/FlateDecode"), catalog=b"/OpenAction 5 0 R ")


@pytest.mark.parametrize(
    "content",
    [
        samples.pdf(catalog=b"/OpenAction " + JS_ACTION),
        samples.pdf(catalog=b"/OpenAction << /S /J#61vaScript /J#53 (app.alert\\(1\\)) >>"),  # names with #xx escapes
        samples.pdf(catalog=b"/OpenAction << /S /Launch /F (cmd.exe) >>"),
        samples.pdf(JS_ACTION, catalog=b"/Names << /JavaScript << /Names [(x) 4 0 R] >> >>"),
        samples.pdf(samples.stream(b"", b"<xdp/>"), catalog=b"/AcroForm << /XFA 4 0 R >>"),
        samples.pdf(catalog=b"/OpenAction << /S /SubmitForm /F (https://example.com/collect) >>"),
        samples.pdf(catalog=b"/OpenAction << /S /ImportData /F (data.fdf) >>"),
        samples.pdf(catalog=b"/OpenAction << /S /GoToE /T << /R /C /N (x) >> >>"),
        # Inside a compressed object stream, Flate or another filter.
        _flate_object_stream_pdf({5: JS_ACTION}),
        samples.pdf(
            samples.object_stream({5: JS_ACTION}, lambda d: base64.b16encode(d) + b">", b"/ASCIIHexDecode"),
            catalog=b"/OpenAction 5 0 R ",
        ),
        # Not listed in the cross-reference table: a viewer repairing the file still finds it.
        samples.pdf(catalog=b"/OpenAction 9 0 R ", raw=b"9 0 obj\n" + JS_ACTION + b"\nendobj\n"),
        # Hidden after a comment that looks like the start of a stream.
        samples.pdf(raw=b"% >> stream\n9 0 obj\n" + JS_ACTION + b"\nendobj\n% endstream\n"),
        # Written inside another stream's data, where the table can point.
        samples.pdf(samples.stream(b"/Type /XObject /Subtype /Form", b"9 0 obj\n" + JS_ACTION + b"\nendobj\n")),
    ],
)
def test_pdfs_with_scripts_or_actions_are_refused(client_for, teacher, subject, content):
    response = upload(client_for(teacher), subject, "paper.pdf", content)
    assert response.status_code == 400
    assert "scripts" in str(response.data)
    assert not Resource.objects.exists()


def test_pdf_with_an_embedded_file_is_refused(client_for, teacher, subject):
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    writer.add_attachment("run.exe", b"MZ\x90\x00")
    out = io.BytesIO()
    writer.write(out)
    response = upload(client_for(teacher), subject, "paper.pdf", out.getvalue())
    assert response.status_code == 400
    assert "embedded files" in str(response.data)


def test_pdf_with_javascript_written_by_a_pdf_library_is_refused(client_for, teacher, subject):
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    writer.add_open_action(JavaScript("app.alert('hi');"))
    out = io.BytesIO()
    writer.write(out)
    assert upload(client_for(teacher), subject, "paper.pdf", out.getvalue()).status_code == 400


def test_password_protected_pdf_is_refused(client_for, teacher, subject):
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    writer.encrypt("secret", algorithm="AES-128")
    out = io.BytesIO()
    writer.write(out)
    response = upload(client_for(teacher), subject, "paper.pdf", out.getvalue())
    assert response.status_code == 400
    assert "Password-protected" in str(response.data)


def test_scanned_pdf_whose_image_bytes_spell_javascript_is_accepted(client_for, teacher, subject):
    # Image and page data are never read as PDF structure: bytes that spell /JS or /Launch inside a
    # scanned page must not get a past paper refused.
    noise = b"\x8f\x13/JS (x) /JavaScript /Launch /EmbeddedFile \x00\xff" * 2000
    content = samples.pdf(
        samples.stream(b"/Type /XObject /Subtype /Image /Width 1 /Height 1 /Filter /DCTDecode", noise),
        samples.stream(b"/Filter /FlateDecode", zlib.compress(noise)),
    )
    response = upload(client_for(teacher), subject, "scan.pdf", content)
    assert response.status_code == 201, response.data


def test_pdf_with_ordinary_links_and_object_streams_is_accepted(client_for, teacher, subject):
    link = b"<< /Type /Annot /Subtype /Link /Rect [0 0 10 10] /A << /S /URI /URI (https://www.reb.rw/) >> >>"
    content = _flate_object_stream_pdf({5: b"<< /S /URI /URI (https://www.reb.rw/) >>", 6: link})
    response = upload(client_for(teacher), subject, "paper.pdf", content)
    assert response.status_code == 201, response.data


def test_pdf_that_is_not_parseable_is_refused(client_for, teacher, subject):
    assert upload(client_for(teacher), subject, "paper.pdf", b"%PDF-1.7\n" + b"\x00garbage" * 100).status_code == 400


# --- Office documents and media ---------------------------------------------


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("macro.docx", samples.docx({"word/vbaProject.bin": b"\xd0\xcf\x11\xe0macro"})),
        ("macro.docx", samples.docx(content_types=b"application/vnd.ms-word.document.macroEnabled.main+xml")),
        ("activex.docx", samples.docx({"word/activeX/activeX1.xml": b"<ax/>"})),
    ],
)
def test_office_documents_with_macros_are_refused(client_for, teacher, subject, name, content):
    response = upload(client_for(teacher), subject, name, content)
    assert response.status_code == 400
    assert "macros" in str(response.data)


def test_office_document_that_unpacks_to_too_much_is_refused(client_for, teacher, subject, monkeypatch):
    monkeypatch.setattr(uploads, "ZIP_MAX_UNPACKED", 10_000)
    content = samples.docx({"word/media/big.bin": b"\x00" * 20_000})  # compresses to almost nothing
    response = upload(client_for(teacher), subject, "notes.docx", content)
    assert response.status_code == 400
    assert "too large" in str(response.data)


def test_media_with_trailing_html_is_refused(client_for, teacher, subject):
    assert upload(client_for(teacher), subject, "clip.mp4", samples.mp4() + HTML).status_code == 400


# --- Every way of storing a file is checked ---------------------------------


def test_exam_papers_take_pdfs_only_in_the_admin(admin_user, subject):
    request = RequestFactory().get("/")
    request.user = admin_user
    form_class = site._registry[ExamPaper].get_form(request)
    data = {"subject": subject.id, "level": "O", "year": 2024, "title": "Maths 2024", "kind": "national"}
    for name, content in (("evil page.html", HTML), ("photo.png", samples.image("PNG")), ("p.pdf", HTML)):
        form = form_class(data=data, files={"paper_file": SimpleUploadedFile(name, content)})
        assert not form.is_valid()
        assert "paper_file" in form.errors
    form = form_class(data=data, files={"paper_file": SimpleUploadedFile("Maths 2024.pdf", samples.pdf())})
    assert form.is_valid(), form.errors
    paper = form.save()
    assert paper.paper_file.name.startswith("exam_papers/") and "Maths" not in paper.paper_file.name


def test_code_that_skips_validation_still_cannot_store_an_unsafe_file(teacher, subject):
    resource = Resource(subject=subject, kind="notes", title="Notes", uploaded_by=teacher)
    resource.file = ContentFile(HTML, name="notes.pdf")
    with pytest.raises(ValidationError), transaction.atomic():
        resource.save()
    paper = ExamPaper.objects.create(subject=subject, level="O", year=2024, title="P")
    with pytest.raises(ValidationError), transaction.atomic():
        paper.paper_file.save("paper.html", ContentFile(HTML))
    with pytest.raises(ValidationError), transaction.atomic():
        paper.marking_guide_file.save("guide.png", ContentFile(samples.image("PNG")))
    assert not Resource.objects.exists()
    paper.refresh_from_db()
    assert not paper.paper_file and not paper.marking_guide_file


def test_images_saved_from_code_are_re_encoded_too(teacher, subject):
    resource = Resource.objects.create(subject=subject, kind="notes", title="Photo", uploaded_by=teacher)
    resource.file.save("photo.jpg", ContentFile(samples.jpeg_with_gps()))
    with resource.file.open("rb") as handle:
        assert b"PhoneMaker" not in handle.read()


def test_stored_files_are_not_checked_again_on_unrelated_saves(teacher, subject, monkeypatch):
    resource = Resource.objects.create(subject=subject, kind="notes", title="Notes", uploaded_by=teacher)
    resource.file.save("notes.pdf", ContentFile(samples.pdf()))
    calls = []
    monkeypatch.setattr(uploads, "check", lambda *args, **kwargs: calls.append(args))
    resource.title = "Renamed"
    resource.full_clean()
    resource.save()
    assert calls == []


def test_one_upload_is_checked_once(client_for, teacher, subject, monkeypatch):
    real_check, calls = uploads.check, []

    def counting_check(*args, **kwargs):
        calls.append(args)
        return real_check(*args, **kwargs)

    monkeypatch.setattr(uploads, "check", counting_check)
    assert upload(client_for(teacher), subject, "photo.jpg", samples.jpeg_with_gps()).status_code == 201
    assert len(calls) == 1

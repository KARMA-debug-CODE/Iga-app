"""Uploaded files are private and are sent with headers that stop them running anything
(apps/core/media.py, apps/curriculum/downloads.py, apps/schools/downloads.py, frontend/nginx.conf)."""

import re
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.urls import get_resolver
from django.views.static import serve

from apps.assessments.models import ExamPaper
from apps.core import checks, media
from apps.core.constants import ContentStatus
from apps.curriculum import downloads
from apps.curriculum.models import Resource

from . import samples

pytestmark = pytest.mark.django_db
REPO = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def _media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.PROTECTED_MEDIA_ACCEL = False


def make_resource(teacher, subject, name="notes.pdf", content=None, status=ContentStatus.PUBLISHED, title="Fractions"):
    resource = Resource.objects.create(subject=subject, kind="notes", title=title, uploaded_by=teacher, status=status)
    resource.file.save(name, ContentFile(content if content is not None else samples.pdf()))
    return resource


def file_link(client, resource):
    data = client.get(f"/api/resources/{resource.id}/").data
    return data["file_url"].replace("http://testserver", "")


def test_resource_files_have_no_public_url(client_for, student, teacher, subject):
    resource = make_resource(teacher, subject)
    link = file_link(client_for(student), resource)
    assert link.startswith("/api/files/resources/") and "/media/" not in link
    assert resource.file.name not in link
    # Not even with the stored name: Django has no /media/ route (nginx answers 404 there too).
    assert client_for(student).get(f"/media/{resource.file.name}").status_code == 404
    assert not any(getattr(p, "callback", None) is serve for p in get_resolver().url_patterns)
    assert "static(settings.MEDIA_URL" not in (REPO / "backend" / "config" / "urls.py").read_text()


def test_pdf_opens_inline_with_a_policy_that_blocks_scripts(client_for, student, teacher, subject):
    resource = make_resource(teacher, subject, title='Fractions "S2"\r\nX-Evil: 1 / Imibare é')
    response = client_for().get(file_link(client_for(student), resource))
    assert response.status_code == 200
    assert b"".join(response.streaming_content).startswith(b"%PDF-")
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"].startswith("inline;")
    assert "\n" not in response["Content-Disposition"] and "X-Evil" not in response.headers
    assert "filename*=utf-8''" in response["Content-Disposition"]  # the French title survives, encoded
    assert response["Content-Security-Policy"] == "default-src 'none'; object-src 'none'; script-src 'none'"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize(
    ("name", "content", "content_type", "inline", "csp"),
    [
        ("photo.png", samples.image("PNG"), "image/png", True, media.CSP_MEDIA),
        ("photo.jpg", samples.image("JPEG"), "image/jpeg", True, media.CSP_MEDIA),
        ("song.mp3", samples.mp3(), "audio/mpeg", True, media.CSP_MEDIA),
        ("clip.mp4", samples.mp4(), "video/mp4", True, media.CSP_MEDIA),
        ("notes.docx", samples.docx(), media.CONTENT_TYPES[".docx"], False, media.CSP_DEFAULT),
        ("notes.odt", samples.odt(), media.CONTENT_TYPES[".odt"], False, media.CSP_DEFAULT),
    ],
)
def test_each_kind_gets_its_type_disposition_and_sandbox(
    client_for, student, teacher, subject, name, content, content_type, inline, csp
):
    resource = make_resource(teacher, subject, name=name, content=content)
    response = client_for().get(file_link(client_for(student), resource))
    assert response.status_code == 200
    assert response["Content-Type"] == content_type
    assert response["Content-Disposition"].startswith("inline;" if inline else "attachment;")
    assert response["Content-Security-Policy"] == csp
    assert csp == media.CSP_PDF or csp.startswith("sandbox;")
    assert response["X-Content-Type-Options"] == "nosniff"


def test_an_unknown_stored_file_is_a_sandboxed_download(teacher, subject):
    # A file that somehow got past the checks (an old upload, a manual copy) still can't run.
    content_type, inline, csp = media.policy("resources/old.html")
    assert (content_type, inline, csp) == ("application/octet-stream", False, media.CSP_DEFAULT)
    assert media.policy("resources/x.svg")[1] is False


def test_files_waiting_for_review_reach_only_their_uploader_and_admins(
    client_for, student, teacher, other_teacher, admin_user, subject
):
    resource = make_resource(teacher, subject, status=ContentStatus.REVIEW)
    assert client_for(student).get(f"/api/resources/{resource.id}/").status_code == 404
    for user in (teacher, admin_user):
        assert client_for().get(file_link(client_for(user), resource)).status_code == 200
    # A link handed to someone else is checked against the person it was made for, not who opens it;
    # a forged one for another user doesn't verify.
    forged = downloads.signed_resource_url(None, resource, student).replace("/api/files/resources/", "")
    assert client_for().get(f"/api/files/resources/{forged[:-1]}x/").status_code == 404
    assert client_for().get(downloads.signed_resource_url(None, resource, student)).status_code == 404
    assert client_for().get(downloads.signed_resource_url(None, resource, other_teacher)).status_code == 404


def test_admins_can_open_an_uploaded_file_from_the_review_queue(client_for, teacher, admin_user, subject):
    resource = make_resource(teacher, subject, status=ContentStatus.REVIEW)
    items = client_for(admin_user).get("/api/admin/review/").data
    item = next(i for i in items if i["type"] == "resource" and i["id"] == resource.id)
    link = item["url"].replace("http://testserver", "")
    assert link.startswith("/api/files/resources/")
    assert client_for().get(link).status_code == 200


def test_old_links_stop_working(client_for, student, teacher, subject, monkeypatch):
    resource = make_resource(teacher, subject)
    link = file_link(client_for(student), resource)
    assert client_for().get(link).status_code == 200
    # Sent back to review: published no more.
    Resource.objects.filter(pk=resource.pk).update(status=ContentStatus.REVIEW)
    assert client_for().get(link).status_code == 404
    Resource.objects.filter(pk=resource.pk).update(status=ContentStatus.PUBLISHED)
    # The viewer's account is switched off.
    student.is_active = False
    student.save(update_fields=["is_active"])
    assert client_for().get(link).status_code == 404
    student.is_active = True
    student.save(update_fields=["is_active"])
    assert client_for().get(link).status_code == 200
    # Expired.
    monkeypatch.setattr(downloads, "LINK_SECONDS", -1)
    assert client_for().get(link).status_code == 404
    monkeypatch.setattr(downloads, "LINK_SECONDS", 3600)
    # Deleted.
    resource.delete()
    assert client_for().get(link).status_code == 404
    assert client_for().get("/api/files/resources/forged-token/").status_code == 404


def test_behind_nginx_the_file_is_sent_from_the_internal_location(client_for, student, teacher, subject, settings):
    settings.PROTECTED_MEDIA_ACCEL = True
    resource = make_resource(teacher, subject, name="notes.docx", content=samples.docx())
    response = client_for().get(file_link(client_for(student), resource))
    assert response["X-Accel-Redirect"] == f"/protected-media/{resource.file.name}"
    assert response.content == b""
    assert response["Content-Disposition"].startswith("attachment;")


def test_past_papers_get_the_same_safe_headers(client_for, student, subject):
    paper = ExamPaper.objects.create(subject=subject, level="O", year=2024, title="Maths 2024")
    paper.paper_file.save("paper.pdf", ContentFile(samples.pdf()))
    # A title stored before titles were cleaned (apps/core/text.py) can't add a header line either.
    ExamPaper.objects.filter(pk=paper.pk).update(title="Maths\r\n2024")
    link = client_for(student).get(f"/api/exam-papers/{paper.id}/").data["paper_link"].replace("http://testserver", "")
    response = client_for().get(link)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == 'inline; filename="Maths2024.pdf"'
    assert response["Content-Security-Policy"] == media.CSP_PDF
    assert response["X-Content-Type-Options"] == "nosniff"


def test_nginx_never_serves_uploads_directly_and_uses_the_same_policy():
    conf = (REPO / "frontend" / "nginx.conf").read_text()
    assert re.search(r"location \^~ /media/ \{\s*return 404;\s*\}", conf)
    internal = re.search(r"location \^~ /protected-media/ \{(.*?)\n    \}", conf, re.S).group(1)
    assert "internal;" in internal
    assert "add_header X-Content-Type-Options nosniff always;" in internal
    assert "add_header Content-Security-Policy $upload_csp always;" in internal
    policies = dict(
        re.findall(
            r'^\s+(default|"[^"]+")\s+"([^"]+)";', re.search(r"map \$uri \$upload_csp \{(.*?)\}", conf, re.S).group(1), re.M
        )
    )
    assert policies["default"] == media.CSP_DEFAULT
    assert policies['"~*\\.pdf$"'] == media.CSP_PDF
    assert policies['"~*\\.(png|jpe?g|gif|webp|mp3|mp4)$"'] == media.CSP_MEDIA
    assert set(media.MEDIA_EXTENSIONS) == {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".mp4"}


def test_stored_files_go_when_no_row_uses_them(teacher, subject, settings, django_capture_on_commit_callbacks):
    storage_root = Path(settings.MEDIA_ROOT)
    with django_capture_on_commit_callbacks(execute=True):
        resource = make_resource(teacher, subject)
    first = storage_root / resource.file.name
    assert first.exists()
    # Replaced by a new upload: the old file goes.
    with django_capture_on_commit_callbacks(execute=True):
        resource.file.save("new.pdf", ContentFile(samples.pdf()))
    second = storage_root / resource.file.name
    assert second.exists() and not first.exists()
    # Saving without touching the file keeps it.
    with django_capture_on_commit_callbacks(execute=True):
        resource.title = "Renamed"
        resource.save()
    assert second.exists()
    # A file another row still uses is kept.
    twin = Resource.objects.create(subject=subject, kind="notes", title="Twin", uploaded_by=teacher, file=resource.file.name)
    with django_capture_on_commit_callbacks(execute=True):
        twin.delete()
    assert second.exists()
    # Deleted with its row.
    with django_capture_on_commit_callbacks(execute=True):
        resource.delete()
    assert not second.exists()


def test_media_root_must_stay_out_of_static_folders(settings, tmp_path):
    settings.STATIC_ROOT = tmp_path / "static"
    settings.MEDIA_ROOT = tmp_path / "media"
    assert checks.media_root_check(None) == []
    for inside in (tmp_path / "static", tmp_path / "static" / "uploads", tmp_path):
        settings.MEDIA_ROOT = inside
        assert [e.id for e in checks.media_root_check(None)] == ["iga.E013"]
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.STATICFILES_DIRS = [("extra", tmp_path / "media" / "public")]
    assert [e.id for e in checks.media_root_check(None)] == ["iga.E013"]

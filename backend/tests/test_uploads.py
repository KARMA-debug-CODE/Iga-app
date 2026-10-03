import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.curriculum.models import Resource

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path


def upload(client, subject, name, content):
    return client.post(
        "/api/resources/",
        {"subject": subject.id, "kind": "notes", "title": "Notes", "file": SimpleUploadedFile(name, content)},
        format="multipart",
    )


def test_pdf_upload_gets_a_random_name(client_for, teacher, subject):
    response = upload(client_for(teacher), subject, "../../etc/My Notes.PDF", b"%PDF-1.7 ...")
    assert response.status_code == 201, response.data
    stored = Resource.objects.get().file.name
    assert stored.startswith("resources/") and stored.endswith(".pdf")
    assert "Notes" not in stored and ".." not in stored


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("page.html", b"<script>alert(1)</script>"),
        ("image.svg", b"<svg onload=alert(1)>"),
        ("notes.pdf", b"<html><script>alert(1)</script>"),  # wrong contents for the extension
        ("photo.png", b"GIF89a..."),
    ],
)
def test_unsafe_or_mislabelled_uploads_are_refused(client_for, teacher, subject, name, content):
    response = upload(client_for(teacher), subject, name, content)
    assert response.status_code == 400
    assert not Resource.objects.exists()


def test_upload_size_limit(client_for, teacher, subject, settings):
    settings.UPLOAD_MAX_MB = 1
    response = upload(client_for(teacher), subject, "big.pdf", b"%PDF-" + b"0" * (1024 * 1024 + 1))
    assert response.status_code == 400

"""Oversized requests are refused with a JSON 413 before any view reads them (nginx refuses them first in
production; these limits protect a deployment without it). See DATA_UPLOAD_* in config/settings.py."""

import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db


def test_defaults_keep_json_bodies_small(settings):
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE == 2 * 1024 * 1024
    assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE <= 2 * 1024 * 1024
    assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS <= 1000
    assert settings.DATA_UPLOAD_MAX_NUMBER_FILES <= 10


def test_an_oversized_json_body_is_refused(settings):
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024
    body = json.dumps({"identifier": "someone", "password": "x" * (65 * 1024)})
    response = APIClient().post("/api/auth/login/", body, content_type="application/json")
    assert response.status_code == 413
    assert response["Content-Type"] == "application/json"
    assert response.json() == {"detail": "This request is too large."}
    assert AuditLog.objects.filter(action="request_too_large").exists()


def test_the_refusal_speaks_french(settings):
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 1024
    response = APIClient().post(
        "/api/auth/login/", json.dumps({"pad": "x" * 2048}), content_type="application/json", HTTP_ACCEPT_LANGUAGE="fr"
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "Cette requête est trop volumineuse."}


def test_a_body_just_under_the_limit_is_read(settings):
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024
    body = json.dumps({"identifier": "someone", "password": "wrong-password", "note": "x" * (60 * 1024)})
    response = APIClient().post("/api/auth/login/", body, content_type="application/json")
    assert response.status_code == 401  # read and checked: a wrong password, not a refusal


def test_too_many_form_fields_are_refused(settings):
    settings.DATA_UPLOAD_MAX_NUMBER_FIELDS = 50
    body = "&".join(f"field{i}=1" for i in range(51))
    response = APIClient().post("/api/auth/login/", body, content_type="application/x-www-form-urlencoded")
    assert response.status_code == 413
    assert response.json() == {"detail": "This request has too many fields or files."}


def test_too_many_files_are_refused(settings, teacher, client_for):
    settings.DATA_UPLOAD_MAX_NUMBER_FILES = 2
    files = {f"file{i}": SimpleUploadedFile(f"notes{i}.txt", b"notes", content_type="text/plain") for i in range(3)}
    response = client_for(teacher).post("/api/resources/", {"title": "Notes", **files}, format="multipart")
    assert response.status_code == 413

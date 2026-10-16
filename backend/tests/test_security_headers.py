"""S41: security headers on Django's answers (nginx sends the app's own; frontend/tests/nginx tests those)."""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

API_POLICY = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"


def test_api_answers_carry_every_security_header(student, client_for):
    for client, path in [(APIClient(), "/api/meta/"), (client_for(student), "/api/dashboard/"), (APIClient(), "/api/nowhere/")]:
        response = client.get(path)
        assert response["Content-Security-Policy"] == API_POLICY, path
        assert response["X-Frame-Options"] == "DENY", path
        assert response["X-Content-Type-Options"] == "nosniff", path
        assert response["Referrer-Policy"] == "same-origin", path
        assert response["Cross-Origin-Opener-Policy"] == "same-origin", path
        assert response["Cross-Origin-Resource-Policy"] == "same-origin", path
        assert "camera=()" in response["Permissions-Policy"] and "geolocation=()" in response["Permissions-Policy"], path


def test_refusals_carry_them_too():
    response = APIClient().get("/api/dashboard/")  # not signed in
    assert response.status_code == 401
    assert response["Content-Security-Policy"] == API_POLICY


def test_the_django_admin_may_use_its_own_scripts_and_styles():
    response = APIClient().get("/django-admin/login/")
    policy = response["Content-Security-Policy"]
    assert "script-src 'self'" in policy and "'unsafe-eval'" not in policy
    assert "frame-ancestors 'none'" in policy and "object-src 'none'" in policy


def test_santas_stream_has_them(student, client_for, settings):
    settings.SANTA_URL = ""
    response = client_for(student).post("/api/tutor/stream/", {"message": "cell membrane"}, format="json")
    assert response["Content-Security-Policy"] == API_POLICY

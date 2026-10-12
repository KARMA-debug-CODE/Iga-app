"""Cookie flags (S20) and cross-site requests against the cookie-authenticated endpoints (S24)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
BACKEND = Path(__file__).resolve().parent.parent


def logged_in():
    client = APIClient()
    response = client.post("/api/auth/login/", {"identifier": "student", "password": PASSWORD}, format="json")
    assert response.status_code == 200
    return client, response


def test_refresh_cookie_flags_in_the_set_cookie_header(student):
    _, response = logged_in()
    header = response.cookies["iga_refresh"].output(header="").strip()
    parts = {p.strip().split("=")[0].lower(): p.strip() for p in header.split(";")}
    assert "httponly" in parts
    assert parts["samesite"] == "SameSite=Strict"
    assert parts["path"] == "Path=/api/auth/"
    assert parts["max-age"] == "Max-Age=1209600"
    assert "secure" not in parts  # the tests run over plain HTTP


def test_refresh_cookie_is_secure_under_https(student, settings):
    settings.REFRESH_COOKIE_SECURE = True
    _, response = logged_in()
    assert "Secure" in response.cookies["iga_refresh"].output()
    client = APIClient()
    client.cookies["iga_refresh"] = response.cookies["iga_refresh"].value
    rotated = client.post("/api/auth/refresh/")
    assert rotated.status_code == 200 and "Secure" in rotated.cookies["iga_refresh"].output()


def test_production_settings_secure_every_cookie():
    """Settings as gunicorn loads them in production: DEBUG off, HTTPS on by default."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SECRET_KEY": "x" * 50,
        "FIELD_ENCRYPTION_KEY": "Cs1lH4LCoM_SJMFjbM3MgKs5oXGkNVW3PVlO81oU1EM=",
    }
    code = (
        "import json; from config import settings as s; print(json.dumps({k: getattr(s, k, None) for k in ["
        "'REFRESH_COOKIE_SECURE','REFRESH_COOKIE_SAMESITE','SESSION_COOKIE_SECURE','SESSION_COOKIE_HTTPONLY',"
        "'SESSION_COOKIE_SAMESITE','SESSION_COOKIE_PATH','CSRF_COOKIE_SECURE','CSRF_COOKIE_HTTPONLY',"
        "'CSRF_COOKIE_PATH','SECURE_SSL_REDIRECT','SECURE_HSTS_SECONDS','SESSION_COOKIE_AGE']}))"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, check=True)
    values = json.loads(result.stdout)
    assert values == {
        "REFRESH_COOKIE_SECURE": True,
        "REFRESH_COOKIE_SAMESITE": "Strict",
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_PATH": "/django-admin/",
        "CSRF_COOKIE_SECURE": True,
        "CSRF_COOKIE_HTTPONLY": True,
        "CSRF_COOKIE_PATH": "/django-admin/",
        "SECURE_SSL_REDIRECT": True,
        "SECURE_HSTS_SECONDS": 31536000,
        "SESSION_COOKIE_AGE": 8 * 3600,
    }


@pytest.mark.parametrize(
    "headers",
    [
        {"HTTP_ORIGIN": "https://evil.example"},
        {"HTTP_ORIGIN": "null"},  # a sandboxed frame or a data: page
        {"HTTP_REFERER": "https://evil.example/page.html"},
        {"HTTP_ORIGIN": "http://testserver.evil.example"},
    ],
)
def test_a_cross_site_post_cannot_use_the_refresh_cookie(student, headers):
    client, _ = logged_in()
    cookie = client.cookies["iga_refresh"].value
    response = client.post("/api/auth/refresh/", **headers)
    assert response.status_code == 403
    assert "access" not in response.data and "iga_refresh" not in response.cookies
    assert not BlacklistedToken.objects.exists()  # not even rotated
    assert client.cookies["iga_refresh"].value == cookie
    assert client.post("/api/auth/refresh/").status_code == 200  # still works from the app itself
    assert AuditLog.objects.filter(action="cross_site_refused").exists()


def test_a_cross_site_post_cannot_log_someone_out(student):
    client, _ = logged_in()
    assert client.post("/api/auth/logout/", HTTP_ORIGIN="https://evil.example").status_code == 403
    assert client.post("/api/auth/refresh/").status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},  # no Origin or Referer: not a web page (an app, curl), so CSRF doesn't apply
        {"HTTP_ORIGIN": "http://testserver"},  # this site
        {"HTTP_ORIGIN": "http://localhost:5173"},  # the frontend's origin (CORS_ALLOWED_ORIGINS)
        {"HTTP_REFERER": "http://testserver/learn"},
    ],
)
def test_same_site_and_trusted_origins_can_refresh(student, headers):
    client, _ = logged_in()
    assert client.post("/api/auth/refresh/", **headers).status_code == 200


def test_wildcard_trusted_origins(student, settings):
    settings.CSRF_TRUSTED_ORIGINS = ["https://*.iga.rw"]
    client, _ = logged_in()
    assert client.post("/api/auth/refresh/", HTTP_ORIGIN="https://app.iga.rw").status_code == 200
    assert client.post("/api/auth/refresh/", HTTP_ORIGIN="http://app.iga.rw").status_code == 403
    assert client.post("/api/auth/refresh/", HTTP_ORIGIN="https://iga.rw.evil.example").status_code == 403


def test_local_development_trusts_any_loopback_port(student, settings):
    """Vite's dev proxy sends the backend's own host, so the browser's origin has another port."""
    client, _ = logged_in()
    assert client.post("/api/auth/refresh/", HTTP_ORIGIN="http://127.0.0.1:5211").status_code == 403
    settings.DEBUG = True
    assert client.post("/api/auth/refresh/", HTTP_ORIGIN="http://127.0.0.1:5211").status_code == 200
    assert client.post("/api/auth/refresh/", HTTP_ORIGIN="http://localhost:3000").status_code == 200
    assert client.post("/api/auth/refresh/", HTTP_ORIGIN="https://evil.example").status_code == 403

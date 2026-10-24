"""S27: cross-origin access. nginx serves the app and the API from one origin, so other sites get no CORS
grant unless CORS_ALLOWED_ORIGINS names them; never a wildcard; origins come only from the environment."""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from rest_framework.test import APIClient

BACKEND = Path(__file__).resolve().parent.parent
FOREIGN = "https://evil.example"


def preflight(origin, path="/api/auth/login/"):
    return APIClient().options(path, HTTP_ORIGIN=origin, HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST")


def production_settings(**env):
    base = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SECRET_KEY": "x" * 50,
        "FIELD_ENCRYPTION_KEYS": base64.urlsafe_b64encode(os.urandom(32)).decode(),
    }
    code = (
        "import json; from config import settings as s; print(json.dumps([s.CORS_ALLOWED_ORIGINS, "
        "s.CSRF_TRUSTED_ORIGINS, s.CORS_ALLOW_ALL_ORIGINS, s.CORS_ALLOWED_ORIGIN_REGEXES, s.CORS_URLS_REGEX]))"
    )
    return subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env={**base, **env}, capture_output=True, text=True)


def test_production_grants_no_cross_origin_access_by_default():
    result = production_settings()
    assert result.returncode == 0, result.stderr
    # Before: the Vite dev server's origins (http://localhost:5173, http://127.0.0.1:5173) were trusted
    # with credentials in production too.
    assert json.loads(result.stdout) == [[], [], False, [], "^/api/"]
    # Development keeps the Vite dev server's origins.
    dev = production_settings(DJANGO_DEBUG="true")
    assert json.loads(dev.stdout)[0] == ["http://localhost:5173", "http://127.0.0.1:5173"]


@pytest.mark.parametrize(
    "name, value",
    [
        ("CORS_ALLOWED_ORIGINS", "*"),
        ("CORS_ALLOWED_ORIGINS", "https://*.iga.rw"),
        ("CORS_ALLOWED_ORIGINS", "https://iga.example.rw/"),
        ("CORS_ALLOWED_ORIGINS", "iga.example.rw"),
        ("CORS_ALLOWED_ORIGINS", "null"),
        ("CORS_ALLOWED_ORIGINS", "https://iga.example.rw,*"),
        ("CSRF_TRUSTED_ORIGINS", "*"),
        ("CSRF_TRUSTED_ORIGINS", "https://*"),
        ("CSRF_TRUSTED_ORIGINS", "https://iga.example.rw/admin"),
    ],
)
def test_wildcards_and_non_origins_stop_the_start(name, value):
    result = production_settings(**{name: value})
    assert result.returncode != 0 and f"{name}: " in result.stderr


def test_listed_origins_are_accepted():
    result = production_settings(
        CORS_ALLOWED_ORIGINS="https://app.iga.example.rw", CSRF_TRUSTED_ORIGINS="https://iga.example.rw,https://*.iga.example.rw"
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)[:2] == [
        ["https://app.iga.example.rw"],
        ["https://iga.example.rw", "https://*.iga.example.rw"],
    ]


def test_a_foreign_origin_gets_no_cors_grant(db, settings):
    settings.CORS_ALLOWED_ORIGINS = []
    for origin in [FOREIGN, "http://localhost:5173", "null"]:
        response = preflight(origin)
        assert "Access-Control-Allow-Origin" not in response, origin
        assert "Access-Control-Allow-Credentials" not in response, origin
        simple = APIClient().get("/api/meta/", HTTP_ORIGIN=origin)
        assert simple.status_code == 200 and "Access-Control-Allow-Origin" not in simple


def test_only_a_listed_origin_gets_a_grant(db, settings):
    settings.CORS_ALLOWED_ORIGINS = ["https://app.iga.example.rw"]
    granted = preflight("https://app.iga.example.rw")
    assert granted["Access-Control-Allow-Origin"] == "https://app.iga.example.rw"
    assert granted["Access-Control-Allow-Credentials"] == "true"
    for origin in [FOREIGN, "https://app.iga.example.rw.evil.example", "http://app.iga.example.rw"]:
        assert "Access-Control-Allow-Origin" not in preflight(origin), origin


def test_cors_never_applies_outside_the_api(db, settings):
    settings.CORS_ALLOWED_ORIGINS = ["https://app.iga.example.rw"]
    response = APIClient().get("/django-admin/", HTTP_ORIGIN="https://app.iga.example.rw")
    assert "Access-Control-Allow-Origin" not in response

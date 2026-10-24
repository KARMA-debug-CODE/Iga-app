"""S34: HTTPS in production. Redirects, HSTS (preload when the owner opts in), secure cookies, and
X-Forwarded-Proto believed only from a trusted proxy; `manage.py check --deploy` is clean with the
production environment. The nginx side (redirect, HSTS, TLS) is in frontend/tests/nginx/test_nginx.py."""

import base64
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from rest_framework.test import APIClient

from apps.core import platform_checks

BACKEND = Path(__file__).resolve().parent.parent


def production_env(**env):
    return {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
        "FIELD_ENCRYPTION_KEYS": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "DJANGO_ALLOWED_HOSTS": "iga.example.rw",
        "TRUSTED_PROXY_COUNT": "1",
        **env,
    }


def production_settings(*names, **env):
    code = (
        f"import json; from config import settings as s; print(json.dumps({{k: getattr(s, k, None) for k in {list(names)!r}}}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND, env=production_env(**env), capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def check_deploy(**env):
    return subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=BACKEND,
        env=production_env(**env),
        capture_output=True,
        text=True,
    )


def test_check_deploy_is_clean_with_the_production_environment():
    result = check_deploy()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "System check identified no issues (1 silenced)" in result.stdout
    # The one silenced check is the reminder about HSTS preload, which the owner opts into.
    with_preload = check_deploy(SECURE_HSTS_PRELOAD="true")
    assert with_preload.returncode == 0, with_preload.stdout + with_preload.stderr
    assert "System check identified no issues (0 silenced)" in with_preload.stdout


def test_production_forces_https():
    values = production_settings(
        "SECURE_SSL_REDIRECT", "SECURE_HSTS_SECONDS", "SECURE_HSTS_INCLUDE_SUBDOMAINS", "SECURE_HSTS_PRELOAD",
        "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "REFRESH_COOKIE_SECURE", "SECURE_PROXY_SSL_HEADER",
    )  # fmt: skip
    assert values == {
        "SECURE_SSL_REDIRECT": True,
        "SECURE_HSTS_SECONDS": 31536000,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
        "SECURE_HSTS_PRELOAD": False,
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "REFRESH_COOKIE_SECURE": True,
        "SECURE_PROXY_SSL_HEADER": ["HTTP_X_FORWARDED_PROTO", "https"],
    }
    assert production_settings("SECURE_HSTS_PRELOAD", SECURE_HSTS_PRELOAD="true") == {"SECURE_HSTS_PRELOAD": True}


def test_x_forwarded_proto_is_believed_only_behind_a_trusted_proxy():
    # No proxy in front: anyone could send the header, so it means nothing.
    assert production_settings("SECURE_PROXY_SSL_HEADER", TRUSTED_PROXY_COUNT="0") == {"SECURE_PROXY_SSL_HEADER": None}


@pytest.mark.django_db
def test_plain_http_is_redirected_and_https_gets_hsts(settings):
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_HSTS_SECONDS = 31536000
    settings.SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    plain = APIClient().get("/api/meta/", HTTP_X_FORWARDED_PROTO="http")
    assert plain.status_code == 301 and plain["Location"] == "https://testserver/api/meta/"
    secure = APIClient().get("/api/meta/", HTTP_X_FORWARDED_PROTO="https")
    assert secure.status_code == 200
    assert secure["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    # Without a trusted proxy, a client claiming HTTPS over plain HTTP is still redirected.
    settings.SECURE_PROXY_SSL_HEADER = None
    spoofed = APIClient().get("/api/meta/", HTTP_X_FORWARDED_PROTO="https")
    assert spoofed.status_code == 301


def test_a_real_deployment_without_a_trusted_proxy_is_warned(settings):
    settings.HTTPS = True
    settings.TRUSTED_PROXY_COUNT = 0
    assert [w.id for w in platform_checks.proxy_scheme_check(None)] == ["iga.W011"]
    settings.TRUSTED_PROXY_COUNT = 1
    assert platform_checks.proxy_scheme_check(None) == []


def test_a_real_deployment_trusts_no_plain_http_origin(settings):
    settings.HTTPS = True
    settings.CORS_ALLOWED_ORIGINS = ["http://app.iga.example.rw"]
    settings.CSRF_TRUSTED_ORIGINS = ["https://iga.example.rw", "http://localhost:8080"]
    assert [e.id for e in platform_checks.trusted_origins_check(None)] == ["iga.E012"]
    settings.CORS_ALLOWED_ORIGINS = ["https://app.iga.example.rw"]
    assert platform_checks.trusted_origins_check(None) == []
    # A local trial over http://localhost (HTTPS=false) is not a real deployment.
    settings.HTTPS = False
    settings.CORS_ALLOWED_ORIGINS = ["http://app.iga.example.rw"]
    assert platform_checks.trusted_origins_check(None) == []

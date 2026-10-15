"""The Django admin, demo accounts, default secrets and development-only routes in production."""

import importlib
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, override_settings
from django.urls import clear_url_caches

from apps.accounts.models import User
from apps.core import checks
from apps.core.admin_login import OTPAdminAuthenticationForm, admin_path_problem, admin_url_prefix
from apps.core.demo import DEMO_PASSWORD
from apps.core.models import AuditLog
from apps.core.security_log import fingerprint

from .conftest import make_user

pytestmark = pytest.mark.django_db

BACKEND = Path(__file__).resolve().parent.parent
SECRET_PATH = "k3J9-xQ2_vL8mN4pR7tW"
PASSWORD = "Str0ng-pass-123"


@pytest.fixture
def reload_urls():
    """Rebuild the URL configuration after changing settings, and put it back afterwards."""
    import config.urls

    def _reload():
        importlib.reload(config.urls)
        clear_url_caches()

    yield _reload
    _reload()


def test_admin_path_rules():
    assert admin_path_problem("", debug=True) == ""
    assert admin_path_problem("", debug=False) == "missing"
    assert admin_path_problem("admin", debug=False) == "guessable"
    assert admin_path_problem("django-admin", debug=False) == "guessable"
    assert admin_path_problem("short-secret", debug=False) == "guessable"
    assert admin_path_problem("../" + SECRET_PATH, debug=False) == "characters"
    assert admin_path_problem(SECRET_PATH, debug=False) == ""


def test_admin_is_off_by_default_in_production(client_for):
    assert admin_url_prefix() is None
    for url in ("/django-admin/", "/django-admin/login/", "/admin/", "/admin/login/"):
        assert client_for().get(url).status_code == 404, url


def test_admin_stays_off_without_a_secret_path(settings, reload_urls, client_for):
    settings.ADMIN_ENABLED = True
    settings.ADMIN_PATH = ""
    reload_urls()
    assert client_for().get("/django-admin/login/").status_code == 404
    assert [w.id for w in checks.admin_site_check(None)] == ["iga.W001"]
    settings.ADMIN_PATH = "admin"
    assert [w.id for w in checks.admin_site_check(None)] == ["iga.W001"]


def test_admin_lives_only_at_its_secret_path(settings, reload_urls, client_for):
    settings.ADMIN_ENABLED = True
    settings.ADMIN_PATH = SECRET_PATH
    # The login page links the admin's CSS; tests have no collectstatic manifest.
    settings.STORAGES = {**settings.STORAGES, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    reload_urls()
    assert client_for().get(f"/django-admin/{SECRET_PATH}/login/").status_code == 200
    assert client_for().get("/django-admin/login/").status_code == 404
    assert checks.admin_site_check(None) == []
    admin = make_user("platform", role=User.Role.ADMIN)
    stats = client_for(admin).get("/api/admin/stats/").data
    assert stats["django_admin_url"] == f"/django-admin/{SECRET_PATH}/"


def test_admin_link_is_not_given_when_the_admin_is_off(client_for):
    admin = make_user("platform", role=User.Role.ADMIN)
    assert client_for(admin).get("/api/admin/stats/").data["django_admin_url"] is None


def test_two_factor_for_staff_cannot_be_switched_off_in_production():
    env = {
        **os.environ,
        "DJANGO_DEBUG": "false",
        "DJANGO_ADMIN_REQUIRE_2FA": "false",
        "DJANGO_SECRET_KEY": "x" * 50,
        "HTTPS": "false",
    }
    code = "import django; from django.conf import settings; django.setup(); print(settings.ADMIN_REQUIRE_2FA)"
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND,
        env={**env, "DJANGO_SETTINGS_MODULE": "config.settings"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "True"


def _admin_form(data, ip="10.0.0.1"):
    request = RequestFactory().post("/django-admin/login/", REMOTE_ADDR=ip)
    return OTPAdminAuthenticationForm(request, data=data)


@override_settings(ADMIN_REQUIRE_2FA=False)
def test_admin_logins_are_audited():
    staff = make_user("boss", role=User.Role.ADMIN, is_staff=True)
    assert not _admin_form({"username": "boss", "password": "wrong"}).is_valid()
    failed = AuditLog.objects.get(action="admin_login_failed")
    assert failed.target_id == str(staff.pk) and failed.ip_address == "10.0.0.1"
    assert not _admin_form({"username": "nobody", "password": "wrong"}).is_valid()
    unknown = AuditLog.objects.filter(action="admin_login_failed", target_id="").get()
    # Text typed as an unknown name is kept only as a fingerprint (it is sometimes a password).
    assert unknown.details["identifier"] == fingerprint("nobody") and "nobody" not in str(unknown.details)
    assert _admin_form({"username": "boss", "password": PASSWORD}).is_valid()
    assert AuditLog.objects.filter(action="admin_login", target_id=str(staff.pk)).exists()


@override_settings(ADMIN_REQUIRE_2FA=True)
def test_admin_login_without_2fa_is_refused_and_audited():
    make_user("boss", role=User.Role.ADMIN, is_staff=True)
    assert not _admin_form({"username": "boss", "password": PASSWORD}).is_valid()
    assert AuditLog.objects.filter(action="admin_login_failed", details__reason="otp_required").exists()


@override_settings(ADMIN_REQUIRE_2FA=False, ADMIN_LOGIN_ATTEMPTS_PER_MINUTE=100, ADMIN_LOGIN_IP_ATTEMPTS_PER_MINUTE=5)
def test_admin_login_attempts_are_limited_per_address():
    make_user("boss", role=User.Role.ADMIN, is_staff=True)
    for n in range(5):
        assert not _admin_form({"username": f"guess{n}", "password": "wrong"}).is_valid()
    form = _admin_form({"username": "boss", "password": PASSWORD})
    assert not form.is_valid() and "Too many attempts" in str(form.errors)
    assert _admin_form({"username": "boss", "password": PASSWORD}, ip="10.0.0.2").is_valid()  # another address


def test_seed_demo_refuses_to_run_with_debug_off():
    with pytest.raises(CommandError, match="DEBUG off"):
        call_command("seed_demo", stdout=io.StringIO())
    assert not User.objects.filter(username="aline").exists()
    with pytest.raises(CommandError):  # the old escape hatch is gone
        call_command("seed_demo", "--force", stdout=io.StringIO())


def test_demo_accounts_block_a_real_deployment_until_removed(settings, client_for):
    settings.HTTPS = True
    demo = User.objects.create_user("admin", email="admin@demo.iga.rw", password=DEMO_PASSWORD, role="admin")
    errors = checks.demo_accounts_check(None, databases=["default"])
    assert [e.id for e in errors] == ["iga.E003"] and "admin" in errors[0].msg
    settings.HTTPS = False  # a local trial over http://localhost may keep them
    assert checks.demo_accounts_check(None, databases=["default"]) == []
    settings.HTTPS = True
    call_command("remove_demo_accounts", stdout=io.StringIO())
    demo.refresh_from_db()
    assert not demo.is_active and not demo.check_password(DEMO_PASSWORD)
    assert checks.demo_accounts_check(None, databases=["default"]) == []
    login = client_for().post("/api/auth/login/", {"identifier": "admin", "password": DEMO_PASSWORD}, format="json")
    assert login.status_code == 401


def test_a_real_admin_named_admin_is_not_a_demo_account(settings):
    settings.HTTPS = True
    User.objects.create_user("admin", email="ops@iga.rw", password="A-real-long-passphrase-42", role="admin")
    assert checks.demo_accounts_check(None, databases=["default"]) == []


def test_default_secrets_block_a_real_deployment(settings):
    def flagged():
        problems = checks.default_credentials_check(None)
        assert {problem.id for problem in problems} <= {"iga.E002"}
        return sorted(problem.msg.split(" ")[0] for problem in problems)

    # The suite's own database: CI's throwaway PostgreSQL password ("iga") is a well-known value too.
    database = settings.DATABASES["default"]
    known_db_password = database["ENGINE"].endswith("postgresql") and database["PASSWORD"] in checks.KNOWN_LOCAL_SECRETS
    db = ["POSTGRES_PASSWORD"] if known_db_password else []

    settings.HTTPS = True
    settings.SANTA_URL = "http://santa:8080"
    settings.SANTA_API_KEY = "iga-local-santa"
    settings.CODE_RUNNER_URL = "http://coderunner:2000"
    settings.CODE_RUNNER_TOKEN = "iga-local-code-runner"
    assert flagged() == sorted(["SANTA_API_KEY", "CODE_RUNNER_TOKEN", *db])
    settings.SANTA_API_KEY = "Zr8wq0C9hJ1eLmW4tYb7sKdNfVxP2aGu"
    settings.CODE_RUNNER_TOKEN = "Gd5kP0sQ3mT8wZ1xB6nV9cR2yL4hJ7fE"
    assert flagged() == db
    settings.SANTA_API_KEY = "iga-local-santa"
    settings.HTTPS = False  # the local docker compose trial
    assert checks.default_credentials_check(None) == []


def test_development_tools_are_not_served_in_production(client_for, student):
    # No browsable HTML API, and no list of every endpoint at /api/.
    response = client_for(student).get("/api/dashboard/", HTTP_ACCEPT="text/html")
    assert response.status_code == 406 or response["Content-Type"].startswith("application/json")
    assert client_for(student).get("/api/").status_code == 404


@override_settings(ADMIN_REQUIRE_2FA=False, ADMIN_PATH=SECRET_PATH)
def test_the_secret_admin_path_stays_out_of_the_security_log(caplog):
    make_user("boss", role=User.Role.ADMIN, is_staff=True)
    caplog.set_level("INFO", logger="iga.security")
    request = RequestFactory().post(f"/django-admin/{SECRET_PATH}/login/", REMOTE_ADDR="10.0.0.1")
    assert not OTPAdminAuthenticationForm(request, data={"username": "boss", "password": "wrong"}).is_valid()
    lines = [record.getMessage() for record in caplog.records if record.name == "iga.security"]
    assert lines and all(SECRET_PATH not in line for line in lines)
    assert any("/django-admin/<DJANGO_ADMIN_PATH>/login/" in line for line in lines)

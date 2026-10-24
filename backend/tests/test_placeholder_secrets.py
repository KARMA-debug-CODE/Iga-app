"""A deployment with DEBUG off refuses to start with a secret everyone can read: the local defaults in
docker-compose.yml, the example values in the docs, the values the build and the tests use, or one that
is too short to be random (apps/core/checks.py, iga.E002). Only a local trial (plain HTTP, reachable only
as localhost) may keep the local defaults. `migrate` runs the checks, so the backend never serves."""

import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from apps.core import checks

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent

pytestmark = pytest.mark.django_db


def flagged():
    problems = checks.default_credentials_check(None)
    assert {problem.id for problem in problems} <= {"iga.E002"}
    return sorted(problem.msg.split(" ")[0] for problem in problems)


@pytest.fixture
def server(settings):
    """A real server over plain HTTP (a school's own server without a certificate), every secret random."""
    settings.DEBUG = False
    settings.HTTPS = False
    settings.ALLOWED_HOSTS = ["iga.school.rw"]
    settings.SECRET_KEY = secrets.token_urlsafe(50)
    settings.SANTA_URL = "http://santa:8080"
    settings.SANTA_API_KEY = secrets.token_urlsafe(32)
    settings.CODE_RUNNER_URL = "http://coderunner:2000"
    settings.CODE_RUNNER_TOKEN = secrets.token_urlsafe(32)
    settings.BILLING_PROVIDER = "flutterwave"
    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK-" + secrets.token_hex(16) + "-X"
    settings.FLUTTERWAVE_WEBHOOK_HASH = secrets.token_urlsafe(32)
    settings.LEDGER_HMAC_KEY = secrets.token_urlsafe(32)
    database = settings.DATABASES["default"]
    # The suite's own database: CI's throwaway PostgreSQL password ("iga") is a well-known value too.
    known = database["ENGINE"].endswith("postgresql") and database["PASSWORD"] in checks.KNOWN_LOCAL_SECRETS
    return ["POSTGRES_PASSWORD"] if known else []


def test_random_secrets_pass(server):
    assert flagged() == server


def test_the_compose_defaults_stop_a_server_even_without_https(server, settings):
    # Before: only "DEBUG off and HTTPS on" counted, so a server on plain HTTP kept the defaults every copy
    # of docker-compose.yml knows.
    settings.SANTA_API_KEY = "iga-local-santa"
    settings.CODE_RUNNER_TOKEN = "iga-local-code-runner"
    assert flagged() == sorted(["SANTA_API_KEY", "CODE_RUNNER_TOKEN", *server])


def test_only_a_local_trial_keeps_the_local_defaults(server, settings):
    settings.SANTA_API_KEY = "iga-local-santa"
    settings.CODE_RUNNER_TOKEN = "iga-local-code-runner"
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]  # docker compose up on one's own machine
    assert flagged() == []
    settings.ALLOWED_HOSTS = ["localhost", "*"]  # reachable under any name: not a local trial
    assert "CODE_RUNNER_TOKEN" in flagged()
    settings.ALLOWED_HOSTS = ["localhost"]
    settings.HTTPS = True  # HTTPS is for a real server
    assert "CODE_RUNNER_TOKEN" in flagged()
    settings.DEBUG = True  # development
    assert flagged() == []


def test_example_values_from_the_docs_are_refused(server, settings):
    settings.SANTA_API_KEY = "a-shared-secret"
    settings.CODE_RUNNER_TOKEN = "change-me-to-a-long-random-string"
    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK-..."
    settings.FLUTTERWAVE_WEBHOOK_HASH = "a-long-random-string"
    settings.LEDGER_HMAC_KEY = "a-long-random-string"
    assert flagged() == sorted(
        ["SANTA_API_KEY", "CODE_RUNNER_TOKEN", "FLUTTERWAVE_SECRET_KEY", "FLUTTERWAVE_WEBHOOK_HASH", "LEDGER_HMAC_KEY", *server]
    )


def test_short_shared_secrets_are_refused(server, settings):
    settings.SANTA_API_KEY = "santa123"
    settings.CODE_RUNNER_TOKEN = "x" * 40  # long, but one character
    assert flagged() == sorted(["SANTA_API_KEY", "CODE_RUNNER_TOKEN", *server])


def test_secret_keys_written_in_the_repository_are_refused(server, settings):
    for public in (
        "build-time-placeholder-only-used-for-collectstatic",  # the image build's old one
        "test-only-secret-key-that-is-long-enough-1234567890",  # the test suite's
        "local-only-change-me-0f8e7c2b9a-and-some-more-text",
    ):
        settings.SECRET_KEY = public
        assert flagged() == sorted(["DJANGO_SECRET_KEY", *server]), public


def test_unused_services_need_no_secret(server, settings):
    settings.SANTA_URL = ""
    settings.SANTA_API_KEY = ""
    settings.CODE_RUNNER_URL = ""
    settings.CODE_RUNNER_TOKEN = "iga-local-code-runner"
    settings.BILLING_PROVIDER = ""
    settings.FLUTTERWAVE_SECRET_KEY = "FLWSECK-..."
    settings.LEDGER_HMAC_KEY = ""  # optional
    assert flagged() == server


def test_every_secret_default_in_docker_compose_is_refused():
    """A new ${X:-default} for a secret in docker-compose.yml must be known here, or this fails."""
    compose = (REPO / "docker-compose.yml").read_text()
    defaults = re.findall(r"\$\{([A-Z_]*(?:KEYS?|TOKEN|PASSWORD|SECRET|HASH)):-([^}]*)\}", compose)
    assert defaults, "the pattern no longer finds the compose file's secrets"
    unknown = {(name, value) for name, value in defaults if value and value not in checks.KNOWN_LOCAL_SECRETS}
    assert not unknown


def test_the_image_build_uses_no_fixed_secret_key():
    dockerfile = (BACKEND / "Dockerfile").read_text()
    assert not re.search(r"DJANGO_SECRET_KEY=(?!\"?\$\()", dockerfile)


def _start(**env):
    """`manage.py check` as the container's migrate runs it, in production: DEBUG off."""
    base = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
        "FIELD_ENCRYPTION_KEYS": Fernet.generate_key().decode(),
        "HTTPS": "false",
        "DJANGO_ALLOWED_HOSTS": "iga.school.rw",
        "DATABASE_URL": "sqlite:///:memory:",
    }
    return subprocess.run(
        [sys.executable, "manage.py", "check"], cwd=BACKEND, env={**base, **env}, capture_output=True, text=True
    )


def test_production_does_not_start_with_the_compose_defaults():
    refused = _start(CODE_RUNNER_URL="http://coderunner:2000", CODE_RUNNER_TOKEN="iga-local-code-runner")
    assert refused.returncode != 0 and "iga.E002" in refused.stderr and "CODE_RUNNER_TOKEN" in refused.stderr
    started = _start(CODE_RUNNER_URL="http://coderunner:2000", CODE_RUNNER_TOKEN=secrets.token_urlsafe(32))
    assert started.returncode == 0, started.stderr


def test_production_does_not_start_with_the_build_time_secret_key():
    refused = _start(DJANGO_SECRET_KEY="build-time-placeholder-only-used-for-collectstatic")
    assert refused.returncode != 0 and "DJANGO_SECRET_KEY" in refused.stderr


ENV_FILES = [".env", "backend/.env", "frontend/.env", "frontend/.env.production", ".env.local", "server.key", "tls/cert.pem"]


def test_env_files_and_keys_stay_out_of_git():
    if not shutil.which("git") or not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    result = subprocess.run(["git", "check-ignore", "--no-index", *ENV_FILES], cwd=REPO, capture_output=True, text=True)
    assert sorted(result.stdout.split()) == sorted(ENV_FILES)
    examples = subprocess.run(
        ["git", "check-ignore", "--no-index", ".env.docker.example", "backend/.env.example"], cwd=REPO, capture_output=True
    )
    assert examples.returncode == 1  # the examples are kept


def test_env_files_and_keys_stay_out_of_every_image():
    for folder in ("backend", "frontend"):
        rules = (REPO / folder / ".dockerignore").read_text().split()
        assert {".env", ".env.*", "*.local", "*.pem", "*.key"} <= set(rules), folder
    # The code runner's image copies two named files and nothing else.
    copies = re.findall(r"^COPY (.*)$", (REPO / "coderunner" / "Dockerfile").read_text(), re.M)
    assert copies == ["--from=jdk /opt/java/openjdk /opt/java/openjdk", "server.py test_server.py ./"]

"""Iga's system checks: `manage.py check` runs them, and so does `migrate`, which the container runs before it
starts serving. An Error stops `migrate`, so a real deployment with one of these mistakes doesn't start.

A "real deployment" is DEBUG off with HTTPS on. A local `docker compose` trial over plain
http://localhost (HTTPS=false) may keep the demo accounts. Secrets are stricter: with DEBUG off, only a local
trial (plain HTTP, reachable only as localhost) may keep the well-known local secrets (see local_trial()).
"""

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register
from django.db import DatabaseError

# The local-trial values from docker-compose.yml and the docs, and every other value the repository has
# ever used as a secret (the build's, the tests'): public, so never acceptable for real.
KNOWN_LOCAL_SECRETS = {
    "",
    "iga",
    "iga-local-only",
    "iga-local-owner",
    "iga-local-app",
    "iga-local-santa",
    "iga-local-code-runner",
    "a-shared-secret",
    "a-long-random-string",
    "change-me",
    "change-me-to-a-long-random-string",
    "password",
    "postgres",
    "local-only-change-me-0f8e7c2b9a",
    "dev-only-insecure-key-do-not-use-in-production",
    "build-time-placeholder-only-used-for-collectstatic",
    "test-only-secret-key-that-is-long-enough-1234567890",
    "db-roles-test-secret-key-that-is-long-enough-0123456789",
}
# Words that mark an example or placeholder rather than a secret someone generated.
PLACEHOLDER_WORDS = (
    "change-me",
    "changeme",
    "replace",
    "placeholder",
    "example",
    "your-",
    "a-long-random",
    "local-only",
    "...",
    "<",
    "xxxx",
)
# Shared secrets between Iga's own services (Santa's model server, the code runner) are generated, so long.
MIN_SHARED_SECRET_LENGTH = 16
# Hosts that only reach this machine: `docker compose up` for a look at Iga, or the test client.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1", "testserver"}


def real_deployment():
    return not settings.DEBUG and settings.HTTPS


def local_trial():
    """DEBUG off over plain HTTP, answering only to local names: a trial on one's own machine. A server
    with a name or an address of its own (DJANGO_ALLOWED_HOSTS) is not, even without HTTPS."""
    return not settings.HTTPS and all(host.lower() in LOCAL_HOSTS for host in settings.ALLOWED_HOSTS)


def public_secret(value, min_length=0):
    """Is `value` a secret everyone can know: a published value, an example, too short, or not random?"""
    value = value or ""
    lowered = value.lower()
    return (
        value in KNOWN_LOCAL_SECRETS
        or lowered.startswith(("dev-only", "test-only"))
        or any(word in lowered for word in PLACEHOLDER_WORDS)
        or len(value) < min_length
        or len(set(value)) < 6
    )


@register()
def admin_site_check(app_configs, **kwargs):
    from .admin_login import admin_path_problem

    if not settings.ADMIN_ENABLED:
        return []
    problem = admin_path_problem()
    if not problem:
        return []
    return [
        Warning(
            "The Django admin is switched on but stays off: DJANGO_ADMIN_PATH is "
            + {"missing": "not set", "characters": "not made of letters, digits, - and _ only"}.get(
                problem, "too short or easy to guess"
            )
            + ".",
            hint="Set DJANGO_ADMIN_PATH to a long random value, for example the output of "
            'python -c "import secrets; print(secrets.token_urlsafe(24))". The admin is then at '
            "/django-admin/<DJANGO_ADMIN_PATH>/.",
            id="iga.W001",
        )
    ]


@register()
def default_credentials_check(app_configs, **kwargs):
    """With DEBUG off, Iga must not run with a secret every copy of the code knows (docker-compose.yml's
    local defaults, the docs' examples), with a placeholder, or with a short one. Only a local trial may."""
    if settings.DEBUG or local_trial():
        return []
    errors = []
    if public_secret(settings.SECRET_KEY, 32):
        errors.append(("DJANGO_SECRET_KEY", "signing sessions and links"))
    if settings.SANTA_URL and public_secret(settings.SANTA_API_KEY, MIN_SHARED_SECRET_LENGTH):
        errors.append(("SANTA_API_KEY", "Santa's model server"))
    if settings.CODE_RUNNER_URL and public_secret(settings.CODE_RUNNER_TOKEN, MIN_SHARED_SECRET_LENGTH):
        errors.append(("CODE_RUNNER_TOKEN", "the code runner"))
    database = settings.DATABASES["default"]
    if database.get("ENGINE", "").endswith("postgresql") and database.get("PASSWORD", "") in KNOWN_LOCAL_SECRETS - {""}:
        errors.append(("POSTGRES_PASSWORD / DATABASE_URL", "the database"))
    if settings.BILLING_PROVIDER == "flutterwave":
        # Unset values are iga.W010's business, a test key iga.E011's.
        if settings.FLUTTERWAVE_SECRET_KEY and public_secret(settings.FLUTTERWAVE_SECRET_KEY):
            errors.append(("FLUTTERWAVE_SECRET_KEY", "Flutterwave"))
        if settings.FLUTTERWAVE_WEBHOOK_HASH and public_secret(settings.FLUTTERWAVE_WEBHOOK_HASH):
            errors.append(("FLUTTERWAVE_WEBHOOK_HASH", "Flutterwave's webhooks"))
    if settings.LEDGER_HMAC_KEY and public_secret(settings.LEDGER_HMAC_KEY, MIN_SHARED_SECRET_LENGTH):
        errors.append(("LEDGER_HMAC_KEY", "the money ledger"))
    return [
        Error(
            f"{name} for {what} is a well-known, placeholder or short value.",
            hint='Set a long random value (python -c "import secrets; print(secrets.token_urlsafe(32))") '
            "in .env. Only a local trial (HTTPS=false, DJANGO_ALLOWED_HOSTS=localhost) may keep the local defaults.",
            id="iga.E002",
        )
        for name, what in errors
    ]


@register(Tags.database)
def database_role_check(app_configs, databases=None, **kwargs):
    """Django must not connect to PostgreSQL with powers it never needs (apps/core/dbroles.py)."""
    if not databases or not real_deployment():
        return []
    from django.db import connections

    from .dbroles import current_role_powers

    found = []
    for alias in databases:
        connection = connections[alias]
        if connection.vendor != "postgresql":
            continue
        try:
            name, powers = current_role_powers(connection)
        except DatabaseError:
            continue
        hint = (
            "Run Django as a role that may only read and write rows: python manage.py db_roles sets one up "
            '(docker compose does it for you). See "Database roles" in docs/ARCHITECTURE.md.'
        )
        if "superuser" in powers:
            found.append(
                Error(
                    f"Django connects to PostgreSQL as {name}, a superuser: SQL it was tricked into running could "
                    "read or change anything on the database server, and run programs on it.",
                    hint=hint,
                    id="iga.E004",
                )
            )
        elif powers:
            found.append(
                Warning(
                    f"Django connects to PostgreSQL as {name}, which has {', '.join(powers).upper()}; it needs none of these.",
                    hint=hint,
                    id="iga.W002",
                )
            )
    return found


@register(Tags.database)
def demo_accounts_check(app_configs, databases=None, **kwargs):
    """No account on a real deployment may sign in with seed_demo's public password."""
    if not databases or not real_deployment():
        return []
    from .demo import demo_accounts

    try:
        found = demo_accounts()
    except DatabaseError:  # tables not created yet (first migrate)
        return []
    if not found:
        return []
    return [
        Error(
            "These demo accounts still sign in with the public demo password: "
            + ", ".join(sorted(user.username for user in found))
            + ".",
            hint="Run: python manage.py remove_demo_accounts (it deactivates them).",
            id="iga.E003",
        )
    ]


def _served_folders():
    """Folders whose files Django (whitenoise) serves to anyone as static files."""
    folders = [settings.STATIC_ROOT, getattr(settings, "WHITENOISE_ROOT", None)]
    for entry in getattr(settings, "STATICFILES_DIRS", []):
        folders.append(entry[1] if isinstance(entry, (list, tuple)) else entry)
    return [Path(folder).resolve() for folder in folders if folder]


@register()
def media_root_check(app_configs, **kwargs):
    """Uploads must stay out of every folder served as static files, where they would be public and
    skip the access checks and safe headers of apps/core/media.py."""
    if not settings.MEDIA_ROOT:
        return [Error("MEDIA_ROOT is not set.", hint="Point MEDIA_ROOT at a folder of its own for uploads.", id="iga.E013")]
    media = Path(settings.MEDIA_ROOT).resolve()
    clashes = [
        str(folder) for folder in _served_folders() if media == folder or folder in media.parents or media in folder.parents
    ]
    if not clashes:
        return []
    return [
        Error(
            f"MEDIA_ROOT ({media}) overlaps a folder served as static files: {', '.join(clashes)}.",
            hint="Keep uploads in a folder of their own, outside STATIC_ROOT, STATICFILES_DIRS and WHITENOISE_ROOT.",
            id="iga.E013",
        )
    ]

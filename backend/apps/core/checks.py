"""Iga's system checks: `manage.py check` runs them, and so does `migrate`, which the container runs before it
starts serving. An Error stops `migrate`, so a real deployment with one of these mistakes doesn't start.

A "real deployment" is DEBUG off with HTTPS on. A local `docker compose` trial over plain
http://localhost (HTTPS=false) may keep the well-known local secrets and demo accounts.
"""

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register
from django.db import DatabaseError

# The local-trial values from docker-compose.yml and the docs: public, so never acceptable for real.
KNOWN_LOCAL_SECRETS = {
    "",
    "iga",
    "iga-local-only",
    "iga-local-santa",
    "iga-local-code-runner",
    "a-shared-secret",
    "change-me",
    "password",
    "postgres",
}


def real_deployment():
    return not settings.DEBUG and settings.HTTPS


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
    """A real deployment must not run with the secrets every copy of the code knows."""
    if not real_deployment():
        return []
    errors = []
    if settings.SANTA_URL and settings.SANTA_API_KEY in KNOWN_LOCAL_SECRETS:
        errors.append(("SANTA_API_KEY", "Santa's model server"))
    if settings.CODE_RUNNER_URL and settings.CODE_RUNNER_TOKEN in KNOWN_LOCAL_SECRETS:
        errors.append(("CODE_RUNNER_TOKEN", "the code runner"))
    database = settings.DATABASES["default"]
    if database.get("ENGINE", "").endswith("postgresql") and database.get("PASSWORD", "") in KNOWN_LOCAL_SECRETS - {""}:
        errors.append(("POSTGRES_PASSWORD / DATABASE_URL", "the database"))
    return [
        Error(
            f"{name} for {what} is a well-known default value.",
            hint='Set a long random value (python -c "import secrets; print(secrets.token_urlsafe(32))") '
            "in .env. HTTPS=false is only for a local trial on http://localhost.",
            id="iga.E002",
        )
        for name, what in errors
    ]


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

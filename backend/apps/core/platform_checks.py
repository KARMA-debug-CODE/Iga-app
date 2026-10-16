"""System checks for how Iga is deployed: HTTPS behind a proxy and the origins it trusts. Like the checks in
checks.py they run with `manage.py check` and before `migrate`, so an Error keeps a real deployment (DEBUG
off, HTTPS on) from starting."""

from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, Warning, register

from .checks import real_deployment

LOOPBACK = {"localhost", "127.0.0.1", "::1"}


@register()
def proxy_scheme_check(app_configs, **kwargs):
    """With no trusted proxy, Django ignores X-Forwarded-Proto: behind one, every request would look like HTTP."""
    if not real_deployment() or settings.TRUSTED_PROXY_COUNT > 0:
        return []
    return [
        Warning(
            "TRUSTED_PROXY_COUNT is 0, so Django believes no proxy: it ignores X-Forwarded-Proto and X-Forwarded-For. "
            "Behind nginx or a load balancer that terminates HTTPS, every request then looks like plain HTTP "
            "(redirect loops) and every client has the proxy's address (shared rate limits and lockouts).",
            hint="Behind the bundled nginx set TRUSTED_PROXY_COUNT=1 (docker compose does). Leave it at 0 only "
            "when clients connect to Django directly over HTTPS.",
            id="iga.W011",
        )
    ]


@register()
def trusted_origins_check(app_configs, **kwargs):
    """A real deployment must not let pages from a plain-HTTP site in: anyone on the network could write them."""
    if not real_deployment():
        return []
    found = []
    for name in ("CORS_ALLOWED_ORIGINS", "CSRF_TRUSTED_ORIGINS"):
        for origin in getattr(settings, name):
            parts = urlsplit(origin)
            if parts.scheme != "https" and (parts.hostname or "") not in LOOPBACK:
                found.append(
                    Error(
                        f"{name} trusts {origin}, a plain-HTTP origin: anyone between that site and its visitors could "
                        "put a page there that uses Iga with their session.",
                        hint="List only https:// origins (for the bundled nginx, CORS_ALLOWED_ORIGINS can stay empty).",
                        id="iga.E012",
                    )
                )
    return found

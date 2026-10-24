"""Maintenance mode: "back soon" for everyone except the Iga team.

While it is on (MAINTENANCE_MODE=true, or the file MAINTENANCE_FILE exists: `manage.py maintenance on`),
every API request answers 503 {"code": "maintenance"} unless a platform admin makes it, and the app shows
its "back soon" page. nginx sees the same file (docker compose shares it) and answers the app's pages with
its own "back soon" page and a 503 (frontend/nginx.conf); the `iga_team` cookie, which sign-in gives
platform admins only, and the /team page (the team's sign-in) let the team in. The cookie is only a hint for
nginx: whoever sends it still gets 503 from every API request unless they are a platform admin.

Still open while it is on: health checks, the public site information (the app reads it to say "back soon"),
sign-in, refresh and logout (which refuse everyone but platform admins themselves, apps/accounts/views.py),
payment webhooks (Flutterwave retries, but a payment should not wait), and the Django admin (staff only).
"""

from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import gettext as _
from rest_framework.response import Response

# Exact API paths that keep working during maintenance.
OPEN_PATHS = {
    "/api/health/",
    "/api/site/",
    "/api/auth/login/",
    "/api/auth/refresh/",
    "/api/auth/logout/",
}
OPEN_PREFIXES = ("/api/billing/webhooks/",)
# Seconds the browser is told to wait before trying again.
RETRY_AFTER = 300
TEAM_COOKIE = "iga_team"


def maintenance_on():
    if settings.MAINTENANCE_MODE:
        return True
    path = settings.MAINTENANCE_FILE
    try:
        return bool(path) and Path(path).exists()
    except OSError:
        return False


def set_maintenance(on):
    """Switch the file-based maintenance mode on or off (MAINTENANCE_MODE=true in the environment stays on)."""
    path = Path(settings.MAINTENANCE_FILE)
    if on:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Maintenance mode: python manage.py maintenance off\n", encoding="utf-8")
    else:
        path.unlink(missing_ok=True)


def message():
    return _("Iga is being updated. We'll be back soon.")


def payload():
    return {"detail": message(), "code": "maintenance", "retry_after": RETRY_AFTER}


def drf_response():
    """The answer a DRF view gives during maintenance (sign-in and refresh for anyone but platform admins)."""
    response = Response(payload(), status=503)
    response["Retry-After"] = str(RETRY_AFTER)
    return response


def _platform_admin(request):
    """The platform admin making this API request (Bearer access token), or None."""
    from apps.accounts.authentication import IgaJWTAuthentication

    try:
        result = IgaJWTAuthentication().authenticate(request)
    except Exception:  # an expired or forged token, a temporary password: not the team
        return None
    if result is None:
        return None
    user = result[0]
    return user if user.is_active and user.is_platform_admin else None


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if (
            path.startswith("/api/")
            and path not in OPEN_PATHS
            and not path.startswith(OPEN_PREFIXES)
            and maintenance_on()
            and _platform_admin(request) is None
        ):
            response = JsonResponse(payload(), status=503)
            response["Retry-After"] = str(RETRY_AFTER)
            response["Cache-Control"] = "no-store"
            return response
        return self.get_response(request)


def set_team_cookie(request, response, user):
    """Platform admins carry the `iga_team` cookie, so nginx lets them reach the app during maintenance; anyone
    else who has it loses it. It is a hint for nginx only, never a permission (see the module docstring)."""
    if user is not None and user.is_platform_admin:
        response.set_cookie(
            TEAM_COOKIE,
            "1",
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            httponly=True,
            secure=settings.REFRESH_COOKIE_SECURE,
            samesite="Strict",
            path="/",
        )
    elif TEAM_COOKIE in request.COOKIES:
        response.delete_cookie(TEAM_COOKIE, path="/", samesite="Strict")
    return response

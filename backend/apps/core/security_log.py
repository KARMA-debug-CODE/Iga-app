"""Security events: one structured (JSON) log line each, plus an entry in the audit log.

Every sign-in, lockout, password and 2FA change, refresh-token reuse, refused request (403),
throttled request (429) and cross-site request refusal goes through `event()`, so it reaches the
"iga.security" logger (one JSON object per line, for a log collector) and the audit log that
platform admins read in Admin -> Audit. Nothing secret is written: passwords, codes and tokens are
dropped, and text someone typed as a username is only kept as a short fingerprint (people
sometimes type their password into the username box).
"""

import hashlib
import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.views.csrf import csrf_failure as django_csrf_failure
from rest_framework.exceptions import PermissionDenied, Throttled
from rest_framework.views import exception_handler as drf_exception_handler

from . import audit

log = logging.getLogger("iga.security")

# Audit-log actions that are security events (Admin -> Audit can show only these).
SECURITY_ACTIONS = {
    "login",
    "login_failed",
    "login_locked",
    "account_locked",
    "register",
    "change_password",
    "password_reset_requested",
    "password_reset",
    "password_reset_failed",
    "enable_2fa",
    "disable_2fa",
    "2fa_failed",
    "reauth_failed",
    "step_up",
    "step_up_failed",
    "email_in_use",
    "email_changed",
    "logout_everywhere",
    "refresh_token_reuse",
    "reset_student_password",
    "permission_denied",
    "throttled",
    "cross_site_refused",
    "admin_login",
    "admin_login_failed",
}

# Never logged, whatever a caller passes in `details`.
SECRET_FIELDS = {
    "password",
    "new_password",
    "current_password",
    "otp",
    "code",
    "token",
    "secret",
    "access",
    "refresh",
    "totp_secret",
}


def fingerprint(text):
    """A short stand-in for typed text that must not be stored as typed (an unknown username or email)."""
    return hashlib.sha256(str(text).strip().casefold().encode()).hexdigest()[:16]


def _clean(details):
    return {key: value for key, value in details.items() if key.lower() not in SECRET_FIELDS}


def event(request, action, user=None, *, level=logging.INFO, audit_every=None, **details):
    """Log a security event and record it in the audit log.

    `user` is the account concerned (None when no account is known). With `audit_every` (seconds),
    the audit log keeps at most one entry per event, account (or IP) and path in that time, so a
    flood of refused requests can't fill the database; every occurrence is still logged.
    """
    details = _clean(details)
    ip = audit.client_ip(request)
    path = _loggable_path(request)
    line = {
        "ts": timezone.now().isoformat(),
        "event": action,
        "user_id": user.pk if user is not None else None,
        "ip": ip,
        "method": getattr(request, "method", None),
        "path": path,
        **details,
    }
    log.log(level, json.dumps(line, default=str, sort_keys=True))
    if audit_every:
        who = f"u{user.pk}" if user is not None else f"ip{ip}"
        key = "security-audit:" + hashlib.sha256(f"{action}|{who}|{path}".encode()).hexdigest()
        if not cache.add(key, 1, audit_every):
            return None
    if user is not None and "username" not in details:
        details["username"] = user.username
    return audit.record(request, action, user, **details)


def _loggable_path(request):
    """The request path, or its URL pattern when the path carries a secret (a signed download link, or the
    Django admin's secret address)."""
    path = getattr(request, "path", None)
    match = getattr(request, "resolver_match", None)
    if match is not None and any("token" in key or "secret" in key for key in match.kwargs):
        return "/" + match.route
    admin_path = settings.ADMIN_PATH
    if path and admin_path and path.startswith(f"/django-admin/{admin_path}/"):
        return "/django-admin/<DJANGO_ADMIN_PATH>/" + path[len(f"/django-admin/{admin_path}/") :]
    return path


def _request_user(request):
    user = getattr(request, "user", None)
    return user if user is not None and user.is_authenticated else None


def exception_handler(exc, context):
    """DRF's exception handler, plus a security event for refused (403) and throttled (429) requests."""
    response = drf_exception_handler(exc, context)
    request = context.get("request")
    if request is None or response is None:
        return response
    if isinstance(exc, Throttled):
        event(request, "throttled", _request_user(request), level=logging.WARNING, audit_every=600, wait=exc.wait)
    elif isinstance(exc, PermissionDenied) and getattr(exc, "default_code", "") != "password_change_required":
        event(request, "permission_denied", _request_user(request), level=logging.WARNING, audit_every=600)
    return response


def csrf_failure(request, reason=""):
    """Django's CSRF failure page (Django admin forms), logged as a security event."""
    event(request, "cross_site_refused", _request_user(request), level=logging.WARNING, audit_every=600, reason=reason)
    return django_csrf_failure(request, reason=reason)

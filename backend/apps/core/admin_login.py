"""The Django admin: off unless switched on, at a secret address, and with the app's own login protections.

* Off unless DJANGO_ADMIN_ENABLED; in production (DEBUG off) it also needs DJANGO_ADMIN_PATH, a long
  random secret, and lives at /django-admin/<DJANGO_ADMIN_PATH>/ (nginx already forwards /django-admin/).
  Without a valid path it stays off (and `manage.py check` says why).
* Staff need two-factor authentication (always in production).
* Login attempts are limited per account and per address, share the app's progressive sign-in lockout,
  and every attempt is a security event (logged, and audit-logged against the account when it exists).
"""

import hashlib
import logging
import re

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.cache import cache
from django.utils.translation import gettext as _

from apps.accounts import lockout
from apps.accounts.security import find_account, verify_totp

from . import security_log
from .audit import client_ip

ADMIN_PATH_MIN_LENGTH = 16
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
# Paths a scanner tries first: never acceptable as the secret part.
GUESSABLE = {"admin", "django-admin", "administrator", "backend", "manage", "staff", "dashboard", "login"}


def admin_path_problem(path=None, debug=None):
    """Why the configured admin path can't be used ("" when it can)."""
    path = settings.ADMIN_PATH if path is None else path
    debug = settings.DEBUG if debug is None else debug
    if not path:
        return "" if debug else "missing"
    if not _PATH_PATTERN.match(path):
        return "characters"
    if not debug and (len(path) < ADMIN_PATH_MIN_LENGTH or path.lower() in GUESSABLE):
        return "guessable"
    return ""


def admin_url_prefix():
    """Where the admin is mounted ("django-admin/<secret>/"), or None when it must stay off."""
    if not settings.ADMIN_ENABLED or admin_path_problem():
        return None
    return f"django-admin/{settings.ADMIN_PATH}/" if settings.ADMIN_PATH else "django-admin/"


def _over_limit(key, limit):
    attempts = cache.get(key, 0)
    if attempts >= limit:
        return True
    cache.set(key, attempts + 1, 60)
    return False


class OTPAdminAuthenticationForm(AdminAuthenticationForm):
    otp = forms.CharField(
        label="Authenticator code",
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )

    def clean(self):
        username = (self.data.get("username") or "").strip().lower()
        ip = client_ip(self.request)
        account_key = "admin-login:" + hashlib.sha256(username.encode()).hexdigest()
        ip_key = "admin-login-ip:" + hashlib.sha256((ip or "unknown").encode()).hexdigest()
        if _over_limit(account_key, settings.ADMIN_LOGIN_ATTEMPTS_PER_MINUTE) or _over_limit(
            ip_key, settings.ADMIN_LOGIN_IP_ATTEMPTS_PER_MINUTE
        ):
            self._log("admin_login_failed", username, reason="throttled", audit_every=600)
            raise forms.ValidationError(_("Too many attempts. Wait a minute and try again."), code="throttled")

        # The same progressive lockout as the app's sign-in (shared counters).
        keys = lockout.sign_in_keys(username, ip)
        if lockout.check(keys):
            self._log("admin_login_failed", username, reason="locked", audit_every=600)
            raise forms.ValidationError(_("Too many attempts. Wait a minute and try again."), code="throttled")

        try:
            cleaned = super().clean()  # checks the password and that the user is staff
            user = self.get_user()
            if user is not None:
                if user.totp_enabled:
                    if not verify_totp(user, self.cleaned_data.get("otp")):
                        raise forms.ValidationError(_("Enter the current 6-digit code from your authenticator app."), code="otp")
                elif settings.ADMIN_REQUIRE_2FA:
                    raise forms.ValidationError(
                        _("Turn on two-factor authentication in your Iga profile before using the admin site."),
                        code="otp_required",
                    )
        except forms.ValidationError as error:
            codes = {getattr(e, "code", None) for e in error.error_list}
            # A wrong password or code counts towards the lockout; a missing 2FA setup doesn't.
            if codes & {"invalid_login", "otp"}:
                lockout.fail(keys)
            self._log("admin_login_failed", username, reason=",".join(sorted(c for c in codes if c)) or "invalid")
            raise
        lockout.succeed(keys)
        self._log("admin_login", username, user=self.get_user())
        return cleaned

    def _log(self, action, username, user=None, audit_every=None, **details):
        """A security event, against the account when one matches the typed name. Text typed as an unknown
        name is kept only as a fingerprint (people sometimes type their password there)."""
        if user is None and username:
            user = find_account(username)
        if user is None:
            details["identifier"] = security_log.fingerprint(username)
        level = logging.INFO if action == "admin_login" else logging.WARNING
        security_log.event(self.request, action, user, level=level, audit_every=audit_every, **details)


def install():
    admin.site.login_form = OTPAdminAuthenticationForm
    admin.site.login_template = "admin/iga_login.html"

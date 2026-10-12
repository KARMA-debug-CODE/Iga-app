"""The Django admin: off unless switched on, at a secret address, and with the app's own login protections.

* Off unless DJANGO_ADMIN_ENABLED; in production (DEBUG off) it also needs DJANGO_ADMIN_PATH, a long
  random secret, and lives at /django-admin/<DJANGO_ADMIN_PATH>/ (nginx already forwards /django-admin/).
  Without a valid path it stays off (and `manage.py check` says why).
* Staff need two-factor authentication (always in production).
* Login attempts are limited per account and per address, and every attempt is audit-logged.
"""

import hashlib
import re

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.translation import gettext as _

from apps.accounts.security import verify_totp
from apps.core import audit

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
        account_key = "admin-login:" + hashlib.sha256(username.encode()).hexdigest()
        ip = audit.client_ip(self.request) or "unknown"
        ip_key = "admin-login-ip:" + hashlib.sha256(ip.encode()).hexdigest()
        if _over_limit(account_key, settings.ADMIN_LOGIN_ATTEMPTS_PER_MINUTE) or _over_limit(
            ip_key, settings.ADMIN_LOGIN_IP_ATTEMPTS_PER_MINUTE
        ):
            self._record_failure(username, "throttled")
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
            self._record_failure(username, getattr(error, "code", None) or "invalid")
            raise
        if user is not None:
            audit.record(self.request, "admin_login", user)
        return cleaned

    def _record_failure(self, username, reason):
        """Every refused admin login reaches the audit log (against the account when it exists)."""
        account = get_user_model().objects.filter(username__iexact=username).first() if username else None
        audit.record(self.request, "admin_login_failed", account, reason=reason, username=username[:150])


def install():
    admin.site.login_form = OTPAdminAuthenticationForm
    admin.site.login_template = "admin/iga_login.html"

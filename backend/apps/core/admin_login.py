"""Django admin login with the same protections as the app: 2FA, attempt limits and lockout, and logging."""

import hashlib
import logging

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.cache import cache
from django.utils.translation import gettext as _

from apps.accounts import lockout
from apps.accounts.security import verify_totp

from . import security_log
from .audit import client_ip


class OTPAdminAuthenticationForm(AdminAuthenticationForm):
    otp = forms.CharField(
        label="Authenticator code",
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )

    def clean(self):
        username = (self.data.get("username") or "").strip().lower()
        key = "admin-login:" + hashlib.sha256(username.encode()).hexdigest()
        attempts = cache.get(key, 0)
        if attempts >= settings.ADMIN_LOGIN_ATTEMPTS_PER_MINUTE:
            self._log("admin_login_failed", None, username, reason="throttled", audit_every=600)
            raise forms.ValidationError(_("Too many attempts. Wait a minute and try again."), code="throttled")
        cache.set(key, attempts + 1, 60)

        # The same progressive lockout as the app's sign-in (shared counters).
        keys = lockout.sign_in_keys(username, client_ip(self.request))
        if lockout.check(keys):
            self._log("admin_login_failed", None, username, reason="locked", audit_every=600)
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
            self._log("admin_login_failed", self.get_user(), username, reason=",".join(sorted(c for c in codes if c)))
            raise
        lockout.succeed(keys)
        self._log("admin_login", self.get_user(), username)
        return cleaned

    def _log(self, action, user, username, audit_every=None, **details):
        if user is None:
            details["identifier"] = security_log.fingerprint(username)
        level = logging.INFO if action == "admin_login" else logging.WARNING
        security_log.event(self.request, action, user, level=level, audit_every=audit_every, **details)


def install():
    admin.site.login_form = OTPAdminAuthenticationForm
    admin.site.login_template = "admin/iga_login.html"

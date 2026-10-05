"""Django admin login with the same protections as the app: 2FA and a per-account attempt limit."""

import hashlib

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.cache import cache
from django.utils.translation import gettext as _

from apps.accounts.security import verify_totp


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
            raise forms.ValidationError(_("Too many attempts. Wait a minute and try again."), code="throttled")
        cache.set(key, attempts + 1, 60)

        cleaned = super().clean()  # checks the password and that the user is staff
        user = self.get_user()
        if user is not None:
            if user.totp_enabled:
                if not verify_totp(user, self.cleaned_data.get("otp")):
                    raise forms.ValidationError(_("Enter the current 6-digit code from your authenticator app."), code="otp")
            elif settings.ADMIN_REQUIRE_2FA:
                raise forms.ValidationError(
                    _("Turn on two-factor authentication in your Iga profile before using the admin site."), code="otp_required"
                )
        return cleaned


def install():
    admin.site.login_form = OTPAdminAuthenticationForm
    admin.site.login_template = "admin/iga_login.html"

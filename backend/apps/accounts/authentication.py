from django.utils.translation import gettext_lazy
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

# What someone may still do before replacing a temporary password.
ALLOWED_WITH_TEMPORARY_PASSWORD = {"/api/auth/me/", "/api/auth/password/", "/api/auth/logout/"}


class PasswordChangeRequired(PermissionDenied):
    default_detail = gettext_lazy("Choose a new password before continuing.")
    default_code = "password_change_required"


class IgaJWTAuthentication(JWTAuthentication):
    """JWT auth that holds accounts with a temporary password (set by a teacher) at the
    change-password step, so the teacher who knows it can't keep using the account."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, _ = result
            if user.must_change_password and request.path not in ALLOWED_WITH_TEMPORARY_PASSWORD:
                raise PasswordChangeRequired()
        return result

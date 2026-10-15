from django.utils.translation import gettext_lazy
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from .security import token_is_current

# What someone may still do before replacing a temporary password.
ALLOWED_WITH_TEMPORARY_PASSWORD = {"/api/auth/me/", "/api/auth/password/", "/api/auth/logout/"}


class PasswordChangeRequired(PermissionDenied):
    default_detail = gettext_lazy("Choose a new password before continuing.")
    default_code = "password_change_required"


class IgaJWTAuthentication(JWTAuthentication):
    """JWT auth that holds accounts with a temporary password (set by a teacher) at the
    change-password step, so the teacher who knows it can't keep using the account."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        # Every session ended (password changed or reset, 2FA changed, stolen token detected):
        # access tokens from before stop working at once, not when they expire.
        if not token_is_current(validated_token, user):
            raise AuthenticationFailed(gettext_lazy("Your session has ended. Log in again."), code="session_ended")
        return user

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, _ = result
            if user.must_change_password and request.path not in ALLOWED_WITH_TEMPORARY_PASSWORD:
                raise PasswordChangeRequired()
        return result

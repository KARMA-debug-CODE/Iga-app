"""Step-up: confirm your password (and 2FA code) before a privileged operation.

Tokens carry the time the user last gave their password ("auth_time", set at sign-in and kept through
refreshes, as in OpenID Connect). Privileged operations (apps.core.permissions.RecentAuthentication)
accept it for STEP_UP_MAX_AGE_SECONDS; after that the API answers 403 {"code": "step_up_required"}, the
app asks for the password again, and this endpoint hands back an access token stamped with the new time.
"""

import time

from django.utils.translation import gettext as _
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from apps.core import security_log
from apps.core.throttles import ScopedRateThrottle

from .security import SESSION_VERSION_CLAIM, verify_totp
from .throttles import AuthIPThrottle


def signed_in_now():
    return int(time.time())


def auth_time_of(token):
    """The "auth_time" claim of a token (a Unix time), or None when it has none or it is malformed."""
    getter = getattr(token, "get", None)
    if getter is None:
        return None
    value = getter("auth_time")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def stamp(token):
    """Mark a token as issued just after the user proved who they are."""
    token["auth_time"] = signed_in_now()
    return token


def fresh_access_token(user):
    token = AccessToken.for_user(user)
    # Without the session version, IgaJWTAuthentication would refuse it as a token from an ended session.
    token[SESSION_VERSION_CLAIM] = user.session_version
    return stamp(token)


class StepUpSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=4096, trim_whitespace=False)
    otp = serializers.CharField(max_length=8, required=False, allow_blank=True)


class StepUpView(APIView):
    """POST {password, otp?} -> {access}: a new access token that privileged operations accept.

    Wrong passwords and 2FA codes count towards the same per-account lock as other re-authentication
    (changing the password, email or 2FA), so a stolen session can't be used to guess them.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"
    throttle_classes = [ScopedRateThrottle, AuthIPThrottle]

    def post(self, request):
        from .views import _second_check  # views imports this module

        data = StepUpSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = request.user
        refusal = _second_check(
            request,
            user,
            lambda: user.check_password(data.validated_data["password"]),
            "reauth",
            "step_up",
            Response({"detail": _("That password is not right."), "code": "step_up_failed"}, status=status.HTTP_400_BAD_REQUEST),
            event="step_up_failed",
        )
        if refusal is not None:
            return refusal
        if user.totp_enabled:
            otp = data.validated_data.get("otp", "")
            if not otp:
                return Response(
                    {"detail": _("Enter the code from your authenticator app."), "otp_required": True},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            refusal = _second_check(
                request,
                user,
                lambda: verify_totp(user, otp),
                "otp",
                "step_up",
                Response({"detail": _("That code is not valid."), "otp_required": True}, status=status.HTTP_400_BAD_REQUEST),
                event="step_up_failed",
            )
            if refusal is not None:
                return refusal
        security_log.event(request, "step_up", user)
        return Response({"access": str(fresh_access_token(user))})

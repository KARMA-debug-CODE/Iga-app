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

from apps.core import audit

from .security import verify_totp


def signed_in_now():
    return int(time.time())


def stamp(token):
    """Mark a token as issued just after the user proved who they are."""
    token["auth_time"] = signed_in_now()
    return token


def fresh_access_token(user):
    return stamp(AccessToken.for_user(user))


class StepUpSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=4096, trim_whitespace=False)
    otp = serializers.CharField(max_length=8, required=False, allow_blank=True)


class StepUpView(APIView):
    """POST {password, otp?} -> {access}: a new access token that privileged operations accept."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"

    def post(self, request):
        data = StepUpSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(data.validated_data["password"]):
            audit.record(request, "step_up_failed", user, reason="password")
            return Response(
                {"detail": _("That password is not right."), "code": "step_up_failed"}, status=status.HTTP_400_BAD_REQUEST
            )
        if user.totp_enabled:
            otp = data.validated_data.get("otp", "")
            if not otp:
                return Response(
                    {"detail": _("Enter the code from your authenticator app."), "otp_required": True},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not verify_totp(user, otp):
                audit.record(request, "step_up_failed", user, reason="otp")
                return Response(
                    {"detail": _("That code is not valid."), "otp_required": True}, status=status.HTTP_400_BAD_REQUEST
                )
        audit.record(request, "step_up", user)
        return Response({"access": str(fresh_access_token(user))})

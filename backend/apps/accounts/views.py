from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core import audit

from .models import User
from .security import revoke_all_sessions, verify_totp
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    OTPSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .throttles import LoginIdentifierThrottle


def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        str(refresh_token),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )


def _session_response(user, status_code=status.HTTP_200_OK):
    refresh = RefreshToken.for_user(user)
    response = Response(
        {"access": str(refresh.access_token), "user": UserSerializer(user).data},
        status=status_code,
    )
    _set_refresh_cookie(response, refresh)
    return response


def _with_fresh_session(response, user):
    """After a security change: end every other session, keep this device logged in with a new cookie."""
    revoke_all_sessions(user)
    _set_refresh_cookie(response, RefreshToken.for_user(user))
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        audit.record(request, "register", user, role=user.role)
        return _session_response(user, status.HTTP_201_CREATED)


class LoginView(APIView):
    """Log in with username *or* email. If 2FA is on, a 6-digit code is required too."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"
    throttle_classes = [LoginIdentifierThrottle, ScopedRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"].strip()
        password = serializer.validated_data["password"]

        # An "@" means an email address; usernames can't contain one. Ambiguity never logs anyone in.
        lookup = Q(email__iexact=identifier) if "@" in identifier else Q(username__iexact=identifier)
        matches = list(User.objects.filter(lookup)[:2])
        match = matches[0] if len(matches) == 1 else None
        # Always run authenticate() so unknown usernames cost the same hashing time.
        user = authenticate(request, username=match.username if match else identifier, password=password)
        if user is None:
            return Response({"detail": "Invalid username/email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        if user.totp_enabled:
            otp = serializer.validated_data.get("otp", "")
            if not otp:
                return Response(
                    {"detail": "Enter the code from your authenticator app.", "otp_required": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not verify_totp(user, otp):
                return Response(
                    {"detail": "That code is not valid.", "otp_required": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        return _session_response(user)


class RefreshView(APIView):
    """Exchange the httpOnly refresh cookie for a new access token (and rotate the cookie)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "refresh"

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            return Response({"detail": "Not logged in."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            old = RefreshToken(raw)
            user = User.objects.get(pk=old["user_id"], is_active=True)
        except (TokenError, User.DoesNotExist, KeyError):
            just_rotated = self._handle_reuse(raw)
            response = Response({"detail": "Session expired."}, status=status.HTTP_401_UNAUTHORIZED)
            if not just_rotated:
                # (A token rotated moments ago means another tab already holds the new cookie; keep it.)
                response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
            return response
        old.blacklist()  # rotation: each refresh token works exactly once
        return _session_response(user)

    @staticmethod
    def _handle_reuse(raw):
        """A rotated (already used) token coming back means it was copied: end every session of that user.

        Two tabs refreshing at the same moment look the same for a few seconds, so reuse within
        REFRESH_REUSE_GRACE_SECONDS only fails that one request. Returns True in that case.
        """
        try:
            token = RefreshToken(raw, verify=False)
            jti, user_id = token["jti"], token["user_id"]
        except (TokenError, KeyError):
            return False
        used = BlacklistedToken.objects.filter(token__jti=jti).first()
        if used is None:
            return False
        if timezone.now() - used.blacklisted_at < timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS):
            return True
        user = User.objects.filter(pk=user_id).first()
        if user:
            revoke_all_sessions(user)
            audit.record(None, "refresh_token_reuse", user)
        return False


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.must_change_password = False
        request.user.save(update_fields=["password", "must_change_password"])
        audit.record(request, "change_password", request.user)
        return _with_fresh_session(Response({"detail": "Password updated. You were logged out on other devices."}), request.user)


class TwoFactorSetupView(APIView):
    """Generate a fresh secret. 2FA is only switched on after the user proves they saved it."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.totp_enabled:
            return Response({"detail": "Two-factor authentication is already on."}, status=status.HTTP_400_BAD_REQUEST)
        user.totp_secret = pyotp.random_base32()
        user.totp_last_step = None
        user.save(update_fields=["totp_secret", "totp_last_step"])
        uri = pyotp.TOTP(user.totp_secret).provisioning_uri(name=user.username, issuer_name=settings.APP_NAME)
        return Response({"secret": user.totp_secret, "otpauth_uri": uri})


class TwoFactorEnableView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"

    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not verify_totp(user, serializer.validated_data["otp"]):
            return Response({"detail": "That code is not valid."}, status=status.HTTP_400_BAD_REQUEST)
        user.totp_enabled = True
        user.save(update_fields=["totp_enabled"])
        audit.record(request, "enable_2fa", user)
        return _with_fresh_session(Response(UserSerializer(user).data), user)


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"

    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.totp_enabled or not verify_totp(user, serializer.validated_data["otp"]):
            return Response({"detail": "That code is not valid."}, status=status.HTTP_400_BAD_REQUEST)
        user.totp_enabled = False
        user.totp_secret = ""
        user.totp_last_step = None
        user.save(update_fields=["totp_enabled", "totp_secret", "totp_last_step"])
        audit.record(request, "disable_2fa", user)
        return _with_fresh_session(Response(UserSerializer(user).data), user)

import logging
import math
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenBackendError, TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.classroom.services import follow_grade
from apps.core import security_log
from apps.core.audit import client_ip
from apps.core.security_log import fingerprint

from . import enumeration, lockout, password_reset
from .authentication import PasswordChangeRequired
from .models import User
from .security import (
    SESSION_VERSION_CLAIM,
    check_password_or_dummy,
    find_account,
    is_cross_site,
    issue_refresh_token,
    revoke_all_sessions,
    token_is_current,
    verify_totp,
)
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    OTPSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .throttles import (
    AuthIPThrottle,
    LoginIdentifierThrottle,
    PasswordResetIdentifierThrottle,
    PasswordResetIPThrottle,
    RefreshIPThrottle,
    RefreshUserThrottle,
    RegisterIPThrottle,
)


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
    refresh = issue_refresh_token(user)
    response = Response(
        {"access": str(refresh.access_token), "user": UserSerializer(user).data},
        status=status_code,
    )
    _set_refresh_cookie(response, refresh)
    return response


def locked_response(seconds):
    """The answer while sign-in is locked: the same for every username, real or not."""
    minutes = max(1, math.ceil(seconds / 60))
    response = Response(
        {
            "detail": _("Too many failed attempts. Try again in %(minutes)s min.") % {"minutes": minutes},
            "retry_after": seconds,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    response["Retry-After"] = str(seconds)
    return response


def cross_site_refusal(request):
    """The answer to a cookie-authenticated request sent from another site (CSRF), or None."""
    if not is_cross_site(request):
        return None
    security_log.event(
        request,
        "cross_site_refused",
        None,
        level=logging.WARNING,
        audit_every=600,
        origin=request.META.get("HTTP_ORIGIN") or request.META.get("HTTP_REFERER", "")[:200],
    )
    return Response({"detail": _("This request came from another site and was refused.")}, status=status.HTTP_403_FORBIDDEN)


def _with_fresh_session(response, user):
    """After a security change: end every other session, keep this device logged in with a new cookie."""
    revoke_all_sessions(user)
    refresh = issue_refresh_token(user)
    _set_refresh_cookie(response, refresh)
    if isinstance(response.data, dict):
        response.data["access"] = str(refresh.access_token)  # this device's old access token has just ended
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, RegisterIPThrottle]

    def post(self, request):
        with_email = bool(str(request.data.get("email") or "").strip())
        if with_email:
            enumeration.check_budget(request)
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            if serializer.email_in_use:
                enumeration.spend(request)
            raise ValidationError(serializer.errors)
        user = serializer.save()
        security_log.event(request, "register", user, role=user.role)
        return _session_response(user, status.HTTP_201_CREATED)


class LoginView(APIView):
    """Log in with username *or* email. If 2FA is on, a 6-digit code is required too.

    Repeated failures lock the username (and, much later, the IP address) for a growing time
    (see lockout.py). Every answer is the same for real and made-up accounts, and takes as long.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginIdentifierThrottle, AuthIPThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"].strip()
        password = serializer.validated_data["password"]
        keys = lockout.sign_in_keys(identifier, client_ip(request))

        wait = lockout.check(keys)
        if wait:
            security_log.event(
                request,
                "login_locked",
                None,
                level=logging.WARNING,
                audit_every=600,
                identifier=fingerprint(identifier),
                retry_after=wait,
            )
            return locked_response(wait)

        account = find_account(identifier)
        # Unknown names are checked against a dummy hash, so they cost the same time as real ones.
        password_ok = check_password_or_dummy(account, password)
        if not password_ok or not account.is_active:
            reason = "inactive" if password_ok else "password"
            return self._failed(request, keys, identifier, account, reason, _("Invalid username/email or password."))

        if account.temporary_password_expired:
            # Only someone who typed the right temporary password learns this.
            security_log.event(request, "login_failed", account, level=logging.WARNING, reason="temporary_password_expired")
            return Response(
                {
                    "detail": _("This temporary password has expired. Ask your teacher for a new one."),
                    "code": "temporary_password_expired",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if account.totp_enabled:
            otp = serializer.validated_data.get("otp", "")
            if not otp:
                return Response(
                    {"detail": _("Enter the code from your authenticator app."), "otp_required": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not verify_totp(account, otp):
                return self._failed(request, keys, identifier, account, "otp", _("That code is not valid."), otp_required=True)

        lockout.succeed(keys)
        update_last_login(None, account)
        security_log.event(request, "login", account)
        return _session_response(account)

    @staticmethod
    def _failed(request, keys, identifier, account, reason, message, **extra):
        started = lockout.fail(keys)
        details = {"reason": reason} if account else {"reason": reason, "identifier": fingerprint(identifier)}
        security_log.event(request, "login_failed", account, level=logging.WARNING, **details)
        if started:
            seconds = max(started.values())
            security_log.event(
                request, "account_locked", account, level=logging.WARNING, locks=sorted(started), seconds=seconds, **details
            )
            return locked_response(seconds)
        return Response({"detail": message, **extra}, status=status.HTTP_401_UNAUTHORIZED)


class RefreshView(APIView):
    """Exchange the httpOnly refresh cookie for a new access token (and rotate the cookie)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RefreshIPThrottle, RefreshUserThrottle]

    def post(self, request):
        refusal = cross_site_refusal(request)
        if refusal is not None:
            return refusal
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            return Response({"detail": _("Not logged in.")}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            old = RefreshToken(raw)
            user = User.objects.get(pk=old["user_id"], is_active=True)
            if not token_is_current(old, user):
                raise TokenError("session ended")
        except (TokenError, User.DoesNotExist, KeyError):
            just_rotated = self._handle_reuse(request, raw)
            response = Response({"detail": _("Session expired.")}, status=status.HTTP_401_UNAUTHORIZED)
            if not just_rotated:
                # (A token rotated moments ago means another tab already holds the new cookie; keep it.)
                response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
            return response
        old.blacklist()  # rotation: each refresh token works exactly once
        return _session_response(user)

    @staticmethod
    def _handle_reuse(request, raw):
        """A rotated (already used) token coming back means it was copied: end every session of that user.

        Two tabs refreshing at the same moment look the same for a few seconds, so reuse within
        REFRESH_REUSE_GRACE_SECONDS only fails that one request. Returns True in that case.
        """
        try:
            # The signature is checked (only the blacklist isn't): a made-up or edited token naming
            # someone else must never end their sessions.
            payload = token_backend.decode(raw, verify=True)
            jti, user_id = payload[jwt_settings.JTI_CLAIM], payload[jwt_settings.USER_ID_CLAIM]
        except (TokenBackendError, KeyError):
            return False
        used = BlacklistedToken.objects.filter(token__jti=jti, token__user_id=user_id).first()
        if used is None:
            return False
        user = User.objects.filter(pk=user_id).first()
        if user is None or payload.get(SESSION_VERSION_CLAIM, 0) != user.session_version:
            # From a session that was already ended (a password change on another device, logging
            # out everywhere): that's not theft, and there is nothing more to end.
            return False
        if timezone.now() - used.blacklisted_at < timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS):
            return True
        revoke_all_sessions(user)
        security_log.event(request, "refresh_token_reuse", user, level=logging.WARNING)
        return False


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RefreshIPThrottle]

    def post(self, request):
        refusal = cross_site_refusal(request)
        if refusal is not None:
            return refusal
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
        return response


class LogoutEverywhereView(APIView):
    """End every session of this account, on every device (this one included)."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"
    throttle_classes = [ScopedRateThrottle, AuthIPThrottle]

    def post(self, request):
        revoke_all_sessions(request.user)
        security_log.event(request, "logout_everywhere", request.user)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        # Someone holding a teacher's temporary password may only pick the language until the
        # password is changed (otherwise they could set an email and later reset the password).
        if user.must_change_password and set(request.data) - {"preferred_language"}:
            raise PasswordChangeRequired()
        old_email = user.email or ""
        changes_email = "email" in request.data and lockout.normalize(request.data.get("email")) != lockout.normalize(old_email)
        if changes_email:
            if str(request.data.get("email") or "").strip():
                enumeration.check_budget(request, user)
            # Password reset links go to this address, so changing it needs the password.
            if user.has_usable_password():
                refusal = password_refusal(
                    request,
                    user,
                    request.data.get("current_password"),
                    "change_email",
                    _("Enter your current password to change your email address."),
                )
                if refusal is not None:
                    return refusal
        old_grade = user.grade
        serializer = UserSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            if serializer.email_in_use:
                enumeration.spend(request, user)
            raise ValidationError(serializer.errors)
        user = serializer.save()
        data = dict(serializer.data)
        if user.grade != old_grade:
            # The whole app follows the new grade; classes for the old grade leave the student's lists.
            data["left_classes"] = follow_grade(user)
        if changes_email:
            user.password_reset_tokens.all().delete()  # links sent to the old address stop working
            security_log.event(request, "email_changed", user, had_email=bool(old_email), has_email=bool(user.email))
        return Response(data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"
    throttle_classes = [ScopedRateThrottle, AuthIPThrottle]

    def post(self, request):
        refusal = password_refusal(request, request.user, request.data.get("current_password"), "change_password")
        if refusal is not None:
            return refusal
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.must_change_password = False
        request.user.temporary_password_expires_at = None
        request.user.save(update_fields=["password", "must_change_password", "temporary_password_expires_at"])
        security_log.event(request, "change_password", request.user, other_sessions_ended=True)
        return _with_fresh_session(
            Response({"detail": _("Password updated. You were logged out on other devices.")}), request.user
        )


def _second_check(request, user, passed, kind, purpose, wrong_answer):
    """None when `passed()` is true; otherwise the answer to send.

    For an account already signed in (changing its password, email or 2FA): wrong answers count
    towards a lock for that account, like sign-in, so a stolen session can't be used to guess the
    password or a 2FA code; each one is logged.
    """
    keys = [(kind, f"user:{user.pk}")]
    event = "2fa_failed" if kind == "otp" else "reauth_failed"
    wait = lockout.check(keys)
    if wait:
        security_log.event(request, event, user, level=logging.WARNING, audit_every=600, purpose=purpose, locked=True)
        return locked_response(wait)
    if passed():
        lockout.succeed(keys)
        return None
    started = lockout.fail(keys)
    security_log.event(request, event, user, level=logging.WARNING, purpose=purpose)
    if started:
        security_log.event(request, "account_locked", user, level=logging.WARNING, locks=[kind], seconds=started[kind])
        return locked_response(started[kind])
    return wrong_answer


def otp_refusal(request, user, code, purpose):
    """None when `code` is the user's current 2FA code; otherwise the answer to send."""
    return _second_check(
        request,
        user,
        lambda: verify_totp(user, code),
        "otp",
        purpose,
        Response({"detail": _("That code is not valid.")}, status=status.HTTP_400_BAD_REQUEST),
    )


def password_refusal(request, user, password, purpose, message=None):
    """None when `password` is the user's current password; otherwise the answer to send."""
    return _second_check(
        request,
        user,
        lambda: user.check_password(str(password or "")),
        "reauth",
        purpose,
        Response(
            {"current_password": [message or _("Incorrect password.")]},
            status=status.HTTP_400_BAD_REQUEST,
        ),
    )


class TwoFactorSetupView(APIView):
    """Generate a fresh secret. 2FA is only switched on after the user proves they saved it."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"
    throttle_classes = [ScopedRateThrottle, AuthIPThrottle]

    def post(self, request):
        user = request.user
        if user.totp_enabled:
            return Response({"detail": _("Two-factor authentication is already on.")}, status=status.HTTP_400_BAD_REQUEST)
        user.totp_secret = pyotp.random_base32()
        user.totp_last_step = None
        user.save(update_fields=["totp_secret", "totp_last_step"])
        uri = pyotp.TOTP(user.totp_secret).provisioning_uri(name=user.username, issuer_name=settings.APP_NAME)
        return Response({"secret": user.totp_secret, "otpauth_uri": uri})


class TwoFactorEnableView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"
    throttle_classes = [ScopedRateThrottle, AuthIPThrottle]

    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        refusal = otp_refusal(request, user, serializer.validated_data["otp"], "enable")
        if refusal is not None:
            return refusal
        user.totp_enabled = True
        user.save(update_fields=["totp_enabled"])
        security_log.event(request, "enable_2fa", user, other_sessions_ended=True)
        return _with_fresh_session(Response(UserSerializer(user).data), user)


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "sensitive"
    throttle_classes = [ScopedRateThrottle, AuthIPThrottle]

    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.totp_enabled:
            return Response({"detail": _("That code is not valid.")}, status=status.HTTP_400_BAD_REQUEST)
        refusal = otp_refusal(request, user, serializer.validated_data["otp"], "disable")
        if refusal is not None:
            return refusal
        user.totp_enabled = False
        user.totp_secret = ""
        user.totp_last_step = None
        user.save(update_fields=["totp_enabled", "totp_secret", "totp_last_step"])
        security_log.event(request, "disable_2fa", user, other_sessions_ended=True)
        return _with_fresh_session(Response(UserSerializer(user).data), user)


class PasswordResetRequestView(APIView):
    """Email a single-use link to choose a new password. The answer never says whether an account exists."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetIdentifierThrottle, PasswordResetIPThrottle, AuthIPThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password_reset.request_reset(request, serializer.validated_data["identifier"].strip())
        minutes = settings.PASSWORD_RESET_TIMEOUT // 60
        return Response(
            {
                "detail": _(
                    "If an account matches and has an email address, we have sent it a link to choose a new "
                    "password. The link works once, for %(minutes)s minutes."
                )
                % {"minutes": minutes}
            }
        )


class PasswordResetConfirmView(APIView):
    """Choose a new password with the link's secret. Every session of the account ends."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthIPThrottle]

    @transaction.atomic
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = password_reset.valid_token(serializer.validated_data["token"], lock=True)
        if record is None:
            security_log.event(request, "password_reset_failed", None, level=logging.WARNING, audit_every=600)
            return Response(
                {"detail": _("This link is not valid or has expired. Ask for a new one."), "code": "invalid_link"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = record.user
        new_password = serializer.validated_data["new_password"]
        try:
            password_validation.validate_password(new_password, user)
        except DjangoValidationError as error:
            return Response({"new_password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.must_change_password = False
        user.temporary_password_expires_at = None
        # Saving the new password ends every session and every reset link of the account.
        user.save(update_fields=["password", "must_change_password", "temporary_password_expires_at"])
        revoke_all_sessions(user)
        security_log.event(request, "password_reset", user, other_sessions_ended=True)
        return Response({"detail": _("Your password has been changed. Log in with your new password.")})

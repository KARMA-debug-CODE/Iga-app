import hashlib

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.state import token_backend

from apps.core.audit import client_ip

from .lockout import normalize


class IdentifierThrottle(SimpleRateThrottle):
    """Limit attempts per account (the submitted username or email), not per IP.

    Whole schools often share one public IP address, so an IP-only limit would lock out a
    classroom logging in at the same time. Limiting by the submitted username/email still stops
    guessing against any one account, and an unknown name is limited exactly like a real one.
    """

    field = "identifier"

    def get_cache_key(self, request, view):
        identifier = normalize(request.data.get(self.field, "")) if hasattr(request, "data") else ""
        if not identifier:
            return None
        digest = hashlib.sha256(identifier.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}


class LoginIdentifierThrottle(IdentifierThrottle):
    scope = "login"


class PasswordResetIdentifierThrottle(IdentifierThrottle):
    """Reset emails per account, so nobody can flood someone's inbox."""

    scope = "password_reset"


class IPThrottle(SimpleRateThrottle):
    """Per client IP address (trusting X-Forwarded-For only from our own proxies), signed in or not."""

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": client_ip(request) or self.get_ident(request)}


class AuthIPThrottle(IPThrottle):
    scope = "auth"


class RegisterIPThrottle(IPThrottle):
    scope = "register"


class PasswordResetIPThrottle(IPThrottle):
    scope = "password_reset_ip"


class RefreshIPThrottle(IPThrottle):
    scope = "refresh"


class RefreshUserThrottle(SimpleRateThrottle):
    """Per account: refreshes with the account's (validly signed) refresh cookie.

    Only a token our server signed counts, so nobody can use up someone else's allowance by
    sending made-up tokens with their user id.
    """

    scope = "refresh_user"

    def get_cache_key(self, request, view):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            return None
        try:
            user_id = token_backend.decode(raw, verify=True).get(jwt_settings.USER_ID_CLAIM)
        except TokenBackendError:
            return None
        return self.cache_format % {"scope": self.scope, "ident": user_id} if user_id else None

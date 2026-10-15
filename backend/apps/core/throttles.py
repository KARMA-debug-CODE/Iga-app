"""Rate limits shared by every API view (REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] in settings).

Each request is counted against at least one limit: the view's own scope when it has one, plus a per-IP
limit for visitors who are not signed in and a per-user limit for those who are. Views that list their own
throttle_classes replace these defaults with stricter ones (sign-in, sign-up, password reset, refresh);
tests/test_rate_limits.py checks that no view ends up with none.

Client IPs come from apps.core.audit.client_ip, which only trusts the X-Forwarded-For entries our own
proxies add (TRUSTED_PROXY_COUNT), so a client cannot get a fresh allowance by sending a made-up header.
"""

from rest_framework import throttling

from .audit import client_ip


class ClientIPMixin:
    """Identify anonymous clients the way the audit log does (DRF's own NUM_PROXIES logic doesn't validate)."""

    def get_ident(self, request):
        return client_ip(request) or super().get_ident(request)


def _signed_in(request):
    user = getattr(request, "user", None)
    return user is not None and user.is_authenticated


class ScopedRateThrottle(ClientIPMixin, throttling.ScopedRateThrottle):
    """The view's own scope (throttle_scope), per user when signed in and per IP otherwise."""


class AnonRateThrottle(ClientIPMixin, throttling.SimpleRateThrottle):
    """Per IP: every request without a signed-in user. Generous, because a whole school shares one address."""

    scope = "anon"

    def get_cache_key(self, request, view):
        if _signed_in(request):
            return None
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class UserRateThrottle(ClientIPMixin, throttling.SimpleRateThrottle):
    """Per signed-in user: every request, a backstop above anything a person can do by hand."""

    scope = "user"

    def get_cache_key(self, request, view):
        if not _signed_in(request):
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class JoinRateThrottle(ClientIPMixin, throttling.UserRateThrottle):
    """Per user: limits guessing of class, study-group and parent-link codes."""

    scope = "join"

import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginIdentifierThrottle(SimpleRateThrottle):
    """Limit login attempts per account, not per IP.

    Whole schools often share one public IP address, so an IP-only limit would
    lock out a classroom logging in at the same time. Limiting by the submitted
    username/email still stops password guessing against any one account.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        identifier = str(request.data.get("identifier", "")).strip().lower()
        if not identifier:
            return None
        digest = hashlib.sha256(identifier.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}

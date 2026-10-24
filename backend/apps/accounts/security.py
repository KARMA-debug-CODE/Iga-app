"""Session revocation, sign-in checks and one-time-code checks shared by the auth views."""

import hmac
import secrets
import time
from urllib.parse import urlsplit

import pyotp
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q
from django.utils.http import is_same_domain
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .lockout import normalize

STEP_SECONDS = 30
# The token claim carrying the user's session version (User.session_version).
SESSION_VERSION_CLAIM = "sv"

_dummy_hashes = {}


def issue_refresh_token(user, auth_time=None):
    """A new refresh token (and, through it, access token) for the user's current session version.

    `auth_time` is when the user last gave their password (see stepup.py); the access token copies it.
    """
    token = RefreshToken.for_user(user)
    token[SESSION_VERSION_CLAIM] = user.session_version
    if auth_time is not None:
        token["auth_time"] = auth_time
    return token


def token_is_current(token, user):
    """False for a token issued before the user's sessions were last ended."""
    return token.get(SESSION_VERSION_CLAIM, 0) == user.session_version


def revoke_all_sessions(user):
    """Log out everywhere: blacklist every refresh token, and make every access token stop working now."""
    for token in OutstandingToken.objects.filter(user=user).exclude(blacklistedtoken__isnull=False):
        BlacklistedToken.objects.get_or_create(token=token)
    user.bump_session_version()


def find_account(identifier):
    """The one account a typed username or email names, or None.

    An "@" means an email address (usernames can't contain one). The database's case-insensitive
    match is confirmed with the same case folding the sign-in lockout uses, so a spelling the
    database happens to treat as equal (such as a dotless i on PostgreSQL) can't reach an account
    under a different lockout counter. Ambiguity never logs anyone in.
    """
    from .models import User

    field = "email" if "@" in identifier else "username"
    wanted = normalize(identifier)
    matches = [
        user
        for user in User.objects.filter(Q(**{f"{field}__iexact": identifier.strip()}))[:2]
        if normalize(getattr(user, field)) == wanted
    ]
    return matches[0] if len(matches) == 1 else None


def _dummy_hash():
    """A hash made with the current password hasher and costs, built once per process."""
    key = (settings.PASSWORD_HASHERS[0], settings.ARGON2_TIME_COST, settings.ARGON2_MEMORY_COST_KIB, settings.ARGON2_PARALLELISM)
    if key not in _dummy_hashes:
        _dummy_hashes[key] = make_password(secrets.token_urlsafe(32))
    return _dummy_hashes[key]


def check_password_or_dummy(user, password):
    """Check `password` for `user`; for no user, spend the same time on a dummy hash and fail.

    Verifying (rather than creating) a hash for unknown names keeps both paths equally long, so
    timing can't reveal which usernames or emails have an account.
    """
    if user is None or not user.has_usable_password():
        check_password(password, _dummy_hash())
        return False
    return user.check_password(password)


def verify_totp(user, code, now=None):
    """Check a 6-digit code (±30 s for clock drift) and refuse to accept the same code twice."""
    if not user.totp_secret or not code:
        return False
    code = str(code).strip().replace(" ", "")
    totp = pyotp.TOTP(user.totp_secret)
    current = int((now if now is not None else time.time()) // STEP_SECONDS)
    for step in (current - 1, current, current + 1):
        if hmac.compare_digest(totp.generate_otp(step), code):
            # A conditional UPDATE, so two simultaneous requests can't both spend the same code.
            unused = Q(totp_last_step__isnull=True) | Q(totp_last_step__lt=step)
            if not type(user).objects.filter(unused, pk=user.pk).update(totp_last_step=step):
                return False  # replayed
            user.totp_last_step = step
            return True
    return False


LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _origin_of(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower() if parts.scheme and parts.netloc else None


def is_cross_site(request):
    """True when a browser says this request comes from a page on another site.

    For the endpoints a cookie authenticates (refresh, logout), on top of the cookie's SameSite
    flag: the Origin header (or, from older browsers, the Referer) must be this site, the
    frontend's origin (CORS_ALLOWED_ORIGINS) or a CSRF_TRUSTED_ORIGINS entry (wildcards such as
    https://*.iga.rw allowed). "Origin: null" (sandboxed frames, data: pages) is refused. A request
    with neither header doesn't come from a web page (an app, curl), so CSRF can't apply to it.
    """
    origin = request.META.get("HTTP_ORIGIN")
    if origin is None:
        referer = request.META.get("HTTP_REFERER")
        if not referer:
            return False
        origin = _origin_of(referer)
        if origin is None:
            return True
    origin = origin.strip().lower()
    if origin == "null":
        return True
    if settings.DEBUG and urlsplit(origin).hostname in LOOPBACK_HOSTS:
        return False  # local development: Vite's proxy rewrites the Host header to the backend's port
    own = f"{'https' if request.is_secure() else 'http'}://{request.get_host()}".lower()
    trusted = {own, *(o.lower() for o in settings.CORS_ALLOWED_ORIGINS), *(o.lower() for o in settings.CSRF_TRUSTED_ORIGINS)}
    if origin in trusted:
        return False
    scheme, _, netloc = origin.partition("://")
    for entry in trusted:
        entry_scheme, _, pattern = entry.partition("://")
        if pattern.startswith("*.") and entry_scheme == scheme and is_same_domain(netloc, pattern[1:]):
            return False
    return True

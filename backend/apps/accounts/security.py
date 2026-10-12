"""Session revocation, sign-in checks and one-time-code checks shared by the auth views."""

import hmac
import secrets
import time

import pyotp
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .lockout import normalize

STEP_SECONDS = 30
# The token claim carrying the user's session version (User.session_version).
SESSION_VERSION_CLAIM = "sv"

_dummy_hashes = {}


def issue_refresh_token(user):
    """A new refresh token (and, through it, access token) for the user's current session version."""
    token = RefreshToken.for_user(user)
    token[SESSION_VERSION_CLAIM] = user.session_version
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

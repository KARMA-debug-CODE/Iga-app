"""Session revocation and one-time-code checks shared by the auth views."""

import hmac
import time

import pyotp
from django.db.models import Q
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

STEP_SECONDS = 30


def revoke_all_sessions(user):
    """Blacklist every refresh token the user holds (logout everywhere)."""
    for token in OutstandingToken.objects.filter(user=user).exclude(blacklistedtoken__isnull=False):
        BlacklistedToken.objects.get_or_create(token=token)


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

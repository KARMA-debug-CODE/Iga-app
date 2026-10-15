"""Progressive lockout after repeated failed sign-ins: per account, per account and IP, per IP.

Failures in a row (a wrong password or a wrong 2FA code) are counted three ways:

- one username or email from one IP address: locked after LOGIN_LOCKOUT_THRESHOLD (5);
- one username or email from anywhere: locked after LOGIN_LOCKOUT_ACCOUNT_THRESHOLD (20), so
  spreading guesses over many addresses doesn't help, while one attacker elsewhere can't lock a
  student out of their own account after 5 tries;
- one IP address, any account: locked after LOGIN_LOCKOUT_IP_THRESHOLD (100), a high number because
  a whole school often shares one public address.

The first lock lasts LOGIN_LOCKOUT_BASE_SECONDS; each further lock within a day doubles it, up to
LOGIN_LOCKOUT_MAX_SECONDS. Locks are keyed on the text that was typed (case-folded), never on whether
an account exists, so a made-up name is locked exactly like a real one and a lock can't tell anyone
which accounts exist. Counters live in the shared cache (Redis in production), so every server
process sees them.
"""

import hashlib
import time

from django.conf import settings
from django.core.cache import cache

DAY = 24 * 60 * 60


def normalize(identifier):
    """How a typed username or email is compared: whitespace trimmed, case folded."""
    return str(identifier or "").strip().casefold()


def _key(kind, ident, part):
    digest = hashlib.sha256(f"{kind}:{ident}".encode()).hexdigest()
    return f"lockout:{part}:{digest}"


def _limits(kind):
    return {
        "ip": settings.LOGIN_LOCKOUT_IP_THRESHOLD,
        "account": settings.LOGIN_LOCKOUT_ACCOUNT_THRESHOLD,
    }.get(kind, settings.LOGIN_LOCKOUT_THRESHOLD)


def locked_for(kind, ident):
    """Seconds left on a lock (0 when not locked)."""
    if not ident:
        return 0
    until = cache.get(_key(kind, ident, "until"))
    return max(0, int(until - time.time()) + 1) if until else 0


def register_failure(kind, ident):
    """Count one failure. Returns the length of the lock it starts, in seconds (0 if none)."""
    if not ident:
        return 0
    window = settings.LOGIN_FAILURE_WINDOW_SECONDS
    failures_key = _key(kind, ident, "failures")
    cache.add(failures_key, 0, window)
    try:
        failures = cache.incr(failures_key)
    except ValueError:  # expired between add() and incr()
        cache.set(failures_key, 1, window)
        failures = 1
    cache.touch(failures_key, window)
    if failures < _limits(kind):
        return 0
    level_key = _key(kind, ident, "level")
    cache.add(level_key, 0, DAY)
    try:
        level = cache.incr(level_key)
    except ValueError:
        cache.set(level_key, 1, DAY)
        level = 1
    cache.touch(level_key, DAY)
    seconds = min(settings.LOGIN_LOCKOUT_BASE_SECONDS * 2 ** (level - 1), settings.LOGIN_LOCKOUT_MAX_SECONDS)
    cache.set(_key(kind, ident, "until"), time.time() + seconds, seconds)
    cache.delete(failures_key)
    return seconds


def clear_failures(kind, ident):
    """A successful sign-in resets the count of failures in a row (earlier lockouts still count for a day)."""
    if ident:
        cache.delete(_key(kind, ident, "failures"))


def sign_in_keys(identifier, ip):
    """The counters one sign-in attempt touches: (kind, key) pairs."""
    ident = normalize(identifier)
    return [("pair", f"{ident}|{ip}"), ("account", ident), ("ip", ip or "")]


def check(keys):
    """Seconds until sign-in is allowed again for these counters (0 = allowed)."""
    return max(locked_for(kind, ident) for kind, ident in keys)


def fail(keys):
    """Count a failed attempt on every counter; returns {kind: lock seconds} for the locks it started."""
    started = {}
    for kind, ident in keys:
        seconds = register_failure(kind, ident)
        if seconds:
            started[kind] = seconds
    return started


def succeed(keys):
    for kind, ident in keys:
        if kind != "ip":  # one good password doesn't vouch for every other attempt from that address
            clear_failures(kind, ident)

"""Slowing down "is this email address taken?" probing.

Signing up, changing one's email and previewing a class roster must say when an email address is
already used by another account (people need to know why it was refused), which also tells a
prober that the address has an account. Each such answer spends from a small hourly budget, per IP
address for sign-ups and per account otherwise. Once the budget is spent, every request carrying an
email address is refused for the rest of the hour, whether the address is taken or not, so the
refusal itself reveals nothing and nobody can test more than a handful of addresses an hour.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _
from rest_framework.exceptions import Throttled

from apps.core import security_log
from apps.core.audit import client_ip

WINDOW_SECONDS = 60 * 60


def _key(request, user):
    who = f"user:{user.pk}" if user is not None else f"ip:{client_ip(request)}"
    return f"email-in-use:{who}"


def check_budget(request, user=None):
    """Refuse (429) a request carrying an email address once the budget is spent."""
    if cache.get(_key(request, user), 0) >= settings.EMAIL_IN_USE_LIMIT:
        raise Throttled(
            wait=WINDOW_SECONDS,
            detail=_("Too many attempts with email addresses already in use. Try again in an hour."),
        )


def spend(request, user=None, count=1):
    """Count `count` answers that said an email address is already in use."""
    key = _key(request, user)
    cache.add(key, 0, WINDOW_SECONDS)
    try:
        used = cache.incr(key, count)
    except ValueError:
        cache.set(key, count, WINDOW_SECONDS)
        used = count
    security_log.event(
        request,
        "email_in_use",
        user,
        level=logging.WARNING if used >= settings.EMAIL_IN_USE_LIMIT else logging.INFO,
        audit_every=600,
        count=count,
        total_this_hour=used,
    )

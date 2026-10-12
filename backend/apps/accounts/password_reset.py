"""Password reset by email: single-use links that expire.

A link carries a random secret (256 bits); only its SHA-256 is stored, so a copy of the database
can't be used to reset anyone's password. A link works once, for PASSWORD_RESET_TIMEOUT seconds
(1 hour by default), and stops working as soon as the password changes (by this link or any other
way), a newer link is sent, or the account's email address changes.

Asking for a link always gets the same answer, whether or not the username or email has an
account. The lookup, the link and the email happen after the answer is sent (in a background
thread), so the time the answer takes can't reveal it either.
"""

import hashlib
import logging
import secrets
import threading
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import connections, transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.core import security_log
from apps.core.constants import LANGUAGE_CODES

from .models import PasswordResetToken
from .security import find_account

log = logging.getLogger(__name__)


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_link(user):
    """A new reset link for `user`. Any older link for the account stops working."""
    token = secrets.token_urlsafe(32)
    now = timezone.now()
    with transaction.atomic():
        PasswordResetToken.objects.filter(user=user).delete()
        PasswordResetToken.objects.filter(expires_at__lt=now).delete()  # tidy up everyone's old links
        PasswordResetToken.objects.create(
            user=user, token_hash=_digest(token), expires_at=now + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        )
    # In the fragment (#), so the secret never reaches a server log or a Referer header.
    return f"{settings.FRONTEND_URL}/reset-password#{token}"


def valid_token(token, lock=False):
    """The unexpired, unused PasswordResetToken for this secret, or None."""
    if not isinstance(token, str) or not token or len(token) > 128:
        return None
    tokens = PasswordResetToken.objects.select_related("user")
    if lock:
        tokens = tokens.select_for_update()
    found = tokens.filter(token_hash=_digest(token)).first()
    if found is None or found.expires_at <= timezone.now() or not found.user.is_active:
        return None
    return found


def _compose(user, link):
    language = user.preferred_language if user.preferred_language in LANGUAGE_CODES else "en"
    minutes = settings.PASSWORD_RESET_TIMEOUT // 60
    with translation.override(language):
        subject = _("%(app)s: choose a new password") % {"app": settings.APP_NAME}
        body = "\n".join(
            [
                _("Hello %(name)s,") % {"name": user.first_name or user.username},
                "",
                _("Someone (hopefully you) asked to reset the password of your %(app)s account %(username)s.")
                % {"app": settings.APP_NAME, "username": user.username},
                _("Open this link to choose a new password. It works once, for %(minutes)s minutes:") % {"minutes": minutes},
                "",
                link,
                "",
                _("If you didn't ask for this, ignore this email: your password stays the same."),
                "",
            ]
        )
    return subject, body


def _send_link(request, identifier):
    account = find_account(identifier)
    if account is None or not account.is_active or not account.email:
        return
    link = create_link(account)
    subject, body = _compose(account, link)
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [account.email])
    except Exception:  # a mail problem must not surface to the person asking (or reveal anything)
        log.exception("Couldn't send a password reset email to user %s", account.pk)
        return
    security_log.event(request, "password_reset_requested", account, sent=True)


def _in_background(request, identifier):
    try:
        _send_link(request, identifier)
    except Exception:
        log.exception("Password reset email failed")
    finally:
        connections.close_all()  # this thread's own database connections


def deliver(work, *args):
    """Run `work` after the answer has gone: in a background thread (tests replace this)."""
    threading.Thread(target=work, args=args, daemon=True).start()


def request_reset(request, identifier):
    """Send a reset link if `identifier` names an active account with an email; reveal nothing."""
    security_log.event(request, "password_reset_requested", None, identifier=security_log.fingerprint(identifier))
    deliver(_in_background, request, identifier)

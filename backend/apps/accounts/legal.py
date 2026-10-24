"""Acceptance of the Terms of Use and the Privacy Policy.

Both texts (frontend/src/legal/) are accepted together, as one version: LEGAL_VERSION, the date they last
changed. Each account stores the version it accepted and when:

- registration requires accepting the current version (RegisterSerializer.accept_terms);
- accounts a teacher created from a class roster accept at their first sign-in, with their new password;
- when LEGAL_VERSION changes, everyone signed in is asked to accept the new version before going on
  (UserSerializer.consent_required, which the app checks).

Each acceptance is also an audit entry ("terms_accepted", with the version and how), so the history stays
after a later acceptance replaces the stored version.
"""

from django.conf import settings
from django.utils import timezone

from apps.core import audit


def current_version():
    return settings.LEGAL_VERSION


def consent_required(user):
    """True while the account has not accepted the current Terms and Privacy Policy."""
    return user.terms_version != current_version()


def record_acceptance(request, user, how):
    """Store that `user` accepted the current version now. `how`: "register", "first_sign_in" or "update"."""
    now = timezone.now()
    version = current_version()
    type(user).objects.filter(pk=user.pk).update(terms_version=version, terms_accepted_at=now)
    user.terms_version, user.terms_accepted_at = version, now
    audit.record(request, "terms_accepted", user, version=version, how=how)


def public_info():
    """What the legal pages show besides their text (the app reads it from /api/site/)."""
    return {
        "version": current_version(),
        "draft": settings.LEGAL_DRAFT_NOTICE,
        "entity": settings.LEGAL_ENTITY_NAME,
        "address": settings.LEGAL_ENTITY_ADDRESS,
        "privacy_email": settings.PRIVACY_CONTACT_EMAIL,
        "hosting": settings.DATA_HOSTING_LOCATION,
    }


def retention_info():
    """How long records are kept, in days (0 = kept), for the Privacy Policy."""
    return {
        "deletion_grace_days": settings.ACCOUNT_DELETION_GRACE_DAYS,
        "santa_days": settings.SANTA_LOG_RETENTION_DAYS,
        "audit_days": settings.AUDIT_LOG_RETENTION_DAYS,
        "usage_days": settings.USAGE_RETENTION_DAYS,
        "contact_days": settings.CONTACT_RETENTION_DAYS,
        "backup_days": settings.BACKUP_KEEP_DAYS,
        "temporary_password_days": settings.TEMPORARY_PASSWORD_DAYS,
        # How long the sign-in cookie keeps someone signed in.
        "session_days": settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].days,
    }

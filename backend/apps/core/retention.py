"""How long records are kept: `manage.py privacy_cleanup` deletes what is older than the settings allow.

| Records                                   | Setting (days, 0 = keep)  |
|-------------------------------------------|---------------------------|
| Santa's questions and answers             | SANTA_LOG_RETENTION_DAYS  |
| The audit log                             | AUDIT_LOG_RETENTION_DAYS  |
| Daily usage counters (Santa, code runner) | USAGE_RETENTION_DAYS      |
| Contact-form messages                     | CONTACT_RETENTION_DAYS    |

Expired password-reset links, parent codes and refresh tokens are deleted too. The money ledger and payments
are never deleted here (tax and accounting law). The Privacy Policy states these periods (/api/site/).
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def _before(days, now):
    return now - timedelta(days=days) if days > 0 else None


def purge_expired(now=None):
    """Delete records past their retention period. Returns {what: rows deleted}."""
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

    from apps.accounts.models import ParentInvite, PasswordResetToken
    from apps.coderun.models import CodeRunUsage
    from apps.core.models import AuditLog
    from apps.tutor.models import SantaUsage, TutorExchange
    from apps.website.models import ContactMessage

    now = now or timezone.now()
    deleted = {}

    def purge(name, queryset):
        deleted[name] = queryset.delete()[0]

    if cutoff := _before(settings.SANTA_LOG_RETENTION_DAYS, now):
        purge("santa_exchanges", TutorExchange.objects.filter(created_at__lt=cutoff))
    if cutoff := _before(settings.AUDIT_LOG_RETENTION_DAYS, now):
        purge("audit_entries", AuditLog.objects.filter(created_at__lt=cutoff))
    if cutoff := _before(settings.USAGE_RETENTION_DAYS, now):
        day = timezone.localdate(cutoff)
        purge("santa_usage", SantaUsage.objects.filter(day__lt=day))
        purge("code_run_usage", CodeRunUsage.objects.filter(day__lt=day))
    if cutoff := _before(settings.CONTACT_RETENTION_DAYS, now):
        purge("contact_messages", ContactMessage.objects.filter(created_at__lt=cutoff))
    purge("password_reset_links", PasswordResetToken.objects.filter(expires_at__lt=now))
    purge("parent_codes", ParentInvite.objects.filter(expires_at__lt=now))
    purge("refresh_tokens", OutstandingToken.objects.filter(expires_at__lt=now))
    return deleted
